# Screenshot and setup-key retirement acceptance

Tested on 2026-11-11 against current Hermes source
`3bcd071226d3d605a2bb3b4f3933e7d583e189d6`, using an isolated Hermes profile and
the freshly installed laptop guest from the preceding hardening acceptance.
No Studio VM or host reboot was involved.

## Observed live results

- Completed remaining Apple first-login choices without an Apple Account. The
  guest permission guide opened normally. Enabled CuaDriver Accessibility and
  Screen Recording with the user's explicit approval, quit/reopened the driver,
  then approved its separate capture prompt. No host desktop permissions changed.
- Native paste into the protected authentication dialog did not work reliably;
  direct key events with the saved grouped password succeeded. This remains a
  reason to document typing the guest password, not promise clipboard support.
- Left viewer control paused. A real `hermes ownmachine setup --run verify --json`
  invocation performed authenticated SSH role/status checks, the viewer's VNC
  probe, and a valid 1456 × 920 PNG capture through OwnMachineBackend, the native
  Hermes computer_use provider. This is not an auxiliary vision-model call.
- `setup --run verify --apply --json` repeated acceptance and removed the newly
  paired temporary setup entry. A fresh SSH attempt was refused with public-key
  authentication denied; the separate runtime identity still reported the guest
  and driver ready. Hermes persisted completion with screenshot metadata only.
- An independent byte comparison confirmed unrelated authorized-key contents
  were preserved. No runtime key or unrelated operator authorization was removed.

The viewer key stayed under a separate account. The Hermes profile received only
its restricted agent key and the temporary setup identity. Addresses, account
names, credentials, runtime state and desktop pixels are excluded from Git.

## Reminder integration findings

Actual separate Hermes CLI processes passed preview, explicit confirmation,
state persistence, one terminal nudge, daily duplicate suppression and opt-out.
No real external message was sent and no cron job was left behind.

The attempted scheduled path exposed a real API limitation: standalone plugin
CLI dispatch returned `Unknown tool: cronjob_manage`. That also affects a
scheduled helper's required inspection of its live job and destination. The
scheduled implementation was removed before publication; `--mode tomorrow`
explicitly reports unavailable. Only the tested next-OwnMachine-command path is
implemented. Automatic session-open nudges lack a verified sender/thread hook
and remain open. See [reminder controls](onboarding-reminders.md).

Unit coverage includes exact-key preservation and mismatched authorization,
capture failure before retirement, no removal in read-only verification,
refusing completion without proven SSH denial, stale acceptance identities,
already-completed calls, reminder consent expiry, profile/destination changes,
thread isolation, accepted versus failed delivery, progress versus retry budgets,
opt-out/completion suppression and interrupted-delivery reservations.

## Limits

This closes the fresh guest's consent, native screenshot and temporary-key
retirement acceptance. It does not claim a new model-driven desktop task,
external reminder delivery, unattended macOS consent, or a new physical-host
reboot test. Scheduled reminders remain blocked on a supported public API.
