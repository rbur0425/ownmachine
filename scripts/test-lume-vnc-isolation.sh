#!/bin/bash
# Run the regression probe against an already patched pinned Lume checkout.
set -euo pipefail
source=${1:?Pass the patched Lume source checkout}
root=$(cd "$(dirname "$0")/.." && pwd)
target="$source/libs/lume/tests/OwnMachineVNCIsolationTests.swift"
[ ! -e "$target" ] || { echo 'Test destination exists; inspect it first.' >&2; exit 1; }
# Both automatic export routes must be absent, including the SSH fallback.
python3 - "$source/libs/lume/src/VM/VM.swift" <<'PYTHON'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
if any(value in source for value in ('lume-config','vnc.env','writeVNCConfigViaSSH','VNC_PASSWORD=')):
    raise SystemExit('Guest VNC credential export remains')
PYTHON
cp "$root/tests/lume/OwnMachineVNCIsolationTests.swift" "$target"
trap 'rm -f "$target"' EXIT
swift test --package-path "$source/libs/lume" -c release --filter ownMachineVNCCredentialIsolation
