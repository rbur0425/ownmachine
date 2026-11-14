#!/usr/bin/env python3
"""Discover the installed guest's MCP contract without performing desktop input."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--host',required=True);p.add_argument('--user',required=True);p.add_argument('--key',type=Path,required=True);p.add_argument('--known-hosts',type=Path,required=True);p.add_argument('--vm',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.source/'plugin'))
from ownmachine.config import Config
from ownmachine.transport import MCPTransport
argv=['ssh','-F','/dev/null','-i',str(a.key),'-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(a.known_hosts),a.user+'@'+a.host,'ownmachine-host','mcp','--vm',a.vm]
t=MCPTransport(Config(host_alias='spike',guest_profile='windows',action_timeout_seconds=30),argv=argv)
try:
 t.start();a.output.write_text(json.dumps(t.tools,indent=2)+'\n');print('MCP connected; tool schemas saved:',len(t.tools))
finally:t.stop()
