#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Nurymanau
"""Stream SHA256 verification without loading whole weight files in memory."""
import hashlib
from pathlib import Path
import sys
root=Path(__file__).resolve().parent
for line in (root/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    file=root/name
    if not file.is_file():raise SystemExit('Missing: '+name)
    sha=hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):sha.update(block)
    if sha.hexdigest()!=expected:raise SystemExit('SHA256 mismatch: '+name)
    print('OK',name,flush=True)
print('All release files verified.')
