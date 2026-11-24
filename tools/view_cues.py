#!/usr/bin/env python3
"""
view_cues.py - compact, READ-ONLY view of the cues of a working .srt (so they can be reviewed without
reading the raw metadata blocks).

For every cue that still has its metadata block (not finalized) it prints:
    #<n> <start> --> <end> (<duration>)  [<cps> cps of the current translation]
    JA:  the Japanese (one line when [full-ai] and [singlevad-ai-refined] agree, both + "DIFF" when they differ;
         a [manual-input] VoiceText is shown too)
    EN:  the current {TranslatedText}
    AN:  the first line of the {TranslationAnalysis} (Vector / State / Cadence)
    VIS: the rest of the analysis (what is seen / how it is said)  [omitted with --brief]
    SIL: the [terrain] silences
    MAN: any [manual-input] line (OngoingContext, OngoingSpeakers, Speaker...)
    OTH: any other metadata (Speaker, [finalizer] Question/Suggestion...)
Finalized cues are skipped, unless --all (they are then printed as their subtitle text).

Usage:
    python tools/view_cues.py <file.srt> [--from <cue number | HH:MM:SS[,mmm]>] [--count N] [--brief] [--all] [--old] [--oneline]
--from selects the first cue to show (a cue number, or a time: first cue ending after it); default: the first cue.
--count is the number of cues to show (default 30); it counts the cues printed.
--old adds, under each cue, the overlapping cues (by time) of <base>.OLD.srt, an earlier hand-reviewed version of the
subtitles (made with an older transcriber): good phrasings can be reused, but its timings and content differ.

Only the Python standard library is needed.
"""
import argparse
import os
import re
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
CUE_HEAD = re.compile(r"^(﻿?)(\d+)[ \t]*\r?\n" + TS + r" --> " + TS + r"[ \t]*\r?\n", re.MULTILINE)
HEADER = "------- Metadatas -------"
ENTRY = re.compile(r"^\[([\w-]+)\] \{(\w+):", re.MULTILINE)


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def fmt(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def parse(text):
    """list of dicts: number, start, end, body (text after the timing line), meta (list of (source, key, value)) or None."""
    heads = list(CUE_HEAD.finditer(text))
    cues = []
    for i, m in enumerate(heads):
        end_of_cue = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end_of_cue].strip("\r\n \t")
        meta = None
        if body.startswith(HEADER):
            meta = []
            block = body[len(HEADER):]
            entries = list(ENTRY.finditer(block))
            for j, e in enumerate(entries):
                stop = entries[j + 1].start() if j + 1 < len(entries) else len(block)
                value = block[e.end():stop].strip()
                if value.endswith("}"):
                    value = value[:-1]
                meta.append((e.group(1), e.group(2), value))
        cues.append({
            "number": int(m.group(2)),
            "start": to_ms(*m.groups()[2:6]),
            "end": to_ms(*m.groups()[6:10]),
            "body": body,
            "meta": meta,
        })
    return cues


def get(meta, source, key):
    for s, k, v in meta:
        if s == source and k == key:
            return v
    return None


def oneline(cue, old_cues=None):
    """One compact line per cue: time, duration, speaker, Japanese, current translation (+ OLD)."""
    meta = cue["meta"]
    ja = get(meta, "singlevad-ai-refined", "VoiceText") or get(meta, "full-ai", "VoiceText") or ""
    full = get(meta, "full-ai", "VoiceText")
    diff = " (full-ai: %s)" % full if full and ja and full != ja else ""
    en = (get(meta, "singlevad-ai-refined", "TranslatedText") or "").replace("\n", " / ")
    spk = get(meta, "manual-input", "Speaker") or get(meta, "singlevad-ai-refined", "Speaker") or "-"
    line = "%s %.1fs [%s] %s%s => %s" % (fmt(cue["start"]), (cue["end"] - cue["start"]) / 1000.0, spk, ja, diff, en)
    if old_cues is not None:
        found = [o for o in old_cues if o["end"] > cue["start"] + 100 and o["start"] < cue["end"] - 100]
        if found:
            line += "  || OLD: " + " | ".join(o["body"].replace("\r", "").replace("\n", " / ") for o in found[:3])
    print(line)


