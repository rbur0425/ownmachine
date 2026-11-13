# Windows KVM development acceptance

Windows is an experiment in this branch, not a released support claim. The existing macOS and Omarchy setup choices are unchanged. Operator components are under [experiments/windows-kvm](../experiments/windows-kvm/README.md); no deployment addresses, keys, seed media or raw desktop captures belong in Git.

## Tested baseline — 13 November 2026

Linux x86-64 with hardware KVM, QEMU 10.2.1, libvirt 12.0.0, OVMF Secure Boot and software TPM 2.0. The disposable guest uses Windows 11 Enterprise 90-day evaluation, four vCPUs, 8 GiB RAM and a 96 GiB sparse SATA disk with inbox e1000e networking. This does not qualify Windows Pro, virtio, GPU passthrough, Windows on Apple Silicon or cloud providers.

CuaDriver 0.49.3 Windows x86-64 is a **prerelease**. Archive SHA-256: `1f8caf9b0a5577c559d95f12cfc55584bad32edffe5b49f5e700ed3ddc573566`. Sigstore verification passed with identity `https://github.com/trycua/cua/.github/workflows/cd-rust-cua-driver.yml@refs/tags/cua-driver-rs-v0.49.3` and issuer `https://token.actions.githubusercontent.com`. The installed PE signature was Valid. The driver runs under a standard guest account in its interactive session with a Limited scheduled task; Secure Boot and TPM readiness were independently confirmed.

## Security and transport

- Dedicated agent/viewer identities see only the assigned VM. Other-domain reads/mutations and QEMU monitor access are denied. Actual open/connect checks confirmed that only the viewer reaches the private console socket and only the agent reads the guest runtime key.
- Forced SSH commands separate agent status/MCP from viewer console/lifecycle. Shell requests and cross-role operations were refused.
- Browser streaming works through the private Unix console and restricted SSH relay. There is no TCP VNC listener. The new no-auth RFB path requires explicit Windows/private-Unix configuration and exact relay metadata; released Lume/password-VNC configurations cannot silently downgrade.
- Guest probes could not reach host SSH or the tested LAN SSH endpoint, while public HTTPS worked. These sample the policy, not every address/port. Host firewall persistence remains unfinished.
- Permanent autologin is disabled; bootstrap task, guest seed secrets and cached answer files were removed, and installation media ejected. Temporary setup administration remains solely for acceptance and must be retired afterward.

## Real Hermes results and targeting corrections

An isolated Docker Hermes profile with the configured Qwen3.8 model opened Edge and reached Google using only computer_use. Both the HTTPS address and page were independently observed in the private viewer. Inputs used per-action operator approvals: this is supervised model acceptance, not autonomous approval-mode certification.

The initial Notepad attempt guessed a taskbar coordinate and hit a driver exact-HWND activation refusal. OwnMachine stopped writes for operator review. A later identity-based launch succeeded; exact UIA value assignment produced the requested document text. Batched foreground typing had delivered incomplete text, which the model detected rather than treating as success.

The adapter now resolves Windows display names through unique discovered process identities, recognizes advertised UIA `invoke` actions, and maps explicitly foreground modifier shortcuts to the driver's modifier-capable `press_key` API. The driver's XAML `hotkey` path otherwise searches visible menu accelerators even for foreground requests. Exact window admission, capture invalidation, per-action approvals and the human-control gate remain enforced; no automatic fallback or elevation was added.

Hermes's category-provider loader retained the old module across normal plugin reloads and profile changes in the tested gateway. The live acceptance uses a test-only provider directory alias in a separate profile to load the new module without restarting production. This is test deployment plumbing, not a production plugin rename. A normal fresh process loads the standard `ownmachine` package. Source is not patched into Hermes core.

The corrected provider completed the Notepad save through real Hermes: foreground Ctrl+S opened a separately discovered Save As window, Hermes entered the full destination and pressed Return, and the final capture showed a saved title without an unsaved marker. Independent administrative readback confirmed the exact requested 54 bytes, SHA-256 `e739a1fa0f7e83389905acea18361db016a4494d452f9749796be9a3adc6ad91`. No file-writing shell or API completed the model task.

The viewer's graceful shutdown succeeded. Its subsequent start was refused by libvirt because the original per-domain policy omitted network dependencies. `update-network-acl.py` is a reviewable administrator step scoped to the viewer and the configured dedicated network/ports; it does not restart services. Do not share that network with unrelated VMs. Live application and cold-start persistence verification are pending that administrator step. This is not yet a passing viewer restart result.

The portable read-only `probe-saved-file.py` compares exact content and SHA-256 and records the guest boot timestamp, independently of model claims.

## Remaining graduation work

- Complete guest cold-start and post-login driver acceptance after the scoped network-policy update; saved-file acceptance passed.
- Qualify Windows foreground typing, shell/Start targets, background input, lock/sign-out and broader UIA behavior. Do not elevate the daemon to work around refusals.
- Integrate health/forced guest-key setup into fully clean provisioning and retire temporary setup keys automatically.
- Persist and revalidate host firewall policy, add supported provisioning/onboarding/doctor integration and review rollback paths.
- Replace or explicitly qualify the prerelease driver pin; test additional Windows editions/hypervisor configurations separately.

The final provider regression run passed 420 tests. Installed-plugin validation passed with the expected in-process callback and CLI-registration warnings. No production support claim follows from these checks.

Network ACL design follows [libvirt object-scoped Polkit policy](https://www.libvirt.org/aclpolkit.html) and [network-port API permissions](https://libvirt.org/html/libvirt-libvirt-network.html). Offline CI initially rejected the newly added Hermes-dependent tests as undeclared skips; their explicit platform declarations now accompany the tests. They passed in the local Hermes-backed 420-test run.
