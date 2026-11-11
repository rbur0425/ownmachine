# OwnMachine clean-candidate acceptance

Observed on 2026-11-10. Candidate: `f6ed1c6c291688afbf3f025f7708659ae49a000a`
(the merge of PR 21). This is an unpublished acceptance candidate, not a release.

The operator authorized deleting/recreating the former laptop test guest after
confirming its other agent had finished. The old guest was gracefully stopped,
its shared control gate paused, and only that named guest was deleted. Its disk
directory was confirmed absent. Free host space rose to approximately 69.6 GiB.
The Studio guest was not changed.

Fresh provisioning uses the fixed candidate, 4 CPUs, 8 GiB RAM, a 64 GiB sparse
disk and 1900×1200 display. The default 60 GiB preflight budget passed. A separate
operator monitor samples free space and stops provisioning below 8 GiB headroom.
The existing administrator-installed loopback firewall protects the same fixed
verification port; this run does not certify renamed firewall reboot persistence.

Source and plugin bundles were built from the clean candidate and verified.
An extracted source bundle was mounted read-only into a separate Hermes Docker
container. The operator initially extracted it with restrictive directory modes,
preventing container reads; after fixing source-mount permissions, the installer
passed in a new home. An earlier validation attempt had already initialized the
first home, and the installer correctly refused to overwrite it. These are test
harness setup corrections, separate from the guest ownership regression under test.
Plugin validation passed; the container reports its existing pnpm artifact warning.

Local validation: 215 tests, 193 passed and 22 expected Hermes-only skips.
Guest provisioning completed with exit code zero. Observed initial free space was
69.62 GiB, minimum 47.15 GiB and approximately 47.53 GiB at completion; concurrent
host activity and cache behavior mean this is not a universal space requirement.

The corrected lifecycle installer created `.local`, `.local/lib` and its OwnMachine
support directory owned by the guest account, mode 0700. The subsequent signed
driver, permission-guide and MCP installers completed without changing ownership
by hand, reinstalling a partial app, or repairing guest DNS. Key authentication,
password rotation, disabled password SSH, autologin and keychain setup passed.
The guest runs macOS 26.6.2.

After a guest-only lifecycle restart, the guide appeared at 1900×1200. With explicit
operator approval, both guest permissions and final capture consent were enabled
through browser input. Adding CuaDriver through Applications and choosing Quit &
Reopen worked. Hermes doctor then reported READY, including MCP. No host permissions
were granted.

The first model launch could not resolve the configured endpoint hostname in the
isolated container. The operator added its deployment-specific host mapping and
restarted before any GUI actions occurred.
Model acceptance must have one capture owner and retain standard per-write
approvals. Do not run independent AX captures while the model is active. Verify
saved content independently after the model finishes. Never commit credentials,
model transcripts, private screenshots or runtime configuration.

## Model task instructions and scope

The operator identified the configured endpoint as Qwen3.8 Flash Next; the served
weights were not independently attested. Each run used the real Hermes agent,
native `computer_use` provider and standard per-write approvals. The model chose
GUI actions; the operator approved bounded writes but did not complete GUI steps
for it. Independent verification occurred only after each run ended.

For reproducible small-model acceptance, give explicit success criteria:

1. Create a new TextEdit document without changing existing documents.
2. Enter the specified unique text and read it back from a fresh capture.
3. Save under the specified unique filename in the observed Desktop destination.
4. Verify the saved title and exact text, then stop. An independent verifier checks
   file existence; do not add optional title-bar or metadata interactions.

Prefer supported AX `set_value` for text fields. Capturing a window does not focus
it; target keyboard input explicitly and inspect transitions. Do not click disabled
controls or elements without the required action. Inspect location choices before
selecting them. Every capture replaces previous bindings; pixel bindings are
single-use and may expire while awaiting approval. On a review-required result,
stop writes until the operator inspects and acknowledges the outcome. Instructions
do not relax approvals, capture binding, or the shared human-control gate.

## Observed model attempts

- First connected run saved its requested document. Independent AX inspection
  matched the saved title and exact text; a separate guest SSH metadata check
  confirmed the Desktop RTF existed (434 bytes). An unnecessary post-save click
  on a disabled title-bar control failed and set the review-required gate. The
  model stopped correctly. This is verified task completion, not an error-free run.
- The second run used more detailed staged instructions. Its pixel click was
  refused with `capture_expired` before typing or saving. The model stopped and
  independent inspection confirmed the first saved document remained unchanged.
  The expiry cause/threshold was not established; this attempt does not certify
  model-driven pixel input. The operator inspected the outcome before clearing
  the review gate for a separate AX-focused run.
- The third run used AX text entry and staged instructions. It created a separate
  document, entered and read back the exact text, inspected the save destination,
  saved, verified and stopped without a driver review gate. A shortcut initially
  opened a save sheet for a different blank window; the model detected this,
  cancelled it and recovered without modifying the earlier saved document.
  Independent native-provider AX verification matched the new saved title and
  exact text. Separate guest SSH metadata verified its Desktop RTF (435 bytes).
  Rechecking the first document matched its original content hash. Control was
  left paused with no pending action.

The clean guest ownership regression is closed for this tested candidate, and the
real-model AX document task is independently verified. This is not evidence of
unattended permission approval, universal model reliability, reliable model pixel
input across approval delays, native-viewer password paste, or renamed physical-host
service reboot persistence. The temporary laptop relay and existing firewall were
reused; no physical host reboot was performed. Private deployment receipts,
transcripts, credentials and captures remain outside version control.

## Viewer control-button follow-up

A subsequent viewer-only update highlights the current controller, exposes its
pressed state to assistive technology, and restores visible focus to the clicked
handoff button once the asynchronous status refresh enables it. Browser checks
confirmed both human reservation and return-to-agent selected the corresponding
button and retained focus. Moving focus elsewhere is respected. This update does
not change the provider or guest used for the model acceptance above.
