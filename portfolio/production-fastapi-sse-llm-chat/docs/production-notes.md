# Production notes

## 1. Retry boundary: before first token only

Streaming changes retry semantics. Before any model text is emitted, a retry is invisible to the user. After a text delta has been delivered, blindly restarting the upstream request can duplicate output or produce a divergent continuation.

This project therefore retries only pre-token failures. Post-token failures are surfaced as an explicit `error` SSE event with `retryable=true/false` so the client can decide whether to restart the conversation.

## 2. Disconnect propagation

The API checks `request.is_disconnected()` and also handles task cancellation. The provider async generator is closed in `finally`, so an upstream HTTP stream can be released instead of continuing to spend tokens after the browser has gone away.

## 3. Heartbeats vs timeouts

A comment frame (`: ping`) is emitted while the server waits for the next provider delta. Heartbeat interval and upstream idle timeout are separate controls:

- heartbeat keeps intermediaries from treating an idle connection as dead;
- idle timeout stops an upstream that has stalled;
- max duration prevents a single request from living forever.

Every proxy/load balancer in the path should have an idle timeout longer than the application heartbeat interval.

## 4. Nginx and reverse proxies

`proxy_buffering off` is essential for low-latency token delivery through Nginx. The application also sends `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform` as defense in depth.

Do not add a `Connection: keep-alive` response header at the application layer: connection-specific headers are not valid in HTTP/2. Let the HTTP server and reverse proxy negotiate the transport.

## 5. Backpressure

The implementation does not accumulate the full model output in memory. Each provider delta is yielded directly into the ASGI response path. Slow clients therefore apply natural backpressure instead of allowing an unbounded application queue to grow.

## 6. Logging and privacy

Logs contain request ID, provider, attempt, status, duration and error codes, but do not log prompt text by default. For healthcare, finance, or other sensitive domains, prompt/response capture should be an explicit, access-controlled product decision rather than a default debugging behavior.

## 7. Scaling

The stream endpoint is stateless. Scale horizontally behind a load balancer; do not rely on in-process conversation memory. Persist conversation state externally only if the product needs it. Graceful shutdown/draining should allow existing SSE requests to finish or receive a controlled termination event before a container is killed.
