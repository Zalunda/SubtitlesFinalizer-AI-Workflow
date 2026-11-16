#!/usr/bin/env python3
"""
renumber_srt.py - renumber the cues of an .srt file sequentially (1, 2, 3...), in file order.

Only the cue-number lines are changed: the BOM, the line endings (CRLF/LF mix), the timings, the text and the
metadata blocks are kept byte for byte. The cues are NOT reordered (use the file order as is).

It also reports (without changing anything) cues whose start is before the previous cue's start, and overlaps
between consecutive cues, so they can be checked in the polish wave.

Usage:
    python tools/renumber_srt.py <file.srt> [<file2.srt> ...]
    python tools/renumber_srt.py --dry-run <file.srt>        only report, don't write

Only the Python standard library is needed.
"""
import argparse
import os
import re
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
# optional BOM + number line, followed by a timing line
NUMBER_LINE = re.compile(r"^(﻿?)(\d+)([ \t]*\r?\n)(?=" + TS + r" --> " + TS + ")", re.MULTILINE)
TIMING = re.compile(r"^" + TS + r" --> " + TS, re.MULTILINE)


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def fmt(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d.%03d" % (h, m, s, ms)


def check_timings(text, label):
    prev_start = prev_end = None
    warnings = 0
    for i, m in enumerate(TIMING.finditer(text), 1):
        start, end = to_ms(*m.groups()[0:4]), to_ms(*m.groups()[4:8])
        if end <= start:
            print("%s: cue #%d at %s has an end <= its start" % (label, i, fmt(start)))
            warnings += 1
        if prev_start is not None:
            if start < prev_start:
                print("%s: cue #%d at %s starts before the previous cue (out of order)" % (label, i, fmt(start)))
                warnings += 1
            elif start < prev_end:
                print("%s: cue #%d at %s overlaps the previous cue by %d ms" % (label, i, fmt(start), prev_end - start))
                warnings += 1
        prev_start, prev_end = start, end
    return warnings


def renumber(text):
    counter = [0]

    def repl(m):
        counter[0] += 1
        return "%s%d%s" % (m.group(1), counter[0], m.group(3))

    return NUMBER_LINE.sub(repl, text), counter[0]


def main():
    ap = argparse.ArgumentParser(description="Renumber the cues of .srt files sequentially.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--dry-run", action="store_true", help="only report, don't write")
    ap.add_argument("--eol", choices=["crlf", "lf"], help="also convert EVERY line ending of the file to this one (default: keep as is)")
    args = ap.parse_args()

    status = 0
    for path in args.files:
        if not os.path.isfile(path):
            print("ERROR: not found: " + path, file=sys.stderr)
            status = 2
            continue
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        timing_count = len(TIMING.findall(text))
        result, count = renumber(text)
        if count != timing_count:
            # A cue without a number line: don't guess, don't write.
            print("ERROR: %s: %d timing lines but %d number lines; not modified" % (path, timing_count, count), file=sys.stderr)
            status = 1
            continue
        if args.eol:
            result = result.replace("\r\n", "\n")
            if args.eol == "crlf":
                result = result.replace("\n", "\r\n")
        warnings = check_timings(result, os.path.basename(path))
        if result == text:
            print("%s: %d cues, numbering already sequential%s" % (path, count, " (%d timing warnings)" % warnings if warnings else ""))
            continue
        if not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(result)
        print("%s: %d cues %s%s" % (path, count, "would be renumbered" if args.dry_run else "renumbered",
                                    " (%d timing warnings)" % warnings if warnings else ""))
    return status


if __name__ == "__main__":
    sys.exit(main())
