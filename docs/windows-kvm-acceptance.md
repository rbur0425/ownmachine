# Windows KVM development acceptance

Windows is an experiment in this branch, not a released support claim. The Windows development setup choice now saves a plan and exposes read-only checks; fresh provisioning and final acceptance remain blocked until their integration is complete. Existing macOS and Omarchy behavior is preserved. Operator components are under [experiments/windows-kvm](../experiments/windows-kvm/README.md); no deployment addresses, keys, seed media or raw desktop captures belong in Git.

## Tested baseline — 13 November 2026

Linux x86-64 with hardware KVM, QEMU 10.2.1, libvirt 12.0.0, OVMF Secure Boot and software TPM 2.0. The disposable guest uses Windows 11 Enterprise 90-day evaluation, four vCPUs, 8 GiB RAM and a 96 GiB sparse SATA disk with inbox e1000e networking. This does not qualify Windows Pro, virtio, GPU passthrough, Windows on Apple Silicon or cloud providers.

CuaDriver 0.49.3 Windows x86-64 is a **prerelease**. Archive SHA-256: `1f8caf9b0a5577c559d95f12cfc55584bad32edffe5b49f5e700ed3ddc573566`. Sigstore verification passed with identity `https://github.com/trycua/cua/.github/workflows/cd-rust-cua-driver.yml@refs/tags/cua-driver-rs-v0.49.3` and issuer `https://token.actions.githubusercontent.com`. The installed PE signature was Valid. The driver runs under a standard guest account in its interactive session with a Limited scheduled task; Secure Boot and TPM readiness were independently confirmed.

## Security and transport

- Dedicated agent/viewer identities see only the assigned VM. Other-domain reads/mutations and QEMU monitor access are denied. Actual open/connect checks confirmed that only the viewer reaches the private console socket and only the agent reads the guest runtime key.
- Forced SSH commands separate agent status/MCP from viewer console/lifecycle. Shell requests and cross-role operations were refused.
- Browser streaming works through the private Unix console and restricted SSH relay. There is no TCP VNC listener. The new no-auth RFB path requires explicit Windows/private-Unix configuration and exact relay metadata; released Lume/password-VNC configurations cannot silently downgrade.
- Guest probes could not reach host SSH or the tested LAN SSH endpoint, while public HTTPS worked. These sample the policy, not every address/port. The spike firewall was session-only; the production persistence follow-up below supersedes that limitation.
- Permanent autologin is disabled; bootstrap task, guest seed secrets and cached answer files were removed, and installation media ejected. Temporary setup administration remains solely for acceptance and must be retired afterward.

## Real Hermes results and targeting corrections

An isolated Docker Hermes profile with the configured Qwen3.8 model opened Edge and reached Google using only computer_use. Both the HTTPS address and page were independently observed in the private viewer. Inputs used per-action operator approvals: this is supervised model acceptance, not autonomous approval-mode certification.

The initial Notepad attempt guessed a taskbar coordinate and hit a driver exact-HWND activation refusal. OwnMachine stopped writes for operator review. A later identity-based launch succeeded; exact UIA value assignment produced the requested document text. Batched foreground typing had delivered incomplete text, which the model detected rather than treating as success.

The adapter now resolves Windows display names through unique discovered process identities, recognizes advertised UIA `invoke` actions, and maps explicitly foreground modifier shortcuts to the driver's modifier-capable `press_key` API. The driver's XAML `hotkey` path otherwise searches visible menu accelerators even for foreground requests. Exact window admission, capture invalidation, per-action approvals and the human-control gate remain enforced; no automatic fallback or elevation was added.

Hermes's category-provider loader retained the old module across normal plugin reloads and profile changes in the tested gateway. The live acceptance uses a test-only provider directory alias in a separate profile to load the new module without restarting production. This is test deployment plumbing, not a production plugin rename. A normal fresh process loads the standard `ownmachine` package. Source is not patched into Hermes core.

The corrected provider completed the Notepad save through real Hermes: foreground Ctrl+S opened a separately discovered Save As window, Hermes entered the full destination and pressed Return, and the final capture showed a saved title without an unsaved marker. Independent administrative readback confirmed the exact requested 54 bytes, SHA-256 `e739a1fa0f7e83389905acea18361db016a4494d452f9749796be9a3adc6ad91`. No file-writing shell or API completed the model task.

