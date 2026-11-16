# OwnMachine v1.1.1

Adds pinned static analysis and runtime dependency auditing to pull requests and
weekly CI. Ruff, Bandit, ShellCheck, actionlint, zizmor, focused mypy checks and
OwnMachine security regression rules retain reviewable reports and fail according
to the [analysis policy](static-analysis.md).

Removes unused Python code, makes shell startup-attempt validation explicit,
disables implicit workflow caching and adds missing-pipe checks to transport code.
WebSocket SHA-1 is explicitly marked as non-security protocol framing. Reviewed
protocol exceptions are narrow and documented; local-libvirt XML findings remain
visible for case-by-case review. Runtime dependency
ranges and existing platform qualification limits remain unchanged.

Security gates prioritize high findings (the highest category used by Bandit and
zizmor); medium/low findings remain in retained reports for case-by-case review.
Two high protocol/library exceptions are documented. The resolved runtime dependency
audit found no known vulnerabilities.

No VM recreation or host-service change is required for this update. Restart affected
Hermes processes after upgrading to load the updated provider. Catalog installs use
the reviewed catalog pin and receive this version only after its update is approved.
