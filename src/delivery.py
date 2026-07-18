import asyncio
import logging
from typing import Literal, Optional
from pydantic import BaseModel
from src.config import Settings
import httpx
from httpx_sse import aconnect_sse
import json
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class DocResult(BaseModel):
    doc_id: str
    doc_url: str
    status: Literal["created", "updated", "failed"]

class DraftResult(BaseModel):
    draft_id: str
    message: str
    status: Literal["created", "failed"]

class DeliveryResult(BaseModel):
    doc: Optional[DocResult]
    draft: Optional[DraftResult]
    fallback_used: bool

async def _call_tool(client: httpx.AsyncClient, post_url: str, request_id: int, responses: dict, tool_name: str, args: dict):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }
    responses[request_id] = asyncio.Future()
    resp = await client.post(post_url, json=payload)
    resp.raise_for_status()
    data = await responses[request_id]
    if "error" in data:
        raise Exception(f"Tool error: {data['error']}")
    
    result = data.get("result", {})
    if result.get("isError"):
        content = result.get("content", [])
        error_msg = content[0].get("text", "Unknown tool execution error") if content else "Unknown tool execution error"
        raise Exception(f"Tool execution failed: {error_msg}")
        
    return result

async def publish_to_google_docs(client: httpx.AsyncClient, post_url: str, responses: dict, get_id, pulse_md: str, settings: Settings) -> DocResult:
    try:
        req_id = get_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/list"
        }
        responses[req_id] = asyncio.Future()
        resp = await client.post(post_url, json=payload)
        resp.raise_for_status()
        
        data = await responses[req_id]
        tools = data.get("result", {}).get("tools", [])
        
        tool_name = "docs.append_content" 
        for tool in tools:
            if "append" in tool.get("name", "").lower() or "google" in tool.get("name", "").lower():
                tool_name = tool["name"]
                break
                
        if not settings.pulse_doc_id:
            logger.warning("pulse_doc_id is empty. Cannot append to document.")
            return DocResult(doc_id="", doc_url="", status="failed")

        call_id = get_id()
        result = await _call_tool(
            client, post_url, call_id, responses, tool_name, 
            {"documentId": settings.pulse_doc_id, "content": pulse_md}
        )
        
        return DocResult(
            doc_id=settings.pulse_doc_id,
            doc_url=f"https://docs.google.com/document/d/{settings.pulse_doc_id}",
            status="updated"
        )
    except Exception as e:
        logger.error(f"Failed to publish to Google Docs: {e}")
        return DocResult(doc_id="", doc_url="", status="failed")

async def create_gmail_draft(client: httpx.AsyncClient, post_url: str, responses: dict, get_id, email_body: str, settings: Settings, doc_url: Optional[str]) -> DraftResult:
    try:
        subject = "📊 Weekly Review Pulse"
        body = email_body
        if doc_url:
            body += f"\n\nGoogle Doc Link: {doc_url}"
            
        req_id = get_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/list"
        }
        responses[req_id] = asyncio.Future()
        resp = await client.post(post_url, json=payload)
        resp.raise_for_status()
        
        data = await responses[req_id]
        tools = data.get("result", {}).get("tools", [])
        
        tool_name = "gmail.draft_email"
        for tool in tools:
            if "draft" in tool.get("name", "").lower() or "email" in tool.get("name", "").lower() or "mail" in tool.get("name", "").lower():
                tool_name = tool["name"]
                break
                
        call_id = get_id()
        result = await _call_tool(
            client, post_url, call_id, responses, tool_name, 
            {"recipient": settings.pulse_email_to, "subject": subject, "body": body}
        )
        
        return DraftResult(
            draft_id="unknown_id",
            message="Draft created successfully",
            status="created"
        )
    except Exception as e:
        logger.error(f"Failed to create Gmail draft: {e}")
        return DraftResult(draft_id="", message=str(e), status="failed")

async def deliver_async(pulse_md: str, email_body: str, settings: Settings) -> DeliveryResult:
    url = settings.mcp_server_url
    logger.info(f"Connecting to MCP server at {url}")
    
    doc_result = None
    draft_result = None
    fallback_used = False
    
    headers = {"Authorization": f"Bearer {settings.mcp_auth_token}"} if settings.mcp_auth_token else {}
    
    try:
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            async with aconnect_sse(client, "GET", url) as event_source:
                endpoint_future = asyncio.Future()
                responses = {}
                
                async def listen():
                    try:
                        async for event in event_source.aiter_sse():
                            if event.event == "endpoint":
                                if not endpoint_future.done():
                                    endpoint_future.set_result(event.data)
                            elif event.event == "message":
                                data = json.loads(event.data)
                                req_id = data.get("id")
                                if req_id is not None and req_id in responses:
                                    responses[req_id].set_result(data)
                    except Exception as e:
                        logger.error(f"SSE Listener error: {e}")
                
                task = asyncio.create_task(listen())
                
                try:
                    post_path = await asyncio.wait_for(endpoint_future, timeout=30.0)
                except asyncio.TimeoutError:
                    raise Exception("Timed out waiting for MCP endpoint event after 30 seconds.")
                    
                post_url = post_path if post_path.startswith("http") else urljoin(url, post_path)
                logger.info("Connected to MCP server.")
                
                _id_counter = 1
                def get_id():
                    nonlocal _id_counter
                    _id_counter += 1
                    return _id_counter
                    
                doc_result = await publish_to_google_docs(client, post_url, responses, get_id, pulse_md, settings)
                
                if doc_result.status == "failed":
                    logger.warning("Docs failed, using fallback content for email")
                    fallback_used = True
                    doc_url = None
                else:
                    doc_url = doc_result.doc_url
                    
                draft_result = await create_gmail_draft(client, post_url, responses, get_id, email_body, settings, doc_url)
                
                task.cancel()
    except Exception as e:
        logger.error(f"MCP connection failed: {e}")
        fallback_used = True
        
    return DeliveryResult(doc=doc_result, draft=draft_result, fallback_used=fallback_used)

def deliver(pulse, pulse_md: str, email_body: str, settings: Settings) -> DeliveryResult:
    """Synchronous orchestrator for delivery."""
    return asyncio.run(deliver_async(pulse_md, email_body, settings))
