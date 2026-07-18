import asyncio
import httpx
from httpx_sse import aconnect_sse
import json
from urllib.parse import urljoin

async def main():
    url = "https://mcp-server-1-igzm.onrender.com/sse"
    print(f"Connecting to {url}...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
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
                    print(f"SSE Listener error: {e}")
            
            task = asyncio.create_task(listen())
            
            # Wait for the endpoint URL
            post_path = await endpoint_future
            post_url = post_path if post_path.startswith("http") else urljoin(url, post_path)
            print(f"Received POST endpoint: {post_url}")
            
            # Call tools/list
            request_id = 1
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list"
            }
            
            responses[request_id] = asyncio.Future()
            resp = await client.post(post_url, json=payload)
            resp.raise_for_status()
            
            data = await responses[request_id]
            tools = data.get("result", {}).get("tools", [])
            print("--- Available Tools ---")
            for tool in tools:
                print(f"Tool: {tool.get('name')}")
                print(f"Description: {tool.get('description')}")
                print(f"Schema: {json.dumps(tool.get('inputSchema'), indent=2)}")
                print("-" * 40)
            
            task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
