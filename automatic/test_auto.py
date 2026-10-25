import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
loader = importlib.machinery.SourceFileLoader('manager', str(ROOT / 'lifecycle/precision-psr'))
spec = importlib.util.spec_from_loader('manager', loader)
manager = importlib.util.module_from_spec(spec)
sys.modules['manager'] = manager
loader.exec_module(manager)
spec = importlib.util.spec_from_file_location('psr_auto_test', Path(__file__).with_name('auto.py'))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

class AutoTests(unittest.TestCase):
    def test_boot_check_healthy_image_does_not_reboot(self):
        with patch.object(a.Path,'read_text',side_effect=['precision_psr.validated=1','{}']), patch.object(a.m,'maintenance_errors',return_value=[]),patch.object(a,'run') as run:
            a.boot_check();run.assert_not_called()
    def test_boot_check_stale_image_selects_stock_and_reboots_before_login(self):
        with patch.object(a.Path,'read_text',side_effect=['precision_psr.validated=1','{}']), patch.object(a.m,'maintenance_errors',return_value=['Updated NVIDIA module']), patch.object(a.m,'newest_stock',return_value='stock'),patch.object(a.m,'set_default') as default,patch.object(a,'report'),patch.object(a,'run') as run:
            a.boot_check();default.assert_called_once_with('stock');run.assert_called_once_with('systemctl','--no-block','reboot')
    def test_boot_check_does_not_override_intentional_trial(self):
        with patch.object(a.Path,'read_text',return_value='precision_psr.validated=1 precision_psr.trial='+'a'*24),patch.object(a.m,'maintenance_errors') as errors,patch.object(a,'run') as run:
            a.boot_check();errors.assert_not_called();run.assert_not_called()
    def test_source_requires_trusted_signature_not_only_digests(self):
        for code,text in [(0,'Header SHA256 digest: OK'),(1,'Header signature: NOKEY'),(0,'Header signature: NOT OK')]:
            with patch.object(a.subprocess,'run',return_value=Mock(returncode=code,stdout=text)):
                with self.assertRaises(RuntimeError):a.verify_source_rpm('/source.rpm')
        with patch.object(a.subprocess,'run',return_value=Mock(returncode=0,stdout='Header OpenPGP signature: OK\nPayload SHA256 digest: OK')):
            a.verify_source_rpm('/source.rpm')
    def test_marker_is_strict_and_unique(self):
        token = 'a' * 24
        self.assertEqual(a.trial_token('ro precision_psr.trial=' + token), token)
        self.assertIsNone(a.trial_token('ro precision_psr.validated=1'))
        for text in ['precision_psr.trial=bad', 'precision_psr.trial=' + token + ' precision_psr.trial=' + token]:
            with self.assertRaises(ValueError): a.trial_token(text)
    def test_promotion_removes_only_trial_and_changes_title(self):
        text = 'title Trial\nlinux /vmlinuz-example\ninitrd /image.img\noptions root=example ro i915.enable_psr=1 precision_psr.validated=1 precision_psr.trial=' + 'a'*24 + '\n'
        new = a.clear_trial(text)
        self.assertNotIn('precision_psr.trial=', new)
        for preserved in ['linux /vmlinuz-example', 'initrd /image.img', 'root=example ro i915.enable_psr=1 precision_psr.validated=1']:
            self.assertIn(preserved, new)
    def test_trial_keeps_stock_as_persistent_default(self):
        data={'entry':'trial-entry','kernel':'7.2.12','token':'a'*24}
        events=[]
        def out(*args):
            return '' if not events else 'next_entry=trial-entry'
        with patch.object(a,'candidate',return_value=data), patch.object(a,'out',side_effect=out), patch.object(a.m,'newest_stock',return_value='stock'), patch.object(a.m,'set_default',side_effect=lambda entry: events.append(('default',entry))), patch.object(a,'run',side_effect=lambda *args: events.append(args)), patch.object(a,'report'):
            a.test()
        self.assertEqual(events,[('default','stock'),('grub2-reboot','trial-entry')])
    def test_existing_one_time_boot_is_not_replaced(self):
        with patch.object(a,'candidate',return_value={}), patch.object(a,'out',return_value='next_entry=user-choice'), patch.object(a.m,'set_default') as default:
            with self.assertRaises(RuntimeError): a.test()
            default.assert_not_called()
    def test_changed_candidate_cannot_be_scheduled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'candidate.json';path.write_text('{}')
            with patch.object(a,'CANDIDATE',path), patch.object(a.m,'maintenance_errors',return_value=['Driver changed']), patch.object(a.m,'set_default') as default:
                with self.assertRaises(RuntimeError): a.test()
                default.assert_not_called()
    def test_recovery_does_nothing_on_normal_boot(self):
        with patch.object(a.Path,'read_text',return_value='ro precision_psr.validated=1'), patch.object(a,'run') as run, patch.object(a.m,'set_default') as default:
            a.recover(); run.assert_not_called(); default.assert_not_called()
    def test_confirmed_trial_does_not_reboot(self):
        with tempfile.TemporaryDirectory() as tmp:
            confirmed=Path(tmp)/'confirmed';confirmed.touch()
            with patch.object(a,'CONFIRMED',confirmed), patch.object(a.Path,'read_text',return_value='precision_psr.trial='+'a'*24), patch.object(a,'run') as run:
                a.recover();run.assert_not_called()
    def test_unconfirmed_trial_selects_stock_then_reboots(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(a,'CONFIRMED',Path(tmp)/'absent'), patch.object(a.Path,'read_text',return_value='precision_psr.trial='+'a'*24), patch.object(a.m,'newest_stock',return_value='stock'), patch.object(a.m,'set_default') as default, patch.object(a,'run') as run, patch.object(a,'report'):
                a.recover();default.assert_called_once_with('stock');run.assert_called_once_with('systemctl','reboot')
    def test_wrong_running_trial_cannot_be_promoted(self):
        with patch.object(a,'candidate',return_value={'token':'b'*24}), patch.object(a.Path,'read_text',return_value='precision_psr.trial='+'a'*24), patch.object(a,'save') as save:
            with self.assertRaises(RuntimeError): a.confirm()
            save.assert_not_called()
    def test_build_will_not_run_during_trial(self):
        with patch.object(a.Path,'read_text',return_value='precision_psr.trial='+'a'*24), patch.object(a,'source_tree') as source:
            with self.assertRaises(RuntimeError): a.build()
            source.assert_not_called()
    def test_watch_unit_has_gpu_directory_and_all_inputs(self):
        unit=a.watch_unit({'update_inputs':{'/lib/modules/example/extra/nvidia/nvidia.ko.xz':'hash','/boot/image.img':'hash'}})
        self.assertIn('PathChanged=/lib/modules/example/extra/nvidia\n',unit)
        self.assertIn('PathChanged=/boot/image.img\n',unit)
        with self.assertRaises(ValueError): a.watch_unit({'update_inputs':{'/boot/bad\nUnit=evil':'hash'}})
    def test_cleanup_preserves_current_kernel_and_modified_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); entries=base/'entries';entries.mkdir();registry=base/'candidates';registry.mkdir()
            config=base/'config';config.write_text('{"entry":"validated"}')
            def record(name,kernel,changed=False):
                entry=entries/(name+'.conf');entry.write_text(name)
                image=base/(name+'.img');image.write_text(name)
                data={'entry':name,'kernel':kernel,'image':str(image),'artifacts':{str(entry):a.sha(entry),str(image):a.sha(image)}}
                a.save(registry/(name+'.json'),data)
                if changed:entry.write_text('edited')
                return entry,image
            current=record('running',a.os.uname().release)
            modified=record('modified','old',True)
            obsolete=record('obsolete','old')
            with patch.object(a,'BASE',base),patch.object(a,'CANDIDATE',base/'absent'),patch.object(a.m,'CONFIG',config),patch.object(a.m,'ENTRIES',entries),patch.object(a,'out',return_value='saved_entry=validated'):
                a.prune()
            self.assertTrue(all(p.exists() for p in current+modified))
            self.assertFalse(any(p.exists() for p in obsolete))

if __name__ == '__main__': unittest.main()