def show(cue, brief, old_cues=None):
    dur = (cue["end"] - cue["start"]) / 1000.0
    meta = cue["meta"]
    en = get(meta, "singlevad-ai-refined", "TranslatedText")
    cps = ""
    if en:
        cps = "  [%.1f cps]" % (len(en.replace("\n", " ")) / dur if dur > 0 else 0)
    print("#%d %s --> %s (%.2fs)%s" % (cue["number"], fmt(cue["start"]), fmt(cue["end"]), dur, cps))

    full = get(meta, "full-ai", "VoiceText")
    vad = get(meta, "singlevad-ai-refined", "VoiceText")
    man = get(meta, "manual-input", "VoiceText")
    if man:
        print("  JA(manual): " + man)
    if full == vad or full is None or vad is None:
        print("  JA:  " + (vad or full or "(none)"))
    else:
        print("  JA DIFF!")
        print("    full-ai : " + full)
        print("    vad-ai  : " + vad)
    print("  EN:  " + (en or "(none)").replace("\n", " / "))

    analysis = get(meta, "singlevad-ai-refined", "TranslationAnalysis")
    if analysis:
        lines = analysis.split("\n", 1)
        print("  AN:  " + lines[0])
        if len(lines) > 1 and not brief:
            print("  VIS: " + lines[1].replace("\n", " "))

    sil = get(meta, "terrain", "Silences")
    print("  SIL: " + (sil if sil is not None else "(no terrain line)"))

    if old_cues is not None:
        # the cues of the OLD.srt (earlier, hand-reviewed version) that overlap this cue in time
        found = [o for o in old_cues if o["end"] > cue["start"] + 100 and o["start"] < cue["end"] - 100]
        if found:
            for o in found[:4]:
                print("  OLD: [%s] %s" % (fmt(o["start"])[3:8], o["body"].replace("\r", "").replace("\n", " / ")))
        else:
            print("  OLD: (nothing at this time)")

    shown = {("full-ai", "VoiceText"), ("singlevad-ai-refined", "VoiceText"), ("singlevad-ai-refined", "TranslatedText"),
             ("singlevad-ai-refined", "TranslationAnalysis"), ("terrain", "Silences"), ("manual-input", "VoiceText")}
    for s, k, v in meta:
        if (s, k) in shown:
            continue
        tag = "MAN" if s == "manual-input" else "OTH"
        print("  %s: [%s] %s = %s" % (tag, s, k, v.replace("\n", " / ")))
    print()


def main():
    ap = argparse.ArgumentParser(description="Compact read-only view of the cues of a working .srt.")
    ap.add_argument("file")
    ap.add_argument("--from", dest="start", default=None, help="cue number or time (HH:MM:SS[,mmm])")
    ap.add_argument("--count", type=int, default=30)
    ap.add_argument("--brief", action="store_true", help="omit the visual/vocal paragraph of the analysis")
    ap.add_argument("--all", action="store_true", help="also print the finalized cues (as their subtitle text)")
    ap.add_argument("--oneline", action="store_true", help="one compact line per cue (time, speaker, Japanese, translation, OLD): to skim a part quickly")
    ap.add_argument("--old", action="store_true", help="also show, for each cue, the overlapping cues of <base>.OLD.srt (earlier hand-reviewed version)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Japanese text on a cp1252 Windows console

    with open(args.file, "r", encoding="utf-8", newline="") as f:
        cues = parse(f.read())

    first = 0
    if args.start:
        t = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.](\d{1,3}))?", args.start)
        if t:
            ms = to_ms(t.group(1), t.group(2), t.group(3), (t.group(4) or "0").ljust(3, "0"))
            first = next((i for i, c in enumerate(cues) if c["end"] > ms), len(cues))
        elif args.start.isdigit():
            n = int(args.start)
            first = next((i for i, c in enumerate(cues) if c["number"] >= n), len(cues))
        else:
            print("ERROR: --from must be a cue number or a time HH:MM:SS[,mmm]", file=sys.stderr)
            return 2

    old_cues = None
    if args.old:
        base = os.path.basename(args.file)
        for suffix in (".WIP.srt", ".srt"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        folder = os.path.dirname(os.path.abspath(args.file))
        old_path = os.path.join(folder, base + ".OLD.srt")
        if not os.path.isfile(old_path):
            # fallback: one long-named OLD file of the part ('<base> - Actress - Title.OLD.srt')
            import glob
            found = glob.glob(os.path.join(glob.escape(folder), glob.escape(base) + " *.OLD.srt"))
            if len(found) == 1:
                old_path = found[0]
        if not os.path.isfile(old_path):
            print("ERROR: --old: not found: " + old_path, file=sys.stderr)
            return 2
        with open(old_path, "r", encoding="utf-8", newline="") as f:
            old_cues = parse(f.read())

    total = len(cues)
    todo = sum(1 for c in cues if c["meta"] is not None)
    printed = 0
    for c in cues[first:]:
        if printed >= args.count:
            break
        if c["meta"] is None:
            if args.all:
                print("#%d %s --> %s  FINAL: %s\n" % (c["number"], fmt(c["start"]), fmt(c["end"]), c["body"].replace("\n", " / ")))
                printed += 1
            continue
        if args.oneline:
            oneline(c, old_cues)
        else:
            show(c, args.brief, old_cues)
        printed += 1
    print("-- %d cues in the file, %d not finalized yet --" % (total, todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
