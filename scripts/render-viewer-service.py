#!/usr/bin/env python3
"""Render an optional systemd user unit; never install, start or enable it."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin'))
from ownmachine.config import Config


def quote(value):
    value=str(value)
    if any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError('control_character_in_argument')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%').replace('$','$$')+'"'


def render(source, python, config, port=0, swap_red_blue=False, read_only=False, access_dir=None):
    config.validate()
    source=Path(source).expanduser().absolute()
    python=Path(python).expanduser().absolute()
    if not config.control_dir or not (source/'viewer/server.py').is_file() or not python.is_file():
        raise ValueError('source_python_or_control_missing')
    if type(port) is not int or not 0<=port<=65535:raise ValueError('invalid_port')
    command=[str(python),str(source/'viewer/server.py'),'--host-alias',config.host_alias,
             '--vm-name',config.vm_name,'--control-dir',config.control_dir,'--port',str(port),
             '--connect-timeout-seconds',str(config.connect_timeout_seconds),
             '--action-timeout-seconds',str(config.action_timeout_seconds)]
    if access_dir:
        command += ['--access-dir',str(Path(access_dir).expanduser().absolute())]
    if swap_red_blue:command.append('--swap-red-blue')
    if read_only:command.append('--read-only')
    return ('[Unit]\nDescription=OwnMachine private viewer\nStartLimitIntervalSec=60\nStartLimitBurst=3\n\n'
            '[Service]\nType=simple\nExecStart='+ ' '.join(map(quote,command))+
            '\nRestart=on-failure\nRestartSec=5\nTimeoutStopSec=30\nUMask=0077\nNoNewPrivileges=yes\n\n'
            '[Install]\nWantedBy=default.target\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--python',required=True,type=Path)
    parser.add_argument('--host-alias',required=True)
    parser.add_argument('--vm-name',default='ownmachine')
    parser.add_argument('--control-dir',required=True)
    parser.add_argument('--access-dir')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--swap-red-blue',action='store_true')
    parser.add_argument('--read-only',action='store_true')
    parser.add_argument('--connect-timeout-seconds',type=int,default=15)
    parser.add_argument('--action-timeout-seconds',type=int,default=30)
    a=parser.parse_args()
    try:
        unit=render(a.source,a.python,Config(a.host_alias,a.control_dir,a.vm_name,
                    a.connect_timeout_seconds,a.action_timeout_seconds),a.port,a.swap_red_blue,a.read_only,a.access_dir)
    except ValueError as error:parser.error(str(error))
    print(unit,end='')

if __name__=='__main__':main()
