#!/usr/bin/env python3
"""
create_working_srt.py - create the work-in-progress file <SCENE>-<P>.WIP.srt of a part from its two input files.
(The plain <SCENE>-<P>.srt is the FINAL file, produced at the very end by tools/finalize_srt.py.)

Inputs (never modified):
    <SCENE>-<P>.final-ai-debug.srt                          subtitles + metadata
    <SCENE>-<P>.Worker.<id>.TERRAIN-MAP.srt                 audio: every cue is a piece of SOUND ('A'..'Z' speech, '~' breath);
    (or <SCENE>-<P>.TERRAIN-MAP.srt)                        what is not covered by a cue is SILENCE.   OPTIONAL: without it,
                                                            no silence is assumed anywhere ({Silences:none} on every cue)

Output:
    <SCENE>-<P>.WIP.srt = a copy of the debug file, where each cue's metadata block gets one more line:

        [terrain] {Silences:from 00:23:25.234 to 00:23:26.132; from 00:23:27.001 to 00:23:27.350}

    listing the silences (longer than --min-ms, default 100 ms) that OVERLAP that subtitle, with their real
    start/end (a silence can start before the subtitle or end after it). 'none' when there is no silence
    under the subtitle (continuous sound). They are the places where the subtitle can be cut.
    The silence after the last sound ends at the duration of the part, read from <SCENE>-.parts-duration.txt
    (one line per part: "<part name> <hh:mm:ss.fff>", written by the subtitle generator). Without that file
    (or without the part in it) the end is unknown: it is written 'from <time> to the end'.

Everything else in the file is kept byte for byte (BOM, CRLF/LF mix...), only the lines are added.
An existing <SCENE>-<P>.WIP.srt is NEVER overwritten (it holds the work in progress): the part is skipped.

Usage:
    python tools/create_working_srt.py <scene folder>                  every part of the folder
    python tools/create_working_srt.py --debug X.final-ai-debug.srt [--terrain X.TERRAIN-MAP.srt]
        [--min-ms 100]

Only the Python standard library is needed.
"""
import argparse
import os
import re
import sys

