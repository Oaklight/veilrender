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

## Scope

This service renders attacker-supplied URLs in a real browser, so the following
are treated as security issues rather than bugs:

- requests to internal, loopback, link-local, or cloud metadata addresses
  (SSRF), including via redirects, subresources, or DNS rebinding,
- reading local files or non-HTTP schemes,
- escaping the browser sandbox or the container,
- authentication or authorization bypass.
