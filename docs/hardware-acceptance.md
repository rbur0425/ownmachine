# Model and physical-host acceptance

Historical macOS acceptance; reboot follow-up 2026-11-10.

A real Hermes model created and saved a TextEdit document; independent file and
Accessibility checks confirmed the result. Earlier runs encountered focus,
unsupported action and pixel-capture expiry failures. Corrective direct-provider
checks are not substitutes for model-driven acceptance of every input path.

## Physical-host reboot follow-up — 2026-11-10

Operator-assisted host restart passed: changed host boot identity, effective IPv4
LAN VNC blocking before guest startup, restricted SSH/MCP, retained permissions,
saved-document content, capture and viewer handshake. Chrome reopened, but exact
browser-profile identity was not established.

Login/FileVault unlock and explicit guest startup remained operator steps. This
is historical evidence, not proof of reboot behavior for every later firewall or
Lume change. Cloud hosts, IPv6 coverage and unattended recovery are not certified.

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
