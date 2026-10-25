"""XZ settings supported by the kernel's embedded decoder."""
import lzma

def compress_module(data):
    return lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC32,
                         filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 1 << 20}])
