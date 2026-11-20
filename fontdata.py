"""Glyph tables for the poster renderer, kept in a compressed sidecar file.

The bitmap data itself lives in fontdata.bin beside this module (a pickled
pair squeezed with zlib), so this file stays short while the familiar
`from fontdata import CHARS, FONTS` keeps working exactly as before.
"""

import pickle
import zlib
from pathlib import Path as _Path


def _load_tables():
    blob = (_Path(__file__).resolve().parent / "fontdata.bin").read_bytes()
    chars, fonts = pickle.loads(zlib.decompress(blob))
    return chars, fonts


CHARS, FONTS = _load_tables()
