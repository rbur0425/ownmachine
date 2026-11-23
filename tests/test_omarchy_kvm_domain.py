import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from xml.etree import ElementTree


class OmarchyDomainTests(unittest.TestCase):
    def test_profiles_render_separate_boot_media_with_private_console(self):
        renderer = Path(__file__).resolve().parents[1] / 'scripts/windows/render-domain.py'
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            config = dict(vm_name='desktop', vm_uuid=str(uuid.uuid4()), network_uuid=str(uuid.uuid4()),
                          subnet='192.0.2.0/24', guest_ip='192.0.2.2', bridge='testnet',
                          storage_dir=tmp, memory_gb=8, cpu=4, display='1600x900',
                          firmware_code='/firmware/code', firmware_vars='/firmware/vars',
                          console_socket='/console/private.sock', windows_iso='/media/install.iso')
            for profile in ('omarchy-kvm', 'windows'):
                config_path = directory / 'settings.json'
                config_path.write_text(json.dumps(dict(config, guest_profile=profile)))
                subprocess.run([sys.executable, str(renderer), str(config_path), str(directory)],
                               check=True, capture_output=True)
                domain = ElementTree.parse(directory / 'domain.xml')
                self.assertEqual(domain.find('.//graphics/listen').get('socket'), config['console_socket'])
                if profile == 'omarchy-kvm':
                    self.assertIsNone(domain.find(".//disk[@device='cdrom']"))
                    self.assertIsNone(domain.find('.//tpm'))
                    self.assertEqual(domain.find('.//disk/target').get('bus'), 'virtio')
                    self.assertEqual(domain.find('.//video/model/resolution').attrib, dict(x='1600', y='900'))
                    self.assertEqual(domain.findtext('.//loader'), config['firmware_code'])
                else:
                    self.assertIsNotNone(domain.find('.//tpm'))
                    self.assertEqual(len(domain.findall(".//disk[@device='cdrom']")), 2)
