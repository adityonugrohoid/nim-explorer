# Nvidia NIM API Reference

Complete documentation of the Nvidia NIM cloud API, based on live testing against 187 models (2026-03-06).

---

## Base URL & Authentication

```
Base URL:  https://integrate.api.nvidia.com/v1
Auth:      Authorization: Bearer $NVIDIA_API_KEY
Rate:      40 RPM (free tier)
```

Get an API key at [build.nvidia.com](https://build.nvidia.com).

No rate limit headers are returned in responses. Exceeding 40 RPM returns HTTP 429.

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/models` | GET | List all models (returns ~187, not all callable) |
| `/v1/chat/completions` | POST | Chat completion (OpenAI-compatible) |
| `/v1/completions` | POST | Text completion (base/code models) |
| `/v1/embeddings` | POST | Embedding generation |
| `/v1/reranking` | POST | Passage reranking |

---

## GET /v1/models

Returns all models registered on NIM, regardless of whether they're callable with your key.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "meta/llama-3.3-70b-instruct",
      "object": "model",
      "created": 735790403,
      "owned_by": "meta"
    }
  ]
}
```

**Important:** This endpoint lists ~187 models including embeddings, vision-only, deprecated, and premium models. Only ~107 are callable via `/v1/chat/completions` on the free tier. The only way to know is to probe each one.

---

## POST /v1/chat/completions

### Request Parameters

| Parameter | Type | Required | Default | Range | Notes |
|-----------|------|----------|---------|-------|-------|
| `model` | string | **yes** | — | — | Full org/model ID (e.g., `meta/llama-3.3-70b-instruct`) |
| `messages` | array | **yes** | — | — | OpenAI message format (see below) |
| `temperature` | float | no | varies | 0-2 | Default: 0.2 (Llama/Gemma), 0.6 (Nemotron/DeepSeek/Phi-4) |
| `top_p` | float | no | varies | >0-1 | Default: 0.7 (Llama), 0.95 (Nemotron/Phi-4) |
| `max_tokens` | int | no | varies | 1-16384 | Default: 512-8192 depending on model. Omit for model-decided |
| `stream` | bool | no | false | — | Returns SSE `text/event-stream` |
| `stop` | string/array | no | null | — | Stop sequence(s) |
| `frequency_penalty` | float | no | 0 | -2 to 2 | Penalize frequent tokens |
| `presence_penalty` | float | no | 0 | -2 to 2 | Penalize repeated tokens |
| `seed` | int | no | 0 | 0-2^64 | Best-effort reproducibility |
| `tools` | array | no | null | — | Function definitions (model-dependent) |
| `tool_choice` | string/object | no | — | `auto`, `none`, or named | Requires `tools` to be set |
| `response_format` | object | no | — | `{"type": "json_object"}` | JSON mode (model-dependent) |

**Default values vary significantly by model.** Always check model-specific docs on build.nvidia.com.

### Messages Format

```json
[
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi there!"},
  {"role": "user", "content": "How are you?"}
]
```

Roles: `system` (optional, must be first), `user`, `assistant`, `tool` (for tool results).

Vision models accept content as an array:
```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]
}
```

### Response Shape

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1772738213,
  "model": "meta/llama-3.3-70b-instruct",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you?"
    },
    "finish_reason": "stop",
    "logprobs": null
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 7,
    "total_tokens": 16,
    "prompt_tokens_details": null
  }
}
```

**`finish_reason` values:** `stop` (natural end), `length` (hit max_tokens), `tool_calls` (model wants to call a tool).

### Extra Response Fields by Backend

Different NIM backends add different non-standard fields. All are safe to ignore.

**vLLM backend (Llama family, Nemotron):**

| Field | Location | Value |
|-------|----------|-------|
| `refusal` | message | null |
| `annotations` | message | null |
| `audio` | message | null |
| `function_call` | message | null (deprecated) |
| `reasoning` | message | null |
| `reasoning_content` | message | null or string |
| `stop_reason` | choices[] | numeric token ID or null |
| `token_ids` | choices[] | null |
| `service_tier` | top-level | null |
| `system_fingerprint` | top-level | null |
| `prompt_logprobs` | top-level | null |
| `prompt_token_ids` | top-level | null |
| `kv_transfer_params` | top-level | null |

**TensorRT-LLM backend (Mistral, Phi-4):**

| Field | Location | Value |
|-------|----------|-------|
| `reasoning_content` | message | null |
| `stop_reason` | choices[] | null |

---

## Tool Calling

### Supported Models

Tool calling support must be enabled per-model on NIM's server side. Not all models support it.

**Confirmed working (2026-03-06):**
- `meta/llama-3.3-70b-instruct`
- `meta/llama-3.1-405b-instruct`
- `meta/llama-3.1-70b-instruct`
- `meta/llama-3.1-8b-instruct`
- `nvidia/llama-3.1-nemotron-ultra-253b-v1`
- `mistralai/mistral-small-3.1-24b-instruct-2503`
- `microsoft/phi-4-mini-instruct`

**Confirmed NOT supported:**
- `deepseek-ai/deepseek-r1-distill-*` (all R1 distill models)
- `qwen/qwq-32b`
- `qwen/qwen2.5-coder-32b-instruct`

**Broken/misconfigured:**
- `meta/llama-4-maverick-17b-128e-instruct` — returns tool JSON in `content` instead of `tool_calls`
- `google/gemma-3-27b-it` — requires `--enable-auto-tool-choice` server config

### Request Format

```json
{
  "model": "meta/llama-3.3-70b-instruct",
  "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get current weather for a city",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {"type": "string", "description": "City name"}
        },
        "required": ["city"]
      }
    }
  }],
  "tool_choice": "auto"
}
```

**`tool_choice` options:**
- `"auto"` — model decides whether to use tools
- `"none"` — model must not use tools
- `{"type": "function", "function": {"name": "get_weather"}}` — force specific tool

### Response with Tool Call

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "chatcmpl-tool-...",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"Paris\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

### Multi-Turn Tool Flow

1. Send user message with `tools` defined
2. Model responds with `tool_calls`
3. Append assistant message (with tool_calls) + tool result:
   ```json
   {"role": "tool", "tool_call_id": "chatcmpl-tool-...", "content": "{\"temp\": 18, \"condition\": \"cloudy\"}"}
   ```
4. Send follow-up request with same `tools`
5. Model responds with final answer using tool data

---

## Thinking / Reasoning

Three distinct patterns exist on NIM, depending on the model:

### Pattern 1: `<think>` Tags in Content

**Models:** DeepSeek R1-distill family, Phi-4 Mini Flash Reasoning

Thinking output is embedded in the `content` field:
```json
{
  "message": {
    "content": "<think>\nLet me work through this step by step...\n</think>\n\nThe answer is 42."
  }
}
```

**No control mechanism** — these models always think. DeepSeek recommends "enforce responses starting with `<think>`".

**Gotcha:** If `max_tokens` is hit before `</think>`, you get an unclosed tag.

### Pattern 2: `reasoning_content` Field

**Models:** Nemotron Ultra 253B

Thinking appears in a separate non-standard field:
```json
{
  "message": {
    "content": "The answer is 42.",
    "reasoning_content": "Let me work through this step by step..."
  }
}
```

**Control via system prompt:**
- Enable: `"detailed thinking on"` (recommended: temp 0.6, top_p 0.95)
- Disable: `"detailed thinking off"` (recommended: temp 0, greedy)

### Pattern 3: Budget Control (Self-Hosted NIM Only)

**Models:** Qwen3, Nemotron Nano 9B v2

Uses `nvext.max_thinking_tokens` parameter:
```json
{
  "nvext": {"max_thinking_tokens": 128}
}
```

Not available on the cloud API (integrate.api.nvidia.com). Requires `NIM_ENABLE_BUDGET_CONTROL=1` env var on self-hosted.

---

## Structured Output

### JSON Mode (`response_format`)

```json
{
  "response_format": {"type": "json_object"}
}
```

Constrains output to valid JSON but allows any structure (including empty objects).

### Guided Generation (Self-Hosted NIM Only)

More powerful alternatives available on self-hosted NIM:

| Method | Parameter | Description |
|--------|-----------|-------------|
| JSON Schema | `guided_json` | Constrain to specific JSON schema |
| Regex | `guided_regex` | Constrain to regex pattern |
| Choices | `guided_choice` | Constrain to list of options |
| Grammar | `guided_grammar` | Constrain to EBNF grammar |

Nvidia recommends `guided_json` over `response_format` for reliability.

---

## Streaming (SSE)

Set `"stream": true` to receive Server-Sent Events.

### Chunk Format

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{"role":"assistant","content":"","reasoning_content":null},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{"content":""},"logprobs":null,"finish_reason":"stop"}]}

data: [DONE]
```

