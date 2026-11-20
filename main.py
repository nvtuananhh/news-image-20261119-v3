"""Entrypoint: draw the poster and write it to /output/entry.png.

Standard library only, no network. Runs deterministically: two runs
write byte-identical files. Outside the grader, MAKEFUN_OUTPUT_DIR
stands in for /output.

Works when invoked as `python3 -P -s main.py`: the script directory is
not on sys.path under -P -s, so it is added explicitly before importing
the generator that lives beside this file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_poster import build


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size, total = build(path)
    print("wrote %s (%d bytes, %d stories)" % (path, size, total))


if __name__ == "__main__":
    main()
