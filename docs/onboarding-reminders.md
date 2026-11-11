# Explicit onboarding reminders

Installation enables no reminders. Use `hermes ownmachine remind ...` in an
operator terminal or `/ownmachine remind ...` in an explicitly authorized chat.
`setup --later` offers reminder choices without scheduling anything or stopping
an active setup process. `setup --next` explains the next checkpoint or handoff.

```sh
hermes ownmachine remind later                    # next-visit preview
hermes ownmachine remind later --confirm <preview-token>
hermes ownmachine remind later --mode tomorrow    # scheduled preview
hermes ownmachine remind later --mode tomorrow --confirm <preview-token>
hermes ownmachine remind status
hermes ownmachine remind off
```

Review the displayed destination before confirming. A preview expires after 15
minutes. Chat consent binds the authenticated platform, sender, chat and optional
thread. Terminal scheduled delivery requires an explicit
`setup_reminder_destination` containing platform, user_id, chat_id and optional
thread_id; it never guesses a recipient. `setup_reminder_timezone` controls the
preview time zone (default UTC). Tomorrow means 24 hours after the preview.

Next-visit reminders need no job. They can appear when a local CLI/TUI/Desktop
session opens or resumes, on the next admitted message from the approved chat
sender, or on a matching OwnMachine command. Chat admission is a next-message
hook, not a promise to detect every new chat session. JSON and reminder-management
commands do not emit command nudges. Terminal consent follows the active profile,
not a terminal process. No hook consumes the user's message or starts setup.

Tomorrow creates one paused, no-model Hermes cron job. OwnMachine obtains a
short-lived ticket through the public `hermes gateway attach --json` contract,
checks the matching profile/protocol/build, and inspects `cron.manage` results.
It verifies the unique job's script, destination, disabled state and absent next
run before resuming. Tickets are never persisted or logged. No credential or
scheduler store is read. The helper lives in that profile's documented `scripts`
directory and uses the public CLI with the same profile home. A missing gateway
or unsupported method refuses scheduling; status reports unavailable delivery.

At execution the helper rechecks consent, configuration, sender authorization,
setup completion, due time, budget and live job binding. Errors produce no output
and exit successfully, so a helper failure cannot send a failure notice to chat.
Successful reminders contain fixed non-secret text; Hermes may add its standard
cron wrapper. Off and completed setup disable consent before job cleanup. Failed
cleanup is reported and never silently re-enables delivery.

`setup_reminder_limit` is 1–3 (default 3), at least 24 hours apart. A verified stage
advance resets the count. Scheduled delivery is counted only after reconciliation
with a successful run and no reported delivery error or unverified delivery;
printing helper output alone is not confirmation. A scheduled opt-in creates one
reminder, not an automatic recurring chain. Use status to reconcile its result.
Next-visit delivery is counted only when the public message result accepts it.
Interrupted or uncertain operations stay quiet and require inspection; do not
repeat creation to recover a lost response.

No reminder contains credentials, viewer links or desktop content. A reminder
cannot provision, start a VM, invoke a model or grant guest permissions.