### Key Observations

- First chunk includes `delta.role: "assistant"`
- Every chunk includes `reasoning_content: null` even for non-thinking models
- Final content chunk has `finish_reason` set
- `data: [DONE]` sentinel terminates the stream
- Usage is **not** included in stream chunks by default
- Some models (5/12 tested) include a usage-only chunk before `[DONE]`

---

## Error Responses

Error format is **inconsistent** across models and error types:

### Flat String Error
```json
{"error": "Tool use has not been enabled, because it is unsupported by deepseek-ai/deepseek-r1-distill-qwen-14b."}
```

### Structured Error
```json
{
  "error": {
    "message": "\"auto\" tool choice requires --enable-auto-tool-choice...",
    "type": "BadRequestError",
    "param": null,
    "code": 400
  }
}
```

### Plain Text (Not JSON)
```
Function 'b6bb6e01-...': Not found for account '...'
```
Returned with HTTP 404 for invalid model IDs. Breaks JSON parsers.

### Common HTTP Status Codes

| Code | Meaning | Notes |
|------|---------|-------|
| 200 | Success | |
| 400 | Bad request | Invalid params, unsupported features |
| 404 | Not found | Model not on your plan, or deprecated |
| 422 | Unprocessable | Validation error (wrong endpoint for model type) |
| 429 | Rate limited | Exceeded 40 RPM |
| 500 | Server error | Infrastructure issue (retry later) |

---

## Known Quirks

| Quirk | Affected | Description |
|-------|----------|-------------|
| `prompt_tokens_details: null` | Most models | Returns null instead of omitting the field |
| Non-JSON 404 | Invalid model ID | Plain text body instead of JSON error |
| Inconsistent error format | All | Three different error shapes (see above) |
| `reasoning_content: null` on every model | vLLM/TRT-LLM backends | Field present even when model doesn't think |
| Tool JSON in content | Llama 4 Maverick | Puts tool call in `content` instead of `tool_calls` |
| Gemma tool config error | Gemma 3 | Requires server-side flag that cloud doesn't set |
| Model ID mismatch | Nemotron Ultra | Request: `nvidia/llama-3.1-nemotron-ultra-253b-v1`, response: `stg/nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| Duplicate model IDs | GPT-OSS | `openai/gpt-oss-120b` and `openai/gpt-oss-20b` appear twice in `/v1/models` |
