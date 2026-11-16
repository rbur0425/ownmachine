# OwnMachine v1.1.0 release artwork

Generated with **codex-imagegen-cli**, native Codex image backend, high quality,
requested 1536×864; delivered 1672×941 WebP. Visually reviewed for text, scope and
privacy claims. These are labelled promotional illustrations, not screenshots or
acceptance evidence. Existing real viewer captures remain unchanged.

| Asset | Message |
| --- | --- |
| [Three-platform banner](platforms.webp) | Your agent. Its own desktop. |
| [Windows](windows.webp) | Windows work. Your workspace. |
| [macOS](macos.webp) | Your Mac stays yours. |
| [Omarchy](omarchy.webp) | A Linux desktop of its own. |

Windows means Windows 11 Enterprise Evaluation x86-64 on Linux KVM. macOS and
ARM64 Omarchy use Apple Silicon with patched Lume. Omarchy foreground input
requires its native module. Screenshots/app text follow the configured model
provider; the illustrations do not promise that data never leaves the machine.

The exact prompt set is in [prompts/](prompts/). Generation command for each asset:

```sh
codex-imagegen-cli generate --prompt-file PROMPT.txt --out ASSET.webp \
  --output-format webp --quality high --size 1536x864
```

These assets are prepared for the Windows release. They do not update the public
Hermes catalog automatically; pin their final published asset commit in that
separate catalog update. No private desktops, access tokens or host identities
were supplied to image generation.
