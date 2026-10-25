import unittest
from boot_config import MARKER, promote_entry, exclude_validated_boot, stock_args_safe, default_env_preserved

SOURCE = ('title Test\nlinux /vmlinuz-7.2.11\ninitrd /initramfs-tested.img $tuned_initrd\n'
          'options root=UUID=example ro i915.enable_psr=1 i915.psr_safest_params=1 '
          'i915.psr_diag=1 i915.psr_diag_link_standby=1 drm.debug=0x106 $tuned_params\n')

class BootConfigTests(unittest.TestCase):
    def test_default_allows_clearing_transient_entries(self):
        before = {'saved_entry': 'old', 'next_entry': '', 'prev_saved_entry': 'old', 'boot_success': '1'}
        self.assertTrue(default_env_preserved(before, {'saved_entry': 'new', 'boot_success': '1'}))
    def test_default_rejects_unrelated_changes_or_transient_boot(self):
        before = {'saved_entry': 'old', 'boot_success': '1'}
        self.assertFalse(default_env_preserved(before, {'saved_entry': 'new', 'boot_success': '0'}))
        self.assertFalse(default_env_preserved(before, {'saved_entry': 'new', 'boot_success': '1', 'next_entry': 'other'}))
    def test_promotion_preserves_tested_configuration(self):
        new = promote_entry(SOURCE)
        self.assertIn('initrd /initramfs-tested.img $tuned_initrd', new)
        self.assertIn('linux /vmlinuz-7.2.11', new)
        before = next(x for x in SOURCE.splitlines() if x.startswith('options '))
        after = next(x for x in new.splitlines() if x.startswith('options '))
        self.assertEqual(after, before + ' ' + MARKER)
    def test_rejects_stock_driver_source(self):
        with self.assertRaises(ValueError):
            promote_entry(SOURCE.replace('i915.enable_psr=1', 'i915.enable_psr=0'))
    def test_rejects_conflicting_duplicate(self):
        with self.assertRaises(ValueError):
            promote_entry(SOURCE.replace(' ro ', ' ro i915.enable_psr=0 '))
    def test_rejects_missing_workaround(self):
        with self.assertRaises(ValueError):
            promote_entry(SOURCE.replace('i915.psr_diag_link_standby=1', ''))
    def test_test_units_exclude_validated_but_keep_test_conditions(self):
        source = '[Unit]\nConditionKernelCommandLine=i915.enable_psr=1\n[Service]\nType=oneshot\n'
        new = exclude_validated_boot(source)
        self.assertIn('ConditionKernelCommandLine=!' + MARKER, new)
        self.assertIn('ConditionKernelCommandLine=i915.enable_psr=1', new)
        self.assertEqual(exclude_validated_boot(new), new)
    def test_stock_update_defaults_reject_test_flags(self):
        self.assertTrue(stock_args_safe('root=UUID=example ro i915.enable_psr=0'))
        self.assertFalse(stock_args_safe('ro i915.enable_psr=1'))
        self.assertFalse(stock_args_safe('i915.enable_psr=0 i915.enable_psr=1'))
        self.assertFalse(stock_args_safe('i915.enable_psr=0 i915.psr_diag_link_standby=1'))

if __name__ == '__main__':
    unittest.main()
