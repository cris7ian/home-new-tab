"""Reduce the GeoNames cities5000 download to coordinates and display names."""
from argparse import ArgumentParser
import gzip
import json
from pathlib import Path
from zipfile import ZipFile

ap = ArgumentParser()
ap.add_argument('archive', type=Path)
args = ap.parse_args()
rows = []
with ZipFile(args.archive) as gazetteer, gazetteer.open('cities5000.txt') as entries:
    for entry in entries:
        f = entry.decode('utf-8').rstrip('\r\n').split('\t')
        if f[6] != 'P' or f[7] in ('PPLX', 'PPLH', 'PPLQ', 'PPLW'):
            continue
        rows.append((round(float(f[4]), 4), round(float(f[5]), 4), f[1]))
rows.sort()
path = Path(__file__).with_name('cities5000.json.gz')
path.write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':'), ensure_ascii=False).encode(), mtime=0))
print(f'{len(rows):,} places, {path.stat().st_size:,} compressed bytes')
