# Intel macOS guest implementation plan

**Decision proposed for review:** run a native x86_64 macOS guest on a physical Intel Mac that the operator controls. Hermes can run on another machine or in Docker and reach the Mac through the existing SSH relay. Start with a hardware feasibility test. Intel macOS support has not been qualified.

## First target and stop conditions

Try a fully patched macOS Sequoia 15 guest on a Sequoia-compatible Intel Mac running macOS, with a licensed Parallels Desktop 26 Pro or Business installation. Confirm the exact model, host and guest builds, edition, management CLI availability and vendor support before buying equipment or writing a backend. Parallels lists Sequoia for Intel guests with a footnote requiring a Mac that supports it as a host OS. Its Intel installation guide describes using an Apple installer app or Recovery. Desktop 27 is Apple-silicon-only, so pin the tested 26.x build and record its support horizon. [Guest matrix](https://kb.parallels.com/en/124223) · [Intel installation guide](https://kb.parallels.com/en/125105) · [Intel product lifecycle](https://kb.parallels.com/en/131175)

The existing Apple-silicon Lume installer uses a different boot path. The x86_64 Omarchy work supplies reusable onboarding and isolation tests, but its Linux KVM host is outside this macOS target. Use Apple-sourced media and have the operator check the applicable host and guest license, purpose and instance limit. Sequoia’s virtualization grant in §2B(iii) is conditional. Distribute OwnMachine scripts only and have each operator obtain their own installer and hypervisor license. [Apple virtualization architecture](https://developer.apple.com/documentation/virtualization/running-macos-in-a-virtual-machine-on-apple-silicon) · [Sequoia license](https://www.apple.com/legal/sla/docs/macOSSequoia.pdf)

## 1. Prove the three dependencies on hardware

| Experiment | Evidence required to proceed |
| --- | --- |
| Provision and cold-start | Create a guest from Apple media, complete Setup Assistant, shut down fully, then start it by immutable VM ID under the dedicated host account. Record guest architecture and OS build, required host login state, peak disk use, RAM and any manual steps. Confirm the operator can use FileVault normally. |
| Run CuaDriver natively | The [existing installer](../scripts/install-guest-driver.sh) downloads a universal archive. Inspect the x86_64 slice, minimum macOS version, artifact integrity and signing identity. In a standard guest account, grant guest permissions and demonstrate window discovery, actual screen capture and targeted input in TextEdit. Record which actions require foreground focus. |
| Isolate the viewer | Demonstrate a vendor-supported console or guest display transport reachable only through the viewer relay. Try an unrelated unprivileged local account, the agent identity, the guest network and a second LAN machine. All unauthorized connections must fail. Verify that human reservation suppresses agent input and return-to-agent disconnects human input. |

If the driver cannot execute on a maintained guest OS, the console cannot isolate local users, or the hypervisor requires giving the agent host GUI or administrator access, record the failed gate and stop. A guest boot or a working vendor GUI alone is insufficient.

## 2. Implement the smallest backend

- Add an explicit Intel macOS profile only after the spike passes. Keep the existing macOS profile and existing saved configurations working. Validate host architecture, backend and console transport as one configuration update. Persist the VM UUID and refuse ambiguous names, replacements or a mismatched backend.
- Reuse the macOS guest driver, provider, MCP contract, human reservation, SSH-role enforcement and final screenshot verification. Isolate vendor-specific inventory, start, status, graceful shutdown and console connection in a host adapter. Use bounded timeouts, argument lists and the existing minimal SSH environment.
- Configure setup, agent and viewer SSH aliases, storage, resource limits, resolution, network and console transport outside the repository. Preflight the exact vendor edition/build and free space. Give the operator an actionable handoff if the vendor requires a signed-in host account.

## 3. Enforce the permission boundaries

| Actor or resource | Required boundary and negative test |
| --- | --- |
| Host administrator | Install trusted host components and any required persistent firewall rules in a separately approved step. Keep relay code and security configuration administrator-owned. Recheck effective isolation before start and viewer attachment. Changing or removing a required rule must make the operation fail closed. |
| Temporary setup identity | Pin the host key, source revision and VM identity. Allow only the documented setup stages. After final verification, retire the exact temporary public key, prove a new connection with it fails, and recheck both runtime identities. Retirement must survive interruption and retry. |
| Hermes agent and human viewer | Give each a separate forced-command SSH key. Agent gets status and guest MCP. Viewer gets status, private console and approved lifecycle operations for one VM. Deny shell, forwarding, cross-role operations and access to a second VM. Keep viewer credentials outside shared control state. |
| Guest user | Run CuaDriver as a standard user in the signed-in guest session. Reserve the viewer for the operator to approve Accessibility, Screen Recording and any capture prompt **inside the VM**. Verify each grant independently, restart the guest app when requested and test revoking each grant. Keep host desktop permissions, TCC, SIP and FileVault intact. |
| Storage and networking | Disable host folder sharing, shared clipboard, device passthrough and unnecessary guest integration. Enforce private file modes under both 022 and 077 umasks. Stage verified media in a private directory and operate on verified file descriptors across privilege boundaries. Reject symlinks, external disk references and substituted bundles. Test guest-to-host administrative isolation and check logs, process arguments and guest-visible shares for console secrets. |

Use the [Omarchy security acceptance](omarchy-security-acceptance.md) and [existing isolation protocol](security-isolation.md) as the regression baseline. Record the identity, attempted operation and observed denial for each boundary. Successful agent and viewer operations on the assigned VM are positive controls.

## 4. Guide the installation from Hermes

1. Preflight the remote Mac before creating anything. Show the exact software, disk, account and manual consent requirements. Have the operator confirm the host fingerprint and target VM.
2. Persist authenticated stage checkpoints for media, registration, isolation, first login, driver, permissions, viewer and final verification. Bind them to the plan, source and VM identity. Resume only after checking the actual state. Test interruption immediately after disk creation, password rotation and setup-key removal.
3. Keep manual prompts specific. Direct the operator to the vendor UI for installation when required and the guest UI for consent. Link each doctor finding to its guide section and offer existing opt-in reminders only to the authorized sender.
4. Distinguish unreachable host, stopped guest, unavailable guest SSH, signed-out or locked desktop, missing permission, driver still starting, input unavailable and unsafe console. Poll transient startup with a deadline. Preserve read-only diagnostics where safe. Never replay input after reconnecting.

## 5. Qualify and define the support claim

- Run two clean installs, including one from a fresh Docker Hermes profile and one interrupted installation. Validate the packaged plugin. Exercise existing Apple-silicon macOS and Omarchy paths for regressions.
- Have Hermes open TextEdit, type a unique value, save it, close it and reopen it using desktop tools. Independently verify the file contents and a decoded guest screenshot. Repeat after a full guest shutdown and cold start. Verify focus targeting and record foreground-only operations.
- Exercise browser mouse, shifted keyboard input, human takeover, return to agent, guest lock/unlock, sign-out/in, driver restart and gateway restart. Confirm stale sessions cannot inject input. Repeat the role-denial and console tests after restarting the host with the operator’s approval.
- Rehearse an upgrade and rollback with saved guest data. Record whether driver replacement requires renewed consent. Define when host, guest, hypervisor or driver updates require requalification. Retire the supported combination when a required component loses security maintenance and no replacement passes.
- Publish the exact tested hardware and version matrix, operator handoffs, resource measurements and redacted acceptance results. Limit the claim to tested combinations. Track Intel cloud Macs and other hypervisors separately.

**Next action:** identify an available physical Intel Mac and confirm its model supports Sequoia. The first deliverable is a short hardware report recording pass or fail for all three experiments. This plan makes no hardware acceptance claim.