TIMING = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3}) --> (\d{2}):(\d{2}):(\d{2})[,.](\d{3})[ \t]*(\r?\n)", re.MULTILINE)
METADATA_HEADER = "------- Metadatas -------"
DEBUG_SUFFIX = ".final-ai-debug.srt"
PARTS_DURATION_SUFFIX = ".parts-duration.txt"
TERRAIN_NAME = re.compile(r"^(?P<base>.+?)(?:\.Worker\..*?)?\.TERRAIN-MAP\.srt$", re.IGNORECASE)
INFINITY = 10 ** 12


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def fmt(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d.%03d" % (h, m, s, ms)


def read_text(path):
    # newline='' keeps CR/LF as they are; 'utf-8' (not 'utf-8-sig') keeps the BOM as the first character.
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def terrain_sounds(path):
    """(start_ms, end_ms) of every sound piece of the terrain map, sorted."""
    sounds = [(to_ms(*m.groups()[0:4]), to_ms(*m.groups()[4:8])) for m in TIMING.finditer(read_text(path))]
    sounds.sort()
    return sounds


def parts_durations(folder):
    """{part name: duration in ms} from the *.parts-duration.txt of the folder; None when there is no such file."""
    files = [f for f in os.listdir(folder) if f.endswith(PARTS_DURATION_SUFFIX)]
    if not files:
        return None
    if len(files) > 1:
        raise ValueError("more than one *%s in %s" % (PARTS_DURATION_SUFFIX, folder))
    result = {}
    for line in read_text(os.path.join(folder, files[0])).lstrip("﻿").splitlines():
        m = re.match(r"^\s*(.+?)\s+(\d+):(\d{2}):(\d{2})[.,](\d{3})\s*$", line)
        if m:
            result[m.group(1)] = to_ms(*m.groups()[1:5])
        elif line.strip():
            raise ValueError("unexpected line in %s: %r" % (files[0], line))
    return result


def silences(sounds, min_ms, end_ms=None):
    """Silences = what the sounds don't cover, longer than min_ms. The last one ends at end_ms (open ended if None)."""
    result = []
    cursor = 0
    for start, end in sounds:
        # The terrain map shortens each piece by 1 ms, so pieces that touch leave a 1 ms hole: min_ms ignores it.
        if start - cursor > min_ms:
            result.append((cursor, start))
        cursor = max(cursor, end)
    if end_ms is None:
        result.append((cursor, INFINITY))
    elif end_ms - cursor > min_ms:
        result.append((cursor, end_ms))
    return result


def silence_line(cue_start, cue_end, all_silences, newline):
    found = [s for s in all_silences if s[0] < cue_end and s[1] > cue_start]
    if not found:
        text = "none"
    else:
        text = "; ".join(
            "from %s to the end" % fmt(a) if b == INFINITY else "from %s to %s" % (fmt(a), fmt(b))
            for a, b in found)
    return "[terrain] {Silences:%s}%s" % (text, newline)


def build(debug_text, all_silences):
    """Adds the silences line right after the '------- Metadatas -------' line of every cue."""
    out = []
    pos = 0
    count = 0
    for m in TIMING.finditer(debug_text):
        start, end = to_ms(*m.groups()[0:4]), to_ms(*m.groups()[4:8])
        newline = m.group(9)
        after = m.end()
        header_end = after + len(METADATA_HEADER)
        if debug_text.startswith(METADATA_HEADER, after):
            # skip the line ending of the header, insert our line after it
            eol = re.compile(r"\r?\n").match(debug_text, header_end)
            if not eol:
                raise ValueError("unexpected content after the metadata header at %s" % fmt(start))
            insert_at = eol.end()
            out.append(debug_text[pos:insert_at])
            out.append(silence_line(start, end, all_silences, eol.group(0)))
            pos = insert_at
        else:
            # A cue without a metadata block: add one after the cue text (before the blank line).
            blank = re.compile(r"\r?\n[ \t]*\r?\n|\Z").search(debug_text, after)
            insert_at = blank.start()
            out.append(debug_text[pos:insert_at])
            nl = newline
            out.append(nl + METADATA_HEADER + nl + silence_line(start, end, all_silences, "").rstrip("\r\n"))
            pos = insert_at
        count += 1
    out.append(debug_text[pos:])
    return "".join(out), count


def find_pairs(folder):
    """(debug_path, terrain_path or None) for every part of the folder (recursively)."""
    pairs = []
    for root, _dirs, files in os.walk(folder):
        terrains = {}
        for name in files:
            m = TERRAIN_NAME.match(name)
            if m:
                terrains.setdefault(m.group("base"), []).append(os.path.join(root, name))
        for name in sorted(files):
            if name.endswith(DEBUG_SUFFIX):
                base = name[: -len(DEBUG_SUFFIX)]
                candidates = terrains.get(base, [])
                pairs.append((os.path.join(root, name), candidates))
    return pairs


def process(debug_path, terrain_path, min_ms):
    name = os.path.basename(debug_path)
    if not name.endswith(DEBUG_SUFFIX):
        print("ERROR: not a *%s file: %s" % (DEBUG_SUFFIX, debug_path), file=sys.stderr)
        return 1
    out_path = os.path.join(os.path.dirname(debug_path), name[: -len(DEBUG_SUFFIX)] + ".WIP.srt")
    if os.path.exists(out_path):
        print("skipped (the WIP file already exists, not overwritten): " + out_path)
        return 0
    if terrain_path is None:
        # The terrain map is OPTIONAL: without it we assume there is no silence anywhere (every cue gets {Silences:none}).
        result, count = build(read_text(debug_path), [])
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(result)
        print("created %s: %d subtitles; NO TERRAIN-MAP found: assuming no silence anywhere (every cue has {Silences:none})" % (out_path, count))
        return 0
    sounds = terrain_sounds(terrain_path)
    if not sounds:
        print("ERROR: no cue found in " + terrain_path, file=sys.stderr)
        return 1
    part = name[: -len(DEBUG_SUFFIX)]
    try:
        durations = parts_durations(os.path.dirname(debug_path) or ".")
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    end_ms = None
    if durations is None:
        print("WARNING: no *%s in the folder: the last silence will be open ended ('to the end')" % PARTS_DURATION_SUFFIX, file=sys.stderr)
    elif part not in durations:
        print("ERROR: part '%s' is not listed in the *%s file" % (part, PARTS_DURATION_SUFFIX), file=sys.stderr)
        return 1
    else:
        end_ms = durations[part]
        if sounds[-1][1] > end_ms + 1000:
            print("ERROR: the terrain map goes past the duration of %s (%s > %s)" % (part, fmt(sounds[-1][1]), fmt(end_ms)), file=sys.stderr)
            return 1
    result, count = build(read_text(debug_path), silences(sounds, min_ms, end_ms))
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(result)
    print("created %s: %d subtitles, silences from %s (> %d ms)" % (out_path, count, os.path.basename(terrain_path), min_ms))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Create the working .srt from a .final-ai-debug.srt and a .TERRAIN-MAP.srt.")
    ap.add_argument("folder", nargs="?", help="a scene folder: every part found in it is processed")
    ap.add_argument("--debug", help="the *.final-ai-debug.srt file (single part mode)")
    ap.add_argument("--terrain", help="the *.TERRAIN-MAP.srt file (single part mode; optional: without it, no silence is assumed anywhere)")
    ap.add_argument("--min-ms", type=int, default=100, help="ignore silences of this duration or shorter (default 100)")
    args = ap.parse_args()

    if args.debug or args.terrain:
        if not (args.debug and not args.folder):
            ap.error("use either a folder, or --debug (plus --terrain when there is a terrain map)")
        for p in (args.debug, args.terrain):
            if p is not None and not os.path.isfile(p):
                print("ERROR: not found: " + p, file=sys.stderr)
                return 2
        return process(args.debug, args.terrain, args.min_ms)

    if not args.folder:
        ap.error("give a scene folder, or --debug (and --terrain)")
    if not os.path.isdir(args.folder):
        print("ERROR: not a folder: " + args.folder, file=sys.stderr)
        return 2
    pairs = find_pairs(args.folder)
    if not pairs:
        print("ERROR: no *%s found in %s" % (DEBUG_SUFFIX, args.folder), file=sys.stderr)
        return 2
    errors = 0
    for debug_path, terrains in pairs:
        if len(terrains) > 1:
            # Ambiguous: reported, the part is not processed. (No terrain map at all is allowed: no silence is assumed.)
            print("ERROR: %s: expected at most one TERRAIN-MAP.srt for this part, found %d" % (debug_path, len(terrains)), file=sys.stderr)
            errors += 1
            continue
        errors += process(debug_path, terrains[0] if terrains else None, args.min_ms)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
