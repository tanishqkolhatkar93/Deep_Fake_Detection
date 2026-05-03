# Security Policy

## Supported surface

This repository ships a public website and a public inference API. Treat both as internet-facing.

## Reporting a vulnerability

Do not open a public GitHub issue for credential leaks, bypasses, or abuse paths.

Use private contact instead:

- Email the maintainer directly if contact is available
- Or open a GitHub private vulnerability report from the Security tab

## Current security posture

The public demo currently includes:

- file-type allowlists
- MIME validation
- image and video size caps
- max video duration checks
- request IDs
- basic IP-based rate limiting
- restricted CORS allowlist

## Known limitations

This is not a regulated forensic platform. It does not yet include:

- durable audit logging
- WAF-backed abuse filtering
- Redis-backed rate limiting
- malware scanning
- async job isolation for heavy video processing

Do not position it as a compliance-grade evidence system in its current form.
