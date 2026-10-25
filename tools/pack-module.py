#!/usr/bin/env python3
"""Compress a previously signed module without changing the signed bytes."""
import argparse
from pathlib import Path
from module_pack import compress_module

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('module', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
with args.output.open('xb') as output:
    output.write(compress_module(args.module.read_bytes()))
