---
title: "GET / (Dashboard)"
---

# GET / (Dashboard)

The root path serves a built-in stats dashboard showing real-time service status. Does not require authentication.

## Features

- Service status badges
- Capacity bar (active / max concurrent contexts)
- Request statistics
- Responsive layout

## Request

Open in a browser or:

```bash
curl http://localhost:7860/
```

Returns an HTML page with the dashboard UI.
