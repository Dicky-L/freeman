# Production FastAPI + SSE LLM Chat

A compact, production-oriented reference project for **Python async + FastAPI + LLM streaming + reverse-proxy reliability**.

This is not a chat UI toy. The purpose is to demonstrate the failure modes that show up when an LLM stream runs behind Nginx / Cloudflare / an ALB and must survive real client disconnects, slow providers, rate limits and partial responses.

> Portfolio implementation built to demonstrate reusable engineering patterns. It is not presented as code copied from a previous client.

## What it demonstrates

```text
Browser / frontend
      |
      | POST /v1/chat/stream
      v
   FastAPI
      |
      +--> request ID / structured logs
      +--> client disconnect detection
      +--> SSE framing + heartbeat
      +--> pre-token retry policy
      +--> idle + total stream deadline
      |
      v
 provider adapter
      |
      +--> demo provider (no key)
      +--> OpenAI Responses API
      |
      v
 Nginx / reverse proxy
 proxy_buffering off
```

## Production decisions

| Failure mode | Design response |
|---|---|
| Nginx buffers token chunks | `proxy_buffering off` + `X-Accel-Buffering: no` |
| proxy closes an idle stream | SSE heartbeat comments |
| upstream hangs before/among tokens | idle timeout |
| request runs forever | max stream duration |
| provider rate limit / transient failure before output | bounded retry |
| provider fails after partial output | no transparent replay; explicit `error` event |
| browser closes tab / user presses Stop | disconnect detection + upstream generator cleanup |
| debugging a broken stream | request ID + JSON logs + stable error codes |
| slow client | direct async yielding; no unbounded application queue |
| secret leakage | API key remains server-side; prompts are not logged by default |

## Quick start

```bash
cd portfolio/production-fastapi-sse-llm-chat
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn production_sse_chat.api:app --reload
```

Open `http://127.0.0.1:8000/demo`.

With OpenAI:

```bash
pip install -e '.[dev,openai]'
export LLM_PROVIDER=openai
export OPENAI_API_KEY='...'
export OPENAI_MODEL='gpt-5'
uvicorn production_sse_chat.api:app --reload
```

Run behind Nginx:

```bash
docker compose up --build
```

Then open `http://127.0.0.1:8080/demo`.

## Tests

```bash
pytest -q
```

Current suite covers SSE framing, retry-before-first-token, no transparent retry after partial output, heartbeat, idle timeout, cancellation cleanup, and the FastAPI endpoint/request-ID contract.

See [production notes](docs/production-notes.md) for the engineering trade-offs.
