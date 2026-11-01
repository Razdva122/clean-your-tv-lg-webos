#!/usr/bin/env python3
"""Prime automatic Chinese font preparation; ordinary builds call it themselves."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.chinese_fonts import prepare_fonts

if __name__ == '__main__':
    for name, raw in prepare_fonts().items():
        print(f'{name}: {len(raw)} bytes (prepared in build cache; source unchanged)')
