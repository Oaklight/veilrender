# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities through GitHub's **private vulnerability
reporting**:

1. Open the repository's **Security** tab.
2. Click **Report a vulnerability**.

That opens a draft advisory visible only to the maintainers. Please **do not open
a public issue** for a security problem — a public report is immediately visible
to everyone running the published Docker images and PyPI package.

A useful report includes:

- the affected version or commit,
- a minimal reproduction (the exact request, and any URL that triggers it),
- the impact you believe it has,
- a suggested fix, if you have one.

Partial reports are welcome. If you are unsure whether something is exploitable,
report it anyway rather than testing it against third-party deployments.

## Supported versions

Fixes are issued against the latest release on `master` and shipped in a patch
release. Older releases are not maintained; upgrade to the newest version.

## What to expect

- We aim to acknowledge a report within a few days.
- We will confirm the issue, and tell you whether we consider it in scope.
- We prefer coordinated disclosure: we fix, release, and publish a GitHub
  advisory, and we are happy to credit you unless you ask us not to.
- Please give us a reasonable window to ship a fix before disclosing publicly.

## Outbound request policy

VeilRender routes every browser connection through an in-process egress proxy.
For each destination — including every redirect hop, which browser-level route
handlers do not see — the proxy:

- resolves the hostname once and requires every result to be globally
  routable, refusing multicast, NAT64-encoded IPv4 (`64:ff9b::/96`), 6to4,
  Teredo, and other special-purpose ranges in addition to the private space,
- connects only to an address it validated, so a second DNS answer cannot
  move the connection,
- refuses non-global destinations before any connection is made.

The proxy fails closed. If it is unreachable, or cannot be applied to a
browser tier, requests through that tier fail rather than bypassing the
policy. Obscura ignores per-context proxy settings, so it is started with
`--proxy`. Every worker runs a canary navigation at startup and after a
restart; the refusal is counted only when it arrives through the proxy, so a
worker that ignores its proxy configuration (including a remote Obscura that
was not actually started with `--proxy`) is marked unhealthy instead of being
used unprotected.

When traffic is chained through an operator-supplied upstream proxy, the
validated IP is sent upstream by default. Setting
`VEILRENDER_UPSTREAM_PIN_IP=false` forwards the hostname instead, which lets
the upstream resolve again; that trade-off is explicitly the operator's.

The raw `/cdp` endpoint is disabled by default. It gives a client direct
browser control, including contexts that are not created by VeilRender;
local Chromium is launched with a browser-level `--proxy-server` so such
contexts are still proxied, but remote browsers are only protected if they
were launched with the same browser-level proxy. When remote workers are
configured, `/cdp` is rejected even if enabled, because the gateway cannot
apply that launch-level proxy to them. Operators who enable
`VEILRENDER_CDP_ENABLED` should treat CDP access as equivalent to access to
the browser container. When `VEILRENDER_EGRESS_PROXY_TOKEN` is set, contexts
created over `/cdp` on a local worker fail closed (407): Chromium's
browser-level proxy setting cannot carry credentials.

When the proxy binds to a non-loopback address it requires Basic
authentication. The token is passed to Obscura on its command line, so it is
visible to anything sharing the container or host process namespace; scope and
rotate it accordingly.

In upstream mode the proxy assumes the client sends one request per
connection. Browsers do; raw clients must not pipeline. Do not expose the
proxy to untrusted raw clients.

`VEILRENDER_EGRESS_PROXY=false` disables enforcement. It exists for
debugging and is not supported for internet-facing deployments.

The proxy covers HTTP, HTTPS, and WebSocket traffic, which is what a page can
use to reach internal services. UDP-based transports do not traverse an HTTP
proxy: local Chromium workers are launched with `--disable-quic` and
`--force-webrtc-ip-handling-policy=disable_non_proxied_udp`. Remote Chromium
workers (for example `cloakserve` containers) must be launched with the same
flags, and Camoufox needs `media.peerconnection.ice.proxy_only=true` or WebRTC
disabled; the gateway cannot apply these to a browser it did not launch. The
HTTP proxy is not an egress firewall — run the service behind host or network
egress rules as defense in depth.

## Scope

This service renders attacker-supplied URLs in a real browser, so the following
are treated as security issues rather than bugs:

- requests to internal, loopback, link-local, or cloud metadata addresses
  (SSRF), including via redirects, subresources, or DNS rebinding,
- reading local files or non-HTTP schemes,
- escaping the browser sandbox or the container,
- authentication or authorization bypass.
