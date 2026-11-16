#!/usr/bin/env python3
"""
apply_cues.py - write the finalizer's decisions into a working .srt (finalize, split, merge, or add a question),
so the metadata blocks don't have to be retyped in Edit calls.

The decisions come from a text file (UTF-8). Each decision is a block starting with an '@' line that names the
cue(s) by the START TIME of their timing line (HH:MM:SS,mmm):

    # comment lines start with '#'

    @00:00:05,317                        FINALIZE: the cue keeps its timing, metadata is removed, this is the text
    It's time for your sponge bath!      (1 or 2 text lines)

    @00:00:12,094                        SPLIT: each timing line starts a new cue (they must lie inside the original
    00:00:12,094 --> 00:00:14,245        range and not overlap). Also use this to TRIM a cue (one timing line).
    Heard your discharge date's set.
    00:00:14,690 --> 00:00:15,788
    Congrats.

    @00:00:20,050+00:00:23,783           MERGE: several back-to-back cues (consecutive in the file) become one cue
    Alright, let's get this off you.     from the first start to the last end (or give an explicit timing line)

    @00:00:40,112                        QUESTION: the cue keeps its metadata block and gets
    Q: Is she saying X or Y?             [finalizer] {Question:...}  (and [finalizer] {Suggestion:...} with S:)
    S: Your best guess here.

    @00:07:35,402                        DELETE: the cue disappears from the file (ONLY after the user confirmed there is no speech)
    D:

    R: Not sure about "X": check the audio.   (added to ANY finalize/split/merge block: the cue is finalized as usual and
                                              a line is appended to <base>.review.md for the user's audio check)

    @!00:00:20,050                       REDO: '@!' lets a decision replace a cue that is ALREADY finalized (no metadata)
    Okay, taking it off.                 (same text/split/merge rules; use it for later corrections)

Safety:
  * all decisions are validated first; if one is wrong NOTHING is written (unknown time, cue already finalized,
    cue with no metadata block, pieces outside the original range or overlapping, merge not consecutive...)
  * only the named cues are touched; BOM and line endings are kept (each new cue uses the line ending of the
    cue it replaces); the numbers of new pieces repeat the original number (renumber at the end with
    tools/renumber_srt.py)
  * warnings (not errors): more than 2 lines, a line longer than 42 characters, reading speed above 20 cps

Usage:
    python tools/apply_cues.py <working.srt> <decisions.txt> [--dry-run]

Only the Python standard library is needed.
"""
import argparse
import os
import re
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
CUE_HEAD = re.compile(r"^(﻿?)(\d+)([ \t]*\r?\n)" + TS + r" --> " + TS + r"([ \t]*)(\r?\n)", re.MULTILINE)
TIMING_LINE = re.compile(r"^" + TS + r"\s*-->\s*" + TS + r"\s*$")
START_KEY = re.compile(r"^" + TS + r"$")
HEADER = "------- Metadatas -------"
MAX_LINE = 42
MAX_LINES = 2
MAX_CPS = 20.0


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def fmt(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def parse_srt(text):
    heads = list(CUE_HEAD.finditer(text))
    cues = []
    for i, m in enumerate(heads):
        span_end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body_raw = text[m.end():span_end]
        trailing = re.search(r"(\r?\n|[ \t])*\Z", body_raw).group(0)
        cues.append({
            "m": m, "begin": m.start(), "end_pos": span_end, "bom": m.group(1), "number": m.group(2),
            "nl": m.group(len(m.groups())),  # line ending of the timing line
            "start": to_ms(*m.groups()[3:7]), "end": to_ms(*m.groups()[7:11]),
            "body": body_raw[:len(body_raw) - len(trailing)], "trailing": trailing,
            "has_meta": body_raw.lstrip().startswith(HEADER),
        })
    return cues


def parse_decisions(text):
    """list of dicts: keys(list of start ms), timed(list of (start,end,[lines]) or None), plain(list of lines), q, s, line"""
    decisions = []
    cur = None
    for lineno, raw in enumerate(text.lstrip("﻿").splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("#") or (not line.strip() and cur is None):
            continue
        if line.startswith("@"):
            keys = []
            redo = line[1:].startswith("!")
            for part in line[1:].lstrip("!").split("+"):
                k = START_KEY.match(part.strip())
                if not k:
                    raise ValueError("line %d: bad cue start time %r" % (lineno, part))
                keys.append(to_ms(*k.groups()))
            cur = {"keys": keys, "pieces": [], "plain": [], "q": None, "s": None, "line": lineno, "redo": redo, "r": [], "delete": False}
            decisions.append(cur)
            continue
        if cur is None:
            raise ValueError("line %d: text before any '@<start>' line" % lineno)
        if not line.strip():
            continue
        t = TIMING_LINE.match(line.strip())
        if t:
            cur["pieces"].append([to_ms(*t.groups()[0:4]), to_ms(*t.groups()[4:8]), []])
        elif line.startswith("Q:"):
            cur["q"] = line[2:].strip()
        elif line.startswith("S:"):
            cur["s"] = line[2:].strip()
        elif line.startswith("R:"):
            cur["r"].append(line[2:].strip())
        elif line.strip() == "D:":
            cur["delete"] = True
        elif cur["pieces"]:
            cur["pieces"][-1][2].append(line)
        else:
            cur["plain"].append(line)
    return decisions


def check_text(lines, start, end, where, warnings):
    if len(lines) > MAX_LINES:
        warnings.append("%s: %d lines (max %d)" % (where, len(lines), MAX_LINES))
    for l in lines:
        if len(l) > MAX_LINE:
            warnings.append("%s: line of %d characters (max ~%d): %s" % (where, len(l), MAX_LINE, l))
    dur = (end - start) / 1000.0
    chars = len(" ".join(lines))
    if dur > 0 and chars / dur > MAX_CPS:
        warnings.append("%s: reading speed %.1f cps (%d chars in %.2fs)" % (where, chars / dur, chars, dur))


def build_cue(cue, start, end, lines, trailing):
    nl = cue["nl"]
    return "%s%s%s%s --> %s%s%s%s" % (cue["bom"], cue["number"], nl, fmt(start), fmt(end), nl, nl.join(lines), trailing)


def main():
    ap = argparse.ArgumentParser(description="Apply finalizer decisions to a working .srt.")
    ap.add_argument("srt")
    ap.add_argument("decisions")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.srt, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    with open(args.decisions, "r", encoding="utf-8") as f:
        try:
            decisions = parse_decisions(f.read())
        except ValueError as e:
            print("ERROR: " + str(e), file=sys.stderr)
            return 1

    cues = parse_srt(text)
    by_start = {}
    for i, c in enumerate(cues):
        by_start.setdefault(c["start"], []).append(i)

    errors, warnings = [], []
    replace = {}   # cue index -> replacement string (or "" to drop)
    counts = {"finalized": 0, "split": 0, "merged": 0, "questions": 0, "deleted": 0}
    reviews = []   # (start ms, final text lines, notes) for the cues decided with R: lines

    for d in decisions:
        where = "@%s (line %d of the decisions)" % ("+".join(fmt(k) for k in d["keys"]), d["line"])
        idxs = []
        for k in d["keys"]:
            found = by_start.get(k, [])
            if len(found) != 1:
                errors.append("%s: %d cues start at %s" % (where, len(found), fmt(k)))
            else:
                idxs.append(found[0])
        if len(idxs) != len(d["keys"]):
            continue
        if any(i in replace for i in idxs):
            errors.append("%s: a cue is named by two decisions" % where)
            continue
        if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
            errors.append("%s: merged cues are not consecutive in the file" % where)
            continue
        group = [cues[i] for i in idxs]
        for c in group:
            if not c["has_meta"] and not d["redo"]:
                errors.append("%s: cue at %s is already finalized (no metadata block)" % (where, fmt(c["start"])))
        if any(not c["has_meta"] for c in group) and not d["redo"]:
            continue

        first, last = group[0], group[-1]
        if d["delete"]:
            if len(group) != 1 or d["pieces"] or d["plain"] or d["q"] is not None:
                errors.append("%s: a D: (delete) decision must be alone (one cue, no text)" % where)
                continue
            replace[idxs[0]] = ""          # the whole cue disappears from the file
            counts["deleted"] += 1
            continue
        if d["r"] and d["q"] is not None:
            errors.append("%s: R: (check later) is for a finalized cue; a Q: cue is already a pending question" % where)
            continue
        if d["redo"] and d["q"] is not None:
            errors.append("%s: Q: cannot be combined with '@!' (redo)" % where)
            continue
        if d["q"] is not None:
            if len(group) != 1 or d["pieces"] or d["plain"]:
                errors.append("%s: a Q: decision must be alone (one cue, no text)" % where)
                continue
            nl = first["nl"]
            # drop a previous finalizer question/suggestion (single-line), keep every other byte of the block
            new_body = re.sub(r"^\[finalizer\][^\r\n]*(\r?\n|\Z)", "", first["body"], flags=re.MULTILINE).rstrip("\r\n")
            new_body += nl +"[finalizer] {Question:%s}" % d["q"]
            if d["s"]:
                new_body += nl + "[finalizer] {Suggestion:%s}" % d["s"]
            replace[idxs[0]] = "%s%s%s%s --> %s%s%s%s" % (first["bom"], first["number"], nl, fmt(first["start"]), fmt(first["end"]), nl, new_body, first["trailing"])
            counts["questions"] += 1
            continue
        if d["s"] is not None:
            errors.append("%s: S: without Q:" % where)
            continue

        if d["pieces"]:
            if d["plain"]:
                errors.append("%s: text before the first timing line" % where)
                continue
            pieces = d["pieces"]
        else:
            if not d["plain"]:
                errors.append("%s: no text" % where)
                continue
            pieces = [[first["start"], last["end"], d["plain"]]]
        ok = True
        prev_end = None
        for (s, e, lines) in pieces:
            if not lines:
                errors.append("%s: piece %s --> %s has no text" % (where, fmt(s), fmt(e)))
                ok = False
            if e <= s:
                errors.append("%s: piece %s --> %s ends before it starts" % (where, fmt(s), fmt(e)))
                ok = False
            if (s < first["start"] or e > last["end"]) and d["redo"]:
                warnings.append("%s: piece %s --> %s goes outside the original range (allowed with '@!', e.g. to fix a timing)" % (where, fmt(s), fmt(e)))
            elif s < first["start"] or e > last["end"]:
                errors.append("%s: piece %s --> %s is outside the original range %s --> %s" % (where, fmt(s), fmt(e), fmt(first["start"]), fmt(last["end"])))
                ok = False
            if prev_end is not None and s < prev_end:
                errors.append("%s: piece at %s overlaps the previous piece" % (where, fmt(s)))
                ok = False
            prev_end = e
            check_text(lines, s, e, "%s [%s]" % (where, fmt(s)), warnings)
        if not ok:
            continue
        out = []
        for n, (s, e, lines) in enumerate(pieces):
            is_last = n == len(pieces) - 1
            sep = last["trailing"] if is_last else first["nl"] + first["nl"]
            out.append(build_cue(first, s, e, lines, sep))
        replace[idxs[0]] = "".join(out)
        if d["r"]:
            reviews.append((pieces[0][0], [l for pc in pieces for l in pc[2]], d["r"]))
        for i in idxs[1:]:
            replace[i] = ""
        if len(group) > 1:
            counts["merged"] += 1
        elif len(pieces) > 1:
            counts["split"] += 1
        else:
            counts["finalized"] += 1

    for w in warnings:
        print("WARNING: " + w)
    if errors:
        for e in errors:
            print("ERROR: " + e, file=sys.stderr)
        print("Nothing written (%d errors)." % len(errors), file=sys.stderr)
        return 1

    pieces_out = []
    pos = 0
    for i, c in enumerate(cues):
        if i in replace:
            pieces_out.append(text[pos:c["begin"]])
            pieces_out.append(replace[i])
            pos = c["end_pos"]
    pieces_out.append(text[pos:])
    result = "".join(pieces_out)

    summary = "%d finalized, %d split, %d merged, %d questions added, %d deleted" % (counts["finalized"], counts["split"], counts["merged"], counts["questions"], counts["deleted"])
    if args.dry_run:
        print("dry run OK: " + summary)
        return 0
    with open(args.srt, "w", encoding="utf-8", newline="") as f:
        f.write(result)
    print("done: " + summary)
    if reviews:
        # '<base>.review.md' next to the .srt: the cues the assistant is not sure about, for the user's audio check
        base = os.path.basename(args.srt)
        for suffix in (".WIP.srt", ".srt"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        review_path = os.path.join(os.path.dirname(os.path.abspath(args.srt)), base + ".review.md")
        new_file = not os.path.isfile(review_path)
        with open(review_path, "a", encoding="utf-8", newline="") as f:
            if new_file:
                f.write("# %s - cues to re-check\n\n" % base)
                f.write("Cues finalized with a doubt. Listen / ask the transcriber, tick the box when checked "
                        "(`- [x]`) and tell me the result.\n\n")
            for start, lines, notes in reviews:
                f.write("- [ ] %s | %s | %s\n" % (fmt(start)[:8], " / ".join(lines), " ; ".join(notes)))
        print("review notes added to %s (%d)" % (review_path, len(reviews)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
