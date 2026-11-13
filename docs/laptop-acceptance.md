# Fresh laptop onboarding acceptance

Historical macOS laptop evaluation.

Fresh provisioning, key-only guest access, hardening and signed driver setup
passed. The normal permission-guide window allowed System Settings to appear in
front; Accessibility, Screen Recording and final capture consent were approved
manually. Protected password-dialog paste failed; direct typing remains the
fallback. Host permissions were not granted.

A separate Hermes installation passed doctor, MCP, capture, authenticated browser
streaming/input and human handoff. Guest restart preserved saved data and recovered
the driver. Ordinary native-viewer clipboard checks passed, but do not establish
privileged-dialog paste reliability. LAN VNC blocking was checked separately.

Observed disk use was workload/cache dependent; sparse capacity is not an all-in
installation-space requirement. Use current preflight checks rather than historical
free-space measurements. See [current installation guidance](evaluator-quickstart.md).

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
