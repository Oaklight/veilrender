---
title: Security
---

# Security

VeilRender includes several built-in security features (since v0.3.1) to protect against common web-rendering threats.

## URL Validation

Only `http://` and `https://` schemes are allowed in render requests. Dangerous schemes are blocked:

- `file://` — local filesystem access
- `data:` — inline data URIs
- `javascript:` — script execution

Requests with blocked schemes are rejected with a `400` error.

## SSRF Protection

All target URLs are resolved through DNS before rendering. VeilRender rejects URLs that resolve to private or internal IP addresses:

- **Loopback** — `127.0.0.0/8`, `::1`
- **RFC 1918** — `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **Link-local** — `169.254.0.0/16`, `fe80::/10`
- **Cloud metadata** — `169.254.169.254` (AWS/GCP/Azure metadata endpoint)

This prevents Server-Side Request Forgery (SSRF) attacks where an attacker could use VeilRender to probe internal services.

## Rate Limiting

VeilRender uses fail2ban-style IP rate limiting for authentication failures:

- **Threshold**: 3 failed authentication attempts within 5 minutes
- **Ban duration**: 10 minutes
- **X-Forwarded-For**: Supported for deployments behind a reverse proxy

Banned IPs receive a `429 Too Many Requests` response.

## Request Size Limit

Request bodies are limited to **64 KB**. Requests exceeding this limit are rejected with a `413` error.

## Logging

Blocked requests (invalid schemes, SSRF attempts, rate-limited IPs) are logged at `INFO` level for monitoring and auditing.
