#!/usr/bin/env python3
"""Add only the configured viewer's dedicated-network start dependencies."""
import json
import os
from pathlib import Path
import sys
import uuid

if os.geteuid() != 0:
    raise SystemExit('Administrator authentication required')
c = json.loads(Path(sys.argv[1]).read_text())
network = str(uuid.UUID(c['network_uuid']))
rule = Path('/etc/polkit-1/rules.d/00-ownmachine-spike.rules')
s = rule.read_text()
marker = '  if (action.lookup("connect_driver") !== "QEMU") return polkit.Result.NO;'
if marker not in s or json.dumps(c['viewer_user']) not in s or json.dumps(c['vm_uuid']) not in s:
    raise SystemExit('Existing spike rule does not match configuration; no change')
addition = '''  // OwnMachine dedicated-network lifecycle dependencies (viewer only).
  var driver = action.lookup("connect_driver");
  if (viewer && (driver === "QEMU" || driver === "network")) {
    var networkConnect = ["org.libvirt.api.connect.getattr", "org.libvirt.api.connect.read", "org.libvirt.api.connect.search-networks"];
    if (networkConnect.indexOf(action.id) >= 0) return polkit.Result.YES;
    if (action.lookup("network_uuid") === NETWORK) {
      var networkActions = ["org.libvirt.api.network.getattr", "org.libvirt.api.network.read",
        "org.libvirt.api.network-port.create", "org.libvirt.api.network-port.delete",
        "org.libvirt.api.network-port.getattr", "org.libvirt.api.network-port.read"];
      if (networkActions.indexOf(action.id) >= 0) return polkit.Result.YES;
    }
  }
'''.replace('NETWORK', json.dumps(network))
if '// OwnMachine dedicated-network lifecycle dependencies' in s:
    raise SystemExit('Network dependency rule already installed; inspect before changing it')
backup = rule.with_suffix('.rules.before-network')
with backup.open('x') as f:
    f.write(s)
temp = rule.with_suffix('.rules.new')
fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
with os.fdopen(fd, 'w') as f:
    f.write(s.replace(marker, addition + marker, 1))
os.replace(temp, rule)
print('Viewer access added only for the configured dedicated network and its ports. No daemon or VM restarted. Rerun boundary and lifecycle checks.')
