# Viewer dependencies

noVNC 1.6.0 is vendored from upstream commit
`a8dfd6a3ea3c74244f5ebdaa5a7f1023007a7820` (tag `v1.6.0`).
Only `core/`, `vendor/`, AUTHORS and license files are included.
Local patch: `core/rfb.js` normalizes a mouse-down with a zero `buttons` mask
using the event’s explicit left/middle/right `button`. This fixes the macOS
Safari input path observed during laptop acceptance; ordinary chord masks and
releases are preserved. `node tests/viewer-pointer.mjs` covers the handler.
The core is MPL-2.0; bundled pako carries its upstream notices. See
`vendor/novnc/LICENSE.txt` and the accompanying full license texts.
Source: https://github.com/novnc/noVNC/tree/v1.6.0

PyCryptodome 3.23.0 is an explicit operator-installed viewer dependency for legacy
VNC DES challenge-response compatibility. It is not a plugin dependency. The
browser never receives the VNC password; the bridge authenticates upstream over
SSH before accepting an RFB client. Neither dependency updates itself at runtime.
