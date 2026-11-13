# Security hardening validation

Historical security-preview acceptance, 2026-11-11; clean-account runtime source
`6ea64454e897151e4e21186254f43ea8ead49844`.

A fresh non-admin Mac account installed the patched app and a new macOS guest
without directory-ownership repairs. The host account first needed a graphical
login to initialize its keychain; app identity registration also required correction.
Sampled installer boots exposed no VNC listener. Guided guest permissions, final
capture consent and private streaming passed.

Separate agent/viewer identities passed opposite-role refusals and private-file
access checks. Native-provider and browser input saved independently verified
content. Human reservation refused an agent write. Restart retained data and
permissions; temporary setup access was retired and tested rejected. Shared
SQLite permissions required the now-documented initialization procedure.

An initial guest hang required power-off after graceful stop timed out; its cause
was not established. Later normal restart and shutdown/start passed. This does not
prove unattended reliability. The run exercised direct provider input, not a new
model-driven task.

Combined PF/application firewall checks blocked external VNC while allowing the
private path. Independent application-firewall-only random-port coverage and a
physical reboot of this arrangement were not tested. Local-account isolation does
not come from the application firewall. Manual unmanaged launches remain outside
the hardened path.

Automated tests covered firewall evidence, managed credentials, private-file
handling, role separation and tool restrictions. Current changes require their
own CI results; historical platform skips are not current validation counts.
See [safe installation](security-isolation.md) and [acceptance overview](acceptance.md).
