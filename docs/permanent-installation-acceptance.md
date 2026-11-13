# Persistent installation acceptance

2026-11-10; historical Linux runtime and Mac host evaluation.

Direct restricted SSH passed under the configured runtime user; arbitrary
commands were refused. A separate fresh Hermes home installed and validated the
plugin. User/home and persistent mount ownership must match; default container
root access is not a substitute.

Supervised viewer restart rotated access credentials while preserving shared
control. Container recreation retained configuration/plugin state and passed
native/viewer checks. Source remained in a permanent versioned location.
These checks did not reboot the physical host or certify unattended model startup.
See [permanent setup](permanent-installation.md) and [separate reboot evidence](laptop-permanent-reboot-acceptance.md).

This is a scoped historical result, not certification of every later commit.
See the [acceptance overview](acceptance.md) for current evidence and limits.
