import lzma
import subprocess
import tempfile
import unittest
from pathlib import Path
from module_pack import compress_module

class ModulePackTests(unittest.TestCase):
    def test_kernel_compatible_stream(self):
        data = bytes(range(256)) * 128
        compressed = compress_module(data)
        self.assertEqual(lzma.decompress(compressed), data)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'module.ko.xz'
            path.write_bytes(compressed)
            info = subprocess.check_output(['xz', '--robot', '--list', '--verbose', '--verbose', str(path)], text=True)
            self.assertIn('CRC32', info)
            self.assertIn('--lzma2=dict=1MiB', info)
            self.assertNotIn('CRC64', info)

if __name__ == '__main__':
    unittest.main()
