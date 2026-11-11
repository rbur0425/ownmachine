# Setup transport acceptance — 2026-11-11

Scope: Hermes terminal dispatch, actual SSH authentication/forced-command
restriction, remote Mac preflight, and authenticated progress persistence. No
existing VM, firewall service, runtime key or guest permission was changed.

A temporary unprivileged OpenSSH server listened on laptop loopback, using newly
generated fixture keys and a restrictive forced-command entry. Known-hosts was
pinned from the locally generated server key, not trusted from a network scan.
A separate isolated Hermes home loaded the candidate plugin against Hermes source
`3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.

Observed through real Hermes CLI subprocesses:

- `setup --run preflight --json` executed on the actual Mac through SSH and
  imported an observed result, with the source/plan/VM/nonce bindings intact.
- `setup --run progress --json` fetched the endpoint's authenticated observations.
- A separate `status --json` invocation showed the persisted execution outcomes.
- The actual remote preflight checked Swift, available selected-volume capacity,
  CPU count and physical memory against the fixture plan.

Actual SSH refusal checks passed: arbitrary command, duplicate request nonce,
wrong plan digest, wrong source fingerprint, unapproved build stage, and wrong
server host key. The wrong-key test failed at OpenSSH authentication; it did not
reach the endpoint. Unit checks additionally exercise mismatched receipt fields,
strict stage postconditions, bounded output/timeouts, explicit apply, separate
setup alias, stale configuration, source-symlink refusal and chat's nonblocking
terminal handoff.

This is a **loopback SSH integration test on a real Mac**, not a new physical-host
installation or a Linux-to-remote-Mac provisioning acceptance run. The allowed
fixture stage was read-only preflight. No build, VM creation or permission grant
was performed. Full cross-machine execution, guest hardening, remote viewer
orchestration, computer_use screenshot and saved desktop task acceptance remain
open. The temporary server, fixture keys/profile and only their newly created
setup-state directories are removed after testing.
