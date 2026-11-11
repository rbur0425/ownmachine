# Docker onboarding and reminder acceptance

Candidate branch: `feature/onboarding-docker-reminders`.
Hermes reference: `3bcd071226d3d605a2bb3b4f3933e7d583e189d6`.
These results describe observed tests, not a claim that every onboarding path has
completed. Private destinations, account names, paths and keys are omitted.

## Public scheduler route

- Created a no-model job paused through the public CLI. The authenticated gateway
  listing confirmed its exact unique name, script, destination, disabled state
  and absent next run before it was resumed.
- An isolated resumed silent script completed successfully without output.
- An isolated resumed failing script reported an error; failure delivery was
  configured local, and no external destination was used for this test.
- Sent exactly one fixed reminder through an existing Docker Hermes default
  profile to an explicitly approved Discord channel. Public job status was `ok`,
  with neither a delivery error nor unverified delivery. The user independently
  confirmed receipt, including Hermes's standard cron wrapper. Removed the job
  and helper afterward; no repeat remains scheduled.
- This Hermes version refuses manual execution of paused jobs. Acceptance resumed
  the inspected job before triggering it once. The plugin's delivery-time checks
  still protect early, repeated or altered executions.
- Unit coverage includes due-time checks, edited destinations, opt-out, uncertain
  creation, silent helper failure, unconfirmed delivery and unavailable gateways.

- A cron script running in Hermes’s cleaned environment invoked the public plugin
  CLI and read the exact profile’s reminder preview state successfully.

- Stopping only the isolated profile gateway caused tomorrow scheduling to refuse;
  no job or automatic gateway start occurred.

## Docker-to-Mac setup (in progress)

Separate operator, agent and viewer OS users and private SSH keys were prepared.
Only public keys and independently trusted host-key material crossed machines.
The operator ran remote preflight and build verification through Hermes and the
restricted setup endpoint. The signed patched Lume app was explicitly adopted,
not rebuilt or overwritten. A fresh guest was provisioned in non-default
storage whose path includes a space. The old test guest was deleted only after
explicit approval. Host firewall protection remains active. Remote firewall, relay, keys, hardening
and driver stages all passed. The older relay file differed, so setup refused to
overwrite it; inspection confirmed no relay mutation, and the old file and failed
checkpoint were preserved before the explicit fresh-install retry.

The current fixture initially copied the candidate plugin for testing. This is
not proof of installation through `hermes plugins install` at a public Git pin.
Final packaged installation, guest permissions, Docker viewer input, native
capture and setup-key retirement remain pending in this acceptance run.