The viewer's graceful shutdown succeeded. Its subsequent start was refused by libvirt because the original per-domain policy omitted network dependencies. `update-network-acl.py` is a reviewable administrator step scoped to the viewer and the configured dedicated network/ports; it does not restart services. Do not share that network with unrelated VMs. After applying it, viewer start succeeded. The operator reran all 18 boundary checks, including configured versus unrelated network reads/mutations, and reported all true. The combined restart initially failed at start; the subsequent separate viewer stop/start cycle passed.

The portable read-only `probe-saved-file.py` compares exact content and SHA-256 and records the guest boot timestamp, independently of model claims. The first shutdown/start exposed Windows Fast Startup: the file survived but the boot timestamp did not change. Provisioning now disables hibernation and rejects failure to do so. After applying that setting to the test guest, viewer stop/start changed the boot timestamp and preserved all 54 bytes and the identical SHA-256. After operator sign-in, the standard-user interactive driver returned to ready without repair. Permanent autologin remains off.

Post-boot real Hermes acceptance also reopened the saved file and read its exact text. This run needed operator intervention: UIA `set_value` on the Open dialog's filename Edit was resolved by the driver to its enclosing ComboBox and refused with `option_not_found`. OwnMachine blocked writes for review. After independent visual inspection and explicit acknowledgement, the model took a fresh capture, used explicitly foreground typing into the focused filename field and Return, then captured the reopened document. Independent readback again matched the original hash. This is a supervised passing recovery path, not proof that filename ComboBox value assignment or unattended recovery works. App launch reported a window-discovery timeout before a subsequent window listing found Notepad; delayed launch discovery also needs further qualification.

## Filename-control compatibility fix

CuaDriver 0.49.3 routes native ComboBox child Edit values through option selection, so a free-form filename can fail even though the snapshot advertises `set_value`. OwnMachine now follows snapshot parent indices to identify Windows Edit descendants of ComboBoxes, removes that unsupported action from the model-facing capture, and preflights an attempted value write without dispatching it. Plain Edit fields and ComboBox option selection are unchanged. The capture explains how to use explicitly requested foreground keyboard input after confirming focus, followed by value verification. There is no automatic input-mode fallback, filename-specific label matching, or review-gate reset. Existing human/paused/pending gates still take precedence. This is an adapter compatibility fix; it does not patch the upstream driver's native ComboBox implementation.

Tests cover capability filtering, no dispatch/no pending marker for the unsupported operation, preserved plain-edit and combo-selection routes, explicit typing, capture invalidation, platform scoping, human takeover and pre-existing uncertain outcomes.

### Live rerun

The updated installed plugin completed a real Docker Hermes save-and-reopen test with the same Qwen3.8 model. The filtered capability note appeared in live dialog captures. The model saved the 48-byte text `OwnMachine filename control acceptance verified.`, opened its path through Notepad's Open dialog, and captured the matching document. Independent administrative readback before and after reopen matched SHA-256 `d2b923a103a18f5195db54e7b19a097b66ba20cf829c97711bed5d2b9f8ef71c`; the viewer independently showed the same text. No filename-control failure, manual desktop input, or pending-action acknowledgement was needed during the passing sequence.

This was guided, supervised acceptance: per-action Allow once approvals remained enabled; explicit foreground keyboard delivery, English-guest filename focus guidance and sequential exact-dialog captures were supplied. An earlier general attempt was stopped before a background shortcut; another timed out on dialog navigation. The passing save run also reached its configured wall-clock budget before reopening, so a continuation completed Open without changing VM state or resetting a gate. This demonstrates the corrected filename path, not unattended general Windows reliability. The existing saved file from cold-start acceptance was preserved. Guest restart persistence was established earlier and was not repeated for this adapter-only change.

## Remaining graduation work

