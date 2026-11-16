#!/usr/bin/env python3
"""Render private disposable-guest inputs. No defaults contain deployment identities."""
import argparse
import ipaddress
import json
from pathlib import Path
import secrets
import re
import shutil
from xml.sax.saxutils import escape

p=argparse.ArgumentParser()
p.add_argument('--config',type=Path,required=True)
p.add_argument('--private-dir',type=Path,required=True)
p.add_argument('--driver-zip',type=Path,required=True)
p.add_argument('--driver-sha256',required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--accept-evaluation-terms',action='store_true',required=True)
a=p.parse_args(); c=json.loads(a.config.read_text()); out=a.output
out.mkdir(mode=0o700,parents=True,exist_ok=False)
desktop_user=c.get('guest_user','ownmachine'); setup_user=c.get('guest_setup_user','ownsetup')
if desktop_user==setup_user or any(not re.fullmatch(r'[a-z][a-z0-9_-]{0,19}',n) for n in (desktop_user,setup_user)):raise SystemExit('Invalid or identical guest account names')
guest=dict(desktop_user=desktop_user,setup_user=setup_user,desktop_password=secrets.token_urlsafe(18)+'aA1!',setup_password=secrets.token_urlsafe(24)+'aA1!',host_address=str(ipaddress.ip_network(c['subnet']).network_address+1),driver_sha256=a.driver_sha256)
(out/'guest.json').write_text(json.dumps(guest));(out/'guest.json').chmod(0o600)
for name in ('guest.pub','guest-setup.pub','guest-host','guest-host.pub'):
    shutil.copy2(a.private_dir/name,out/name)
shutil.copy2(a.driver_zip,out/'driver.zip')
for script in ('prepare-guest.ps1','finish-guest.ps1'):
    shutil.copy2(Path(__file__).with_name(script),out/script)
command="powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"$d=(Get-Volume | Where-Object FileSystemLabel -eq 'OWNBOOT').DriveLetter; & (${d} + ':\\prepare-guest.ps1')\""
xml=f'''<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
 <settings pass="windowsPE">
  <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <SetupUILanguage><UILanguage>en-US</UILanguage></SetupUILanguage><InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale>
  </component>
  <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <DiskConfiguration><Disk wcm:action="add"><DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk><CreatePartitions>
    <CreatePartition wcm:action="add"><Order>1</Order><Type>EFI</Type><Size>260</Size></CreatePartition>
    <CreatePartition wcm:action="add"><Order>2</Order><Type>MSR</Type><Size>16</Size></CreatePartition>
    <CreatePartition wcm:action="add"><Order>3</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition>
   </CreatePartitions><ModifyPartitions>
    <ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Format>FAT32</Format><Label>System</Label></ModifyPartition>
    <ModifyPartition wcm:action="add"><Order>2</Order><PartitionID>3</PartitionID><Format>NTFS</Format><Label>Windows</Label><Letter>C</Letter></ModifyPartition>
   </ModifyPartitions></Disk><WillShowUI>OnError</WillShowUI></DiskConfiguration>
   <ImageInstall><OSImage><InstallFrom><MetaData wcm:action="add"><Key>/IMAGE/INDEX</Key><Value>1</Value></MetaData></InstallFrom><InstallTo><DiskID>0</DiskID><PartitionID>3</PartitionID></InstallTo><WillShowUI>OnError</WillShowUI></OSImage></ImageInstall>
   <UserData><AcceptEula>true</AcceptEula><FullName>OwnMachine Evaluation</FullName><Organization>OwnMachine Spike</Organization></UserData>
  </component>
 </settings>
 <settings pass="specialize">
  <component name="Microsoft-Windows-Deployment" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><RunSynchronous><RunSynchronousCommand wcm:action="add"><Order>1</Order><Path>{escape(command)}</Path><Description>Configure isolated OwnMachine evaluation guest</Description></RunSynchronousCommand></RunSynchronous></component>
 </settings>
 <settings pass="oobeSystem">
  <component name="Microsoft-Windows-International-Core" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale></component>
  <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <OOBE><HideEULAPage>true</HideEULAPage><HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE><ProtectYourPC>3</ProtectYourPC></OOBE>
   <AutoLogon><Password><Value>{escape(guest['desktop_password'])}</Value><PlainText>true</PlainText></Password><Enabled>true</Enabled><LogonCount>1</LogonCount><Username>{guest['desktop_user']}</Username></AutoLogon>
  </component>
 </settings>
</unattend>'''
(out/'Autounattend.xml').write_text(xml); (out/'Autounattend.xml').chmod(0o600)
print('Private bootstrap media source rendered; credentials not printed.')
