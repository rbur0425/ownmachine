# Explicit onboarding reminders

Installation enables no reminders. Run either `hermes ownmachine remind ...` in
an operator terminal or `/ownmachine remind ...` in an explicitly authorized chat.

```sh
hermes ownmachine remind later --mode next-visit
# Review the displayed destination, then use its exact confirmation token:
hermes ownmachine remind later --mode next-visit --confirm <preview-token>
hermes ownmachine remind status
hermes ownmachine remind off
```

A preview expires after 15 minutes. Confirmation enables a fixed, non-secret
resume offer on the next matching OwnMachine command. It never starts a VM or
runs setup. Terminal and chat destinations are distinct; chat identity includes
the approved platform, sender, chat and optional thread. Changing setup identity
or withdrawing sender authorization disables prior consent. No credentials,
viewer tokens or desktop content are stored in reminder state or message text.

`setup_reminder_limit` is configurable from 1 to 3 (default 3). Nudges are spaced
at least 24 hours apart; retries do not reset the budget. A verified stage advance
resets the count, and fresh explicit consent can renew an exhausted budget.
Delivery is counted only when terminal output or Hermes's public message result
accepts it. An interrupted delivery reservation stays quiet; `remind off` clears
it before a new explicit opt-in. Unknown state versions are preserved for review.
Completion suppresses nudges. Off persists before any future delivery check.

`remind later --mode tomorrow` explicitly reports unavailable and creates no job.
Current Hermes exposes `ctx.dispatch_tool` but does not load `cronjob_manage` in
standalone plugin commands. A scheduled no-model helper therefore cannot perform
the required live job/destination check through that public API. OwnMachine does
not read private scheduler files or import scheduler internals to work around it.
A supported standalone scheduling/inspection API is required before enabling this
mode. Likewise, “next visit” does not mean opening an arbitrary Hermes session:
the session-start hook does not carry sufficient verified destination identity.

Actual external chat delivery and scheduled reminders remain acceptance work.
