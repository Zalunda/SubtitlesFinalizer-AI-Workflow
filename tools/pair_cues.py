#!/usr/bin/env python3
"""
pair_cues.py - print, for every finalized subtitle of a working .srt, the English text next to the Japanese of the
debug cues it overlaps. Read-only. It is the evidence to print in the conversation before asking the advisor (or a
stronger model) for the final review of a scene (WORKFLOW.md, wave 3, step 2b): the reviewer only sees the conversation.

Usage:
    python tools/pair_cues.py <base>.WIP.srt [--debug FILE] [--from HH:MM:SS] [--to HH:MM:SS] [--cue-numbers]

Output, one line per finalized subtitle (cues that still have their metadata block, and the injected credits of a final
.srt, are skipped):
    HH:MM:SS | English line 1 / English line 2 | Japanese of the overlapping debug cue(s)

The debug file is <base>.final-ai-debug.srt next to the .srt unless --debug is given. The Japanese is, by priority, the
[manual-input] VoiceText, the [singlevad-ai-refined] VoiceText, the [full-ai] VoiceText, then the OnScreenText (captions).
A cue that is the result of a merge/split shows all the Japanese it overlaps, in time order.

Only the Python standard library is needed.
"""
import argparse
import io
import os
import re
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
TIMING = re.compile(r"^" + TS + r"\s*-->\s*" + TS + r"\s*$")
HEADER = "------- Metadatas -------"
KEYS = [
    r"\[manual-input\] \{VoiceText:(.*?)\}",
    r"\[singlevad-ai-refined\] \{VoiceText:(.*?)\}",
    r"\[full-ai\] \{VoiceText:(.*?)\}",
    r"\[singlevad-ai-refined\] \{OnScreenText:(.*?)\}",
]


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def parse_time(text):
    m = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})(?:[,.](\d{1,3}))?$", text.strip())
    if not m:
        raise SystemExit("bad time %r (use HH:MM:SS[.mmm])" % text)
    return to_ms(m.group(1), m.group(2), m.group(3), (m.group(4) or "0").ljust(3, "0"))


def read_cues(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        text = f.read().replace("\r\n", "\n").replace("\r", "\n")
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 2:
            continue
        # the number line may be missing in a hand-edited block: find the timing line
        idx = next((i for i, l in enumerate(lines[:3]) if TIMING.match(l)), None)
        if idx is None:
            continue
        m = TIMING.match(lines[idx])
        g = m.groups()
        yield {
            "number": lines[0] if idx else "",
            "start": to_ms(*g[0:4]),
            "end": to_ms(*g[4:8]),
            "body": lines[idx + 1:],
        }


def japanese_of(body):
    text = "\n".join(body)
    for pat in KEYS:
        m = re.search(pat, text, re.S)
        if m and m.group(1).strip():
            return " ".join(m.group(1).split())
    return ""


def main():
    ap = argparse.ArgumentParser(description="English subtitle next to the Japanese of the debug cues it overlaps.")
    ap.add_argument("srt", help="the working .srt (or the final .srt)")
    ap.add_argument("--debug", help="the final-ai-debug.srt (default: <base>.final-ai-debug.srt next to the .srt)")
    ap.add_argument("--from", dest="t_from", help="first time to show, HH:MM:SS")
    ap.add_argument("--to", dest="t_to", help="last time to show, HH:MM:SS")
    ap.add_argument("--cue-numbers", action="store_true", help="prefix each line with the cue number of the file")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    base = args.srt
    for suffix in (".WIP.srt", ".srt"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    debug = args.debug or base + ".final-ai-debug.srt"
    if not os.path.isfile(args.srt):
        print("ERROR: not found: " + args.srt, file=sys.stderr)
        return 2
    if not os.path.isfile(debug):
        print("ERROR: debug file not found: %s (use --debug)" % debug, file=sys.stderr)
        return 2

    refs = [(c["start"], c["end"], japanese_of(c["body"])) for c in read_cues(debug)]
    refs = [r for r in refs if r[2]]
    t_from = parse_time(args.t_from) if args.t_from else 0
    t_to = parse_time(args.t_to) if args.t_to else None

    shown = skipped = 0
    for c in read_cues(args.srt):
        body = c["body"]
        if HEADER in body or not body or all(not l.strip() for l in body):
            skipped += 1
            continue
        if c["start"] < t_from or (t_to is not None and c["start"] > t_to):
            continue
        english = " / ".join(l.strip() for l in body if l.strip())
        if english.startswith("Created by "):   # injected credit of a final .srt
            continue
        ja = " ".join(j for (s, e, j) in refs if s < c["end"] and e > c["start"])
        secs = c["start"] // 1000
        stamp = "%02d:%02d:%02d" % (secs // 3600, secs // 60 % 60, secs % 60)
        prefix = (c["number"] + " | ") if args.cue_numbers else ""
        print("%s%s | %s | %s" % (prefix, stamp, english, ja))
        shown += 1
    print("-- %d subtitles shown, %d still with metadata skipped" % (shown, skipped), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
