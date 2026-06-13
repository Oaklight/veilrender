---
title: GET /health
---

# GET /health

Health check endpoint. Does not require authentication.

## Request

```bash
curl http://localhost:7860/health
```

## Response

```json
{
  "status": "ok"
}
```

Returns HTTP 200 with `{"status": "ok"}` if the service is running.