- Complete broader lifecycle qualification; the supervised saved-file, genuine guest cold-boot persistence and post-login driver checks passed. Host reboot is a separate, untested Windows surface.
- Qualify Windows foreground typing, shell/Start targets, background input, lock/sign-out and broader UIA behavior. Do not elevate the daemon to work around refusals.
- Integrate health/forced guest-key setup into fully clean provisioning and retire temporary setup keys automatically.
- Finish guided provisioning and rollback qualification; persistent policy and Windows doctor integration are implemented in the production follow-up below.
- Replace or explicitly qualify the prerelease driver pin; test additional Windows editions/hypervisor configurations separately.

The updated provider regression run passed 423 tests. Installed-plugin validation passed with the expected in-process callback and CLI-registration warnings. No production support claim follows from these checks.

Network ACL design follows [libvirt object-scoped Polkit policy](https://www.libvirt.org/aclpolkit.html) and [network-port API permissions](https://libvirt.org/html/libvirt-libvirt-network.html). Offline CI initially rejected the newly added Hermes-dependent tests as undeclared skips; their explicit platform declarations now accompany the tests. They passed in the local Hermes-backed 420-test run.

## Production adapter and persistence follow-up

The KVM adapter now runs behind the production host entrypoint. Runtime code,
configuration and guest key are root-owned; only the agent's dedicated group can
read that key. Domain/network identity, private console configuration and guest
standard-session readiness are checked before control. A narrow, read-only sudo
probe compares the live nftables rules with the installed policy and checks the
root-owned policy/configuration, network bridge/subnet and disabled VM autostart.
The installed systemd service restores only its dedicated table. An unsafe state
refuses access; graceful shutdown remains available.

Live administrator installation passed on the test host. The prerequisite check
initially misread a blank line before an enabled libvirt ACL directive; that parser
was corrected without restarting libvirt. Both production role probes passed,
cross-role operations were refused, and an extra restrictive DROP rule caused
readiness refusal. Restoring the intended table restored readiness. Both runtime
keys were then switched to the root-owned relay. The service reports enabled and
active; **physical-host reboot recovery is not yet tested for this backend**.

The browser connected to the production private console. Human reservation,
display wake input and return to paused mode worked; the previously saved Notepad
text remained visible. No VM or daemon restart was needed. The installed-plugin
doctor check exposed a Lume-only assumption; Windows-specific doctor checks now
have regression coverage and passed in an isolated installed Hermes profile.

See [the production checklist](windows-production-plan.md) for remaining setup,
release-image and qualification gates. These implementation/live checks do not
turn the earlier spike into a released Windows support claim.

Two end-to-end failures were fixed before accepting production MCP. The new
firewall initially dropped replies to host-initiated guest SSH; it now admits
established reply-direction traffic while retaining the guest-initiated host
block. After a dedicated firewall-service restart, guest probes still could not
reach host/LAN SSH and public HTTPS succeeded. All 18 production boundary checks
passed. The service's boot apply path installs/checks nftables without querying
libvirt, avoiding a boot-order dependency cycle; runtime checks still inspect
libvirt state. Physical host reboot remains a release qualification gate.

The MCP readiness subprocess originally inherited protocol stdin and could consume
the client's initialization message. It now receives DEVNULL; tests cover that
stream boundary and refusal of an unhealthy session. Installed Hermes doctor then
passed all readiness checks, with only the intentional paused-control warning.
A real Qwen3.8 Hermes run discovered/captured the existing Notepad window and read
its exact 48-byte sentence through the production relay. The private viewer and
independent file readback agreed. This was a read-only production transport test;
the earlier save/reopen test remains the write-task evidence.

Installed Hermes also saved a Windows plan with non-default storage/disk settings
and returned the expected temporary-key pairing handoff on `setup --next`.
Windows fresh provisioning and final verification/retirement are explicitly
blocked until their stage integration is finished; no macOS installer fallback
or fabricated completion is used. The Windows setup endpoint reuses source/plan
binding, authenticated progress import and interruption handling.

Final local regression validation: the complete 448-test suite passed. Installed-plugin validation passed with the expected in-process hook
and CLI-registration warnings. The live deployment preceded the last restart
revalidation safeguard; that safeguard is unit-tested, while another physical
host/guest restart is not claimed here.
