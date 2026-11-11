# Actual viewer screenshots

Captured on 2026-11-11 from the real noVNC viewer and dedicated acceptance guest
at a 1440×1120 browser viewport. Guest TextEdit contains demonstration text typed
for these captures; the background acceptance document also contains test text.
These are browser-page captures, with no address bar, access link, credentials,
private host identities or personal documents. No UI state was fabricated or
image content retouched. Each image was visually reviewed before committing.

- `human-control.png`: live stream, human reservation selected and focused.
- `agent-control.png`: returned to agent, viewer input disabled, return button
  selected and focused. This is a handoff screenshot, not a model-task result.

The capture session verified browser input and both state transitions. The
workspace was returned to paused after capture. The two handoff captures used the v0.6.0 security-preview viewer.

- `google-task.png`: a separate read-only native capture after the successful
  Qwen-driven Safari task on fix commit `71049a2`. It shows the public Google
  page and URL, without account sign-in or private deployment identifiers.
  This is the actual 1456×786 capture, not an illustration or reconstructed UI.
  See the model acceptance log for the initial failure and passing rerun.
