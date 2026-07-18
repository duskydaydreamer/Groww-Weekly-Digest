# App Store Review Pulse — Edge Cases & Corner Scenarios

This document outlines potential edge cases, corner scenarios, and failure modes across the review processing pipeline, along with the required mitigation strategies to ensure the system remains resilient.

---

## 1. Data Ingestion & Parsing

| Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Empty Export Files** | Pipeline fails because there is no data to process. | **Check & Abort:** Verify row count post-parsing. If `count == 0`, log a clear warning ("No reviews found in export") and gracefully exit the pipeline without attempting to generate a pulse. |
| **Missing / Changed Columns** | `KeyError` when attempting to map CSV columns to the unified schema. | **Flexible Mapping:** Use fuzzy matching for column headers (e.g., check for `Review Text` or `Body`). Fallback: Prompt the user with expected column names vs. actual column names and abort. |
| **Malformed / Non-UTF8 Encoding** | CSV parser throws decoding errors (common with Apple exports containing emojis). | **Encoding Fallbacks:** Attempt to parse using `utf-8-sig`, fallback to `latin-1` or `cp1252`, and use `errors='replace'` to preserve as much text as possible. |
| **Rating-Only Reviews (No Text)**| Meaningless strings passed to the LLM (e.g., just `""` or `NaN`). | **Filter Pipeline:** Drop any review where `word_count == 0` during the normalization step. We only care about qualitative feedback. |
| **Massive Volume Spikes** | Exceeding LLM token limits or running into high API costs. | **Sampling:** If `len(reviews) > 1000` (configurable), implement random or stratified sampling (e.g., ensure proportional representation of 1-star and 5-star reviews) to cap the LLM payload. |

## 2. PII Scrubbing

| Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Obfuscated PII** | User writes "john dot doe at gmail" dodging regex patterns. | **LLM Semantic Check:** Rely on the LLM's inherent understanding during the theming phase to avoid highlighting PII in the generated pulse. Add a strict system prompt constraint: *"Never include names or contact info in the output."* |
| **Regex False Positives** | Version numbers (e.g., `1.2.3.456`) scrubbed as phone numbers/IPs. | **Contextual Regex:** Ensure regex patterns use strong word boundaries. Accept minor false positives as a trade-off for zero false negatives on privacy. |
| **Full Redaction** | Review text was entirely PII and becomes empty (e.g., `"[EMAIL_REDACTED] [PHONE_REDACTED]"`). | **Post-Scrub Filtering:** If `word_count` of the scrubbed review drops to 0, filter it out before passing it to the clustering engine. |

## 3. LLM Theme Clustering

| Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **LLM Safety Filter Blocks** | API refuses to process a batch because reviews contain profanity or hate speech. | **Batch Isolation:** Catch `BlockedPromptException`. Discard the offending batch of reviews, log a warning, and proceed with the remaining batches. |
| **Malformed JSON Output** | LLM responds with conversational text (e.g., *"Here is your JSON: {..."*) breaking the parser. | **Strict Parsing:** Use `json.loads` within a try/except. On failure, use a regex fallback (e.g., `\{.*\}`) to extract the JSON payload, or retry the prompt explicitly asking for "RAW JSON ONLY." |
| **> 5 Themes Generated** | LLM ignores the `<max_themes>` constraint. | **Truncation / Merging:** Sort returned themes by assigned review count. Keep the top 5, and map any reviews assigned to themes 6+ into an "Other/Miscellaneous" bucket. |
| **Homogenous Reviews** | Every review says exactly "Good app", making 3 themes impossible. | **Dynamic Output:** If the LLM only finds 1 or 2 themes, accept it. The Pulse Generator must not force 3 themes if they don't exist. Adapt the Jinja template to handle `len(themes) < 3`. |
| **Hallucinated Quotes** | LLM invents a perfectly phrased quote that isn't in the dataset. | **Exact String Matching (Validation):** Before adding a quote to the pulse, `assert quote in raw_review_text`. If it fails, pick the highest-relevance actual review string instead. |

## 4. Pulse Generation

| Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Exceeding 250-Word Limit**| Pulse is too dense, violating stakeholder scannability requirements. | **Validation & Retry:** Count words of the generated markdown. If `> 250`, append system prompt: *"Your previous response was {N} words. Rewrite it to be STRICTLY under 250 words"* and retry once. If it fails again, truncate non-essential text. |
| **Generic Action Ideas** | LLM suggests "Fix the bugs" or "Improve the UI." | **Prompt Engineering:** Enforce constraint in the prompt: *"Actions must mention specific features, UI elements, or flows based on the themes."* |

## 5. MCP Delivery (Google Docs & Gmail)

| Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **MCP Server Unavailable** | Cannot connect to local `@anthropic/gdocs-mcp-server`. | **Graceful Degradation:** Save the generated Markdown to local disk (`data/processed/pulse_fallback.md`). Log a `CRITICAL` error with instructions on how to manually copy-paste the report. |
| **Multiple Runs in One Week** | Creating 5 separate Docs for the same week if the script is run daily. | **Idempotent Updates:** Query Google Docs for a document with the title "Weekly Review Pulse — {Week}". If it exists, use the `update_document` tool to append/prepend the new data rather than creating a duplicate. |
| **OAuth Token Expiry** | Delivery silently fails due to `401 Unauthorized` from Google. | **Alerting:** Catch authentication errors specifically and print a high-visibility terminal message instructing the user to run the MCP auth re-flow. |
