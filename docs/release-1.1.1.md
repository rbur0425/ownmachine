# OwnMachine v1.1.1 release preparation

Adds pinned static analysis and runtime dependency auditing to pull requests and
weekly CI. Ruff, Bandit, ShellCheck, actionlint, zizmor, focused mypy checks and
OwnMachine security regression rules retain reviewable reports and fail according
to the [analysis policy](static-analysis.md).

Removes unused Python code, makes shell startup-attempt validation explicit,
disables implicit workflow caching and adds missing-pipe checks to transport code.
WebSocket SHA-1 is explicitly marked as non-security protocol framing. Reviewed
protocol/local-libvirt exceptions are narrow and documented. Runtime dependency
ranges and existing platform qualification limits remain unchanged.

This branch prepares v1.1.1; no release or catalog pin update occurs until approved.
