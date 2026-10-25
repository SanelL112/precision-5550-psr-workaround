import unittest
from boot_entry import make_entry

NORMAL = 'title Fedora\nversion 7.2.11\nlinux /vmlinuz-7.2.11\ninitrd /initramfs-original.img\noptions root=UUID=abc ro rootflags=subvol=root i915.enable_psr=0 quiet\n'
class BootTests(unittest.TestCase):
    def test_isolated_initrd_preserves_kernel_root(self):
        result = make_entry(NORMAL, '/initramfs-psr-diag.img')
        for value in ['linux /vmlinuz-7.2.11', 'root=UUID=abc', 'rootflags=subvol=root']:
            self.assertIn(value, result)
        self.assertIn('initrd /initramfs-psr-diag.img', result)
        self.assertNotIn('initrd /initramfs-original.img', result)
        self.assertIn('i915.psr_diag=1', result)
    def test_preserves_fedora_tuned_placeholders(self):
        source = NORMAL.replace('/initramfs-original.img', '/initramfs-original.img $tuned_initrd').replace(' quiet', ' $tuned_params quiet')
        result = make_entry(source, '/initramfs-test.img')
        self.assertIn('initrd /initramfs-test.img $tuned_initrd', result)
        self.assertIn('$tuned_params', result)
    def test_link_standby_opt_in(self):
        result = make_entry(NORMAL.replace(' quiet', ' i915.psr_diag_link_standby=0 quiet'), '/initramfs-link-standby.img')
        self.assertEqual(result.count('i915.psr_diag_link_standby='), 1)
        self.assertIn('i915.psr_diag_link_standby=1', result)
        self.assertIn('i915.enable_psr=1', result)
        self.assertIn('title Precision 5550 PSR1 link-standby test v2 (4-minute recovery)', result)
    def test_flags_are_unique(self):
        source = NORMAL.replace(' quiet', ' drm.debug=0 i915.psr_diag=0 quiet')
        result = make_entry(source, '/initramfs-test.img')
        self.assertEqual(result.count('drm.debug='), 1)
        self.assertEqual(result.count('i915.psr_diag='), 1)
    def test_reject_enabled_source(self):
        with self.assertRaises(ValueError):
            make_entry(NORMAL.replace('i915.enable_psr=0', 'i915.enable_psr=1'), '/initramfs-test.img')
    def test_reject_multiple_initrds(self):
        with self.assertRaises(ValueError):
            make_entry(NORMAL.replace('/initramfs-original.img', '/microcode.img /normal.img'), '/initramfs-test.img')
    def test_reject_image_traversal(self):
        with self.assertRaises(ValueError):
            make_entry(NORMAL, '/initramfs-../escape.img')
if __name__ == '__main__':
    unittest.main()
