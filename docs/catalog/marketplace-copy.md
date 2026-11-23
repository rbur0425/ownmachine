# Marketplace copy for the x86-64 Omarchy release

Use this copy when the catalog pin advances to a published release containing `omarchy-kvm`. The historical catalog YAML describes its original pinned release.

## Short description

Give Hermes its own Mac, Omarchy or Windows VM to test apps, scrape websites and automate desktop work with private SSH access and you in control.

## About

Give your Hermes agent a desktop of its own. Test apps, scrape websites and finish
repetitive workflows in a dedicated Mac, Omarchy or Windows virtual machine,
without handing over your personal desktop or tying up your mouse.

Keep the workspace on infrastructure you control. OwnMachine connects Hermes to
the VM host over private SSH, and your apps and saved files stay available between
sessions. Watch from your browser, pause the agent, take over with your keyboard
and mouse, then hand control back when you're ready.

One guided setup brings together the VM, desktop control and browser viewer, with
resumable progress and doctor checks to help you through manual steps.

**Privacy:** You control the VM and its contents. Screenshots and app text used
by Hermes follow your configured model provider; a cloud model can receive that
data. Private SSH protects the connection, not every downstream use of the data.

**Choose your host.** An Intel or AMD Linux host with hardware KVM can run x86-64 Omarchy or Windows 11 Enterprise Evaluation. Both work without a Mac. Apple Silicon hosts can run macOS or ARM64 Omarchy using patched Lume. Hermes can connect to either host over SSH. See the [platform guides](../evaluator-quickstart.md#choose-the-vm-host) for administrator handoffs and guest sign-in.

## Preserve the catalog disclosures

Keep the reviewed security disclosures alongside the benefit-led description:
OpenSSH uses operator-configured aliases, agents and keys; remote setup executes
reviewed provisioning stages; screenshots, accessibility text and input flow
through the relay; shared control state is stored locally; opt-in scheduled
reminders use a helper script and Hermes cron jobs. Declare websockets and Pillow
dependencies, in-process execution requirements, and the PolyForm Noncommercial
license. Do not remove these disclosures to shorten the marketing copy.

The marketplace may render its catalog description as both the lead and About;
put the short benefit statement first, followed by required disclosures. Use the
README for the expanded paragraphs if the catalog has no separate About field.
