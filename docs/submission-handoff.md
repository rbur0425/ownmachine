# Submission handoff — prepared, not submitted

## Deadline and required entry steps

The [Nous announcement](https://x.com/NousResearch/status/2118094256438936062)
states **November 11, 2026, 5 PM EST (22:00 UTC)**. The announcement is also indexed
on [Nous Research](https://nousresearch.net/). Checked on November 11; no deadline
extension is assumed. The owner's demo is separate from the stylized teaser.

1. Open a PR adding only `plugin-catalog/ownmachine.yaml` to
   [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), following
   [the catalog guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission).
2. Post a **working demo under 90 seconds** on X and tag **@NousResearch**.
3. Submit both links through the [official entry form](https://form.typeform.com/to/FwJLvOln).

The announcement's short links resolve to that guide and form. The public form
schema was inspected without sending answers. Required fields are plugin title,
plugin description, email address, Discord username, X demo post link and the
GitHub link to the **upstream catalog PR**. An OwnMachine development/release PR
is not that catalog PR. The owner supplies contact information; no identity is
invented or borrowed from local configuration.

Judging covers usefulness, reliability, polish and creativity. Show the actual
plugin working. The existing 15-second teaser is explicitly stylized and should
not be presented as live automation. The owner is producing the working demo.

## Ready-to-use wording

**Title:** OwnMachine — Give your AI agent its own desktop.

**Description:** Give Hermes a persistent macOS workspace on hardware you control.
OwnMachine combines native computer use, restricted SSH/MCP and a private streaming
viewer so you can watch, pause, take over and return control. Guided setup tracks
progress, explains administrator and guest-permission handoffs, verifies the desktop
and retires temporary setup access. Keep your personal desktop separate without
assembling a VM, automation driver and remote viewer yourself.

**Suggested X caption:** OwnMachine gives Hermes its own persistent Mac desktop.
Watch it work, pause it, take over in your browser and hand control back. This demo
shows the real plugin—not just a prompt. Built for the Hermes Agent Plugin
Hackathon. @NousResearch

The owner reviews/edits these drafts and supplies the video. No post or form has
been sent. Use the [release](https://github.com/rbur0425/ownmachine/releases/tag/v0.7.0)
and [evaluator quickstart](evaluator-quickstart.md) for installation details.

## Catalog package

Use the attached release asset **ownmachine-catalog.yaml** for the final immutable
release-commit pin and matching screenshot URLs. The source tree's
`docs/catalog/ownmachine.yaml` is a preparation draft pinned to reviewed content;
it cannot self-reference its own future merge SHA. The final release asset is
rendered after that SHA exists and validated separately. Version must match the
pinned manifest, and `subdir` must remain `plugin`.

The three screenshot subjects are human control, agent control and the independently
verified Google task. They contain no viewer token or deployment credential.
The repo README and plugin README explain manual handoffs and preview limits.
Use [catalog disclosures](catalog/README.md) in the entry PR and the exact release
validation summary; automated validation is not catalog admission.

The owner previously confirmed PolyForm Noncommercial 1.0.0 and operator-managed
OpenSSH eligibility. Retain full disclosure and await upstream review. Do not
claim a listing, successful hackathon submission or general security certification
before those events occur.
