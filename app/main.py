from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.config import settings
from app.optimizer import optimize
from app.schemas import ChatRequest
from app.storage import cache_get, cache_key, cache_put, init_db, log_request, stats


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Token Shield", version="0.1.0", lifespan=lifespan)


@app.get("/")
async def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stats")
async def get_stats():
    return stats()


@app.post("/v1/chat/completions")
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)):
    data = request.model_dump(exclude_none=True)
    options = data.pop("token_shield", {})
    messages = data["messages"]
    requested_max = data.pop("max_completion_tokens", None) or data.pop("max_tokens", None)
    result = optimize(messages, data.get("model"), requested_max, options)
    data.update(model=result.model, messages=result.messages, max_completion_tokens=result.max_tokens)

    use_cache = options.get("cache", True) and not request.stream and (request.temperature or 0) == 0
    key = cache_key(data)
    if use_cache and (cached := cache_get(key)):
        cached.setdefault("token_shield", {}).update({"cache_hit": True, "saved_input_tokens": result.before_tokens})
        log_request(result.model, result.before_tokens, 0, 0, True, result.actions + ["cache_hit"])
        return JSONResponse(cached)

    api_key = (authorization or "").removeprefix("Bearer ").strip() or settings.openai_api_key
    if not api_key:
        raise HTTPException(401, "Missing API key. Send Authorization: Bearer ... or set OPENAI_API_KEY.")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{settings.upstream_base_url.rstrip('/')}/v1/chat/completions"
    client = httpx.AsyncClient(timeout=120)
    if request.stream:
        upstream = await client.send(client.build_request("POST", url, headers=headers, json=data), stream=True)
        if upstream.is_error:
            body = await upstream.aread()
            await client.aclose()
            return JSONResponse(status_code=upstream.status_code, content={"error": body.decode(errors="replace")})
        log_request(result.model, result.before_tokens, result.after_tokens, 0, False, result.actions)

        async def relay():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()
        return StreamingResponse(relay(), media_type="text/event-stream")

    try:
        upstream = await client.post(url, headers=headers, json=data)
    finally:
        await client.aclose()
    try:
        body = upstream.json()
    except ValueError:
        raise HTTPException(502, f"Upstream returned invalid JSON ({upstream.status_code})")
    if upstream.is_error:
        return JSONResponse(status_code=upstream.status_code, content=body)

    output_tokens = body.get("usage", {}).get("completion_tokens", 0)
    saved = max(0, result.before_tokens - result.after_tokens)
    body["token_shield"] = {"cache_hit": False, "before_tokens": result.before_tokens, "after_tokens": result.after_tokens, "saved_input_tokens": saved, "actions": result.actions}
    log_request(result.model, result.before_tokens, result.after_tokens, output_tokens, False, result.actions)
    if use_cache:
        cache_put(key, body)
    return JSONResponse(body)

