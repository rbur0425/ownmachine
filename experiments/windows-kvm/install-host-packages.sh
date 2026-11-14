#!/usr/bin/env bash
# Ubuntu-only prerequisite installation; creates no VM or runtime authorization.
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then echo 'Run with sudo on the selected Linux VM host.' >&2; exit 1; fi
. /etc/os-release
if [[ ${ID:-} != ubuntu ]]; then echo 'This reviewed prerequisite script targets Ubuntu.' >&2; exit 1; fi
if [[ $(uname -m) != x86_64 ]]; then echo 'The spike requires an x86_64 host.' >&2; exit 1; fi
if [[ ! -c /dev/kvm ]]; then echo 'KVM device missing; enable hardware virtualization first.' >&2; exit 1; fi
apt-get update
apt-get install --no-install-recommends qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients ovmf swtpm swtpm-tools virtinst
printf '\nOwnMachine Windows spike prerequisites installed. No VM or runtime permissions created.\n'
dpkg-query -W qemu-system-x86 libvirt-daemon-system libvirt-clients ovmf swtpm swtpm-tools virtinst
