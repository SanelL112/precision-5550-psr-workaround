import hashlib
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

loader = importlib.machinery.SourceFileLoader('psr_manager', str(Path(__file__).with_name('precision-psr')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'nvidia.ko'
        self.source.write_bytes(b'validated driver')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.config = {'kernel': '7.2.11-200.fc44.x86_64', 'entry': 'validated-entry',
                       'artifacts': {}, 'update_inputs': {str(self.source): self.digest}}
        self.patcher = mock.patch.multiple(m, HEALTH=self.base/'health.json', PENDING=self.base/'pending.json', ENTRIES=self.base/'entries')
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        m.ENTRIES.mkdir()
    def test_unchanged_inputs_do_not_alter_default(self):
        with mock.patch.object(m, 'set_default') as default:
            self.assertEqual(m.guard(self.config), [])
            default.assert_not_called()
    def test_driver_update_selects_stock_if_validated_was_default(self):
        self.source.write_bytes(b'new driver')
        with mock.patch.object(m,'out',return_value='saved_entry=validated-entry'), mock.patch.object(m,'newest_stock',return_value='new-stock'), mock.patch.object(m,'set_default') as default:
            self.assertTrue(m.guard(self.config))
            default.assert_called_once_with('new-stock')
    def test_guard_does_not_override_another_default(self):
        self.source.unlink()
        with mock.patch.object(m,'out',return_value='saved_entry=user-choice'), mock.patch.object(m,'set_default') as default:
            self.assertTrue(m.guard(self.config))
            default.assert_not_called()
    def test_new_kernel_event_chooses_stock_without_building(self):
        with mock.patch.object(m,'newest_stock',return_value='new-stock'), mock.patch.object(m,'set_default') as default, mock.patch.object(m,'guard'):
            m.kernel_event(self.config,'add','7.2.12-200.fc44.x86_64')
            default.assert_called_once_with('new-stock')
    def test_older_kernel_event_does_not_pin_default(self):
        with mock.patch.object(m,'set_default') as default, mock.patch.object(m,'guard'):
            m.kernel_event(self.config,'add','7.2.9-200.fc44.x86_64')
            default.assert_not_called()
    def test_remove_only_retires_unchanged_generated_entry(self):
        entry=m.ENTRIES/'validated-entry.conf';entry.write_bytes(b'our generated entry')
        self.config['artifacts'][str(entry)]=hashlib.sha256(entry.read_bytes()).hexdigest()
        with mock.patch.object(m,'out',return_value='saved_entry=validated-entry'), mock.patch.object(m,'newest_stock',return_value='fallback'), mock.patch.object(m,'set_default') as default, mock.patch.object(m,'guard'):
            m.kernel_event(self.config,'remove',self.config['kernel'])
            default.assert_called_once_with('fallback')
            self.assertFalse(entry.exists())
    def test_remove_preserves_modified_entry(self):
        entry=m.ENTRIES/'validated-entry.conf';entry.write_bytes(b'user changed this')
        self.config['artifacts'][str(entry)]='old-hash'
        with mock.patch.object(m,'out',return_value='saved_entry=other'), mock.patch.object(m,'guard'):
            m.kernel_event(self.config,'remove',self.config['kernel'])
            self.assertTrue(entry.exists())
    def test_invalid_version_cannot_reach_boot_changes(self):
        with self.assertRaises(SystemExit), mock.patch.object(m,'set_default') as default:
            m.kernel_event(self.config,'add','../../escape')
        default.assert_not_called()
    def test_numerical_kernel_order(self):
        self.assertTrue(m.newer_than('7.2.12-200.fc44.x86_64','7.2.11-200.fc44.x86_64'))
        self.assertFalse(m.newer_than('7.2.9-200.fc44.x86_64','7.2.11-200.fc44.x86_64'))

if __name__ == '__main__':
    unittest.main()
