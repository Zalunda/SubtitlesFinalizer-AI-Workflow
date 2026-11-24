#!/usr/bin/env python3
"""
finalize_srt.py - last step, run ONCE when the subtitles are final: produce the FINAL <base>.srt from the
work-in-progress <base>.WIP.srt.

What it does (settings come from a config file, see below; built-in defaults 300 ms / 1000 ms):
  1. every subtitle's end gets +ExpandSubtileDuration (300 ms)
  2. every subtitle is made at least MinimumSubtitleDuration (1 s) long: the end is pushed, never the start
  3. but an end never goes past the start of the NEXT subtitle (minus --gap-ms, default 0)
  4. an end is never made earlier than it already was (an existing overlap is left alone and reported)
  5. the subtitles listed in "SubtitlesToInject" (credits...) are added, WITHOUT overlapping any dialogue: if there
     is not enough room they are crunched (shortened, down to a duration of 0: a subtitle with no room at all is
     still injected, with duration 0)
  6. the cues are renumbered 1..N
The start times of the existing subtitles are never touched.

Config file (JSON, same shape as the FunscriptToolbox output rule). Looked up in this order:
    --config FILE  >  <folder of the .WIP.srt>/finalize.config.json  >  <repo root>/finalize.config.json
    {
      "Id": "final-ai-srt",                         (informative, ignored)
      "MinimumSubtitleDuration": "00:00:01",
      "ExpandSubtileDuration": "00:00:00.300",      ("ExpandSubtitleDuration" is accepted too)
      "SubtitlesToInject": [
        { "Origin": "Start", "InjectInAllFiles": true, "OffsetTime": "00:00:00", "Duration": "00:00:10",
          "Lines": ["line 1", "line 2"] }
      ]
    }
  Origin "Start": the subtitle starts at OffsetTime from the start of the video; its end is shortened if a dialogue
                  subtitle starts before (e.g. credits 0-10 s, first dialogue at 3.07 s -> credits 0-3.07 s).
  Origin "End":   the subtitle STARTS OffsetTime before the end of the part's video (video duration - OffsetTime) and
                  lasts Duration: OffsetTime = Duration -> ends exactly at the end of the video; a NEGATIVE
                  OffsetTime puts it after the end of the scene. Its start is moved later if a dialogue
                  subtitle is still showing. (Origin "Start" with a negative OffsetTime = before the start of
                  the video; SRT has no negative time, so it is clamped to 0.) The video duration of each part comes from the
                  file <folder>/.parts-duration.txt (or '<SCENE>-.parts-duration.txt', the only '*.parts-duration.txt' of the folder), one line per part:   HNVR-141-A.mp4 00:29:40.970
                  (an Origin "End" injection without that file/line is an ERROR, nothing is written).
  InjectInAllFiles: true = in every part (A, B, C...) of the scene; false = only in the first part for "Start",
                  only in the last part for "End" (the parts are the sibling .WIP.srt files of the same folder: part token A, D, R1, 2... right after the scene id).
  Times are C# TimeSpan strings: [-][d.]hh:mm:ss[.fff].

Files: the WIP file is never modified, so running the tool twice can't add the time twice; the plain <base>.srt is
always rebuilt from it (overwritten if it exists). Refuses a file that still has metadata blocks.
Only the timing lines change, plus the injected cues, the renumbering and the line endings (the final file is always
Windows CRLF, whatever mix the WIP file has: so the WIP file never needs to be renumbered or converted); the BOM is kept.

Usage:
    python tools/finalize_srt.py <base>.WIP.srt [--config FILE] [--no-inject] [--out FILE]
                                 [--extend-ms N] [--min-ms N] [--gap-ms N]

Only the Python standard library is needed.
"""
import argparse
import json
import os
import re
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
TIMING = re.compile(r"^" + TS + r" --> " + TS + r"(?=[ \t]*\r?$)", re.MULTILINE)
NUMBER_LINE = re.compile(r"^(﻿?)(\d+)([ \t]*\r?\n)(?=" + TS + r" --> " + TS + ")", re.MULTILINE)
METADATA_HEADER = "------- Metadatas -------"
CONFIG_NAME = "finalize.config.json"
TIMESPAN = re.compile(r"^(-)?(?:(\d+)\.)?(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d{1,7}))?$")


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def fmt(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def parse_timespan(text):
    m = TIMESPAN.match(str(text).strip())
    if not m:
        raise ValueError("bad TimeSpan %r (use [-][d.]hh:mm:ss[.fff])" % text)
    sign, days, h, mi, s, frac = m.groups()
    ms = (((int(days or 0) * 24 + int(h)) * 60 + int(mi)) * 60 + int(s)) * 1000
    ms += int(round(float("0." + frac) * 1000)) if frac else 0
    return -ms if sign else ms


def find_config(args):
    if args.config:
        return args.config if os.path.isfile(args.config) else None
    candidates = [os.path.join(os.path.dirname(os.path.abspath(args.srt)), CONFIG_NAME),
                  os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CONFIG_NAME)]
    return next((c for c in candidates if os.path.isfile(c)), None)


PARTS_DURATION_NAME = ".parts-duration.txt"


def read_parts_durations(folder):
    """{part base name: duration ms} from <folder>/.parts-duration.txt: lines 'HNVR-141-A.mp4 00:29:40.970'."""
    path = os.path.join(folder, PARTS_DURATION_NAME)
    if not os.path.isfile(path):
        # the user's process names it '<SCENE>-.parts-duration.txt': accept any '*.parts-duration.txt' (only if there is exactly one)
        found = [f for f in os.listdir(folder or ".") if f.endswith(PARTS_DURATION_NAME)]
        if len(found) != 1:
            return None
        path = os.path.join(folder, found[0])
    result = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.rsplit(None, 1)
            if len(parts) != 2:
                continue
            name = parts[0]
            if "." in name and name.lower().rsplit(".", 1)[1] in ("mp4", "mkv", "avi", "mov", "m4v", "webm", "wmv"):
                name = name.rsplit(".", 1)[0]
            try:
                result[name] = parse_timespan(parts[1])
            except ValueError:
                continue
    return result


# A part token is 1-3 capital letters / digits ('A', 'D', 'R1', '2'), written right after the scene id (separator '-'
# or '_') and followed by either '.WIP.srt' or ' - <title>': 'HNVR-141-A.WIP.srt', 'PPVR-020-A - Mei Satsuki [x].WIP.srt',
# 'VRKM-0809-R1 - ... .WIP.srt', 'IPVR-380_2.WIP.srt'.
PART_RE = re.compile(r"^(.*?)[-_]([A-Z0-9]{1,3})(?: - .*)?\.WIP\.srt$")


def part_position(srt_path):
    """('first'|'last'|'middle'|'only', part) of this part among the sibling .WIP.srt files of its folder (same scene prefix)."""
    name = os.path.basename(srt_path)
    m = PART_RE.match(name)
    if not m:
        return "only", None
    prefix, letter = m.group(1), m.group(2)
    letters = sorted(
        {mm.group(2) for f in os.listdir(os.path.dirname(os.path.abspath(srt_path)) or ".")
         for mm in [PART_RE.match(f)] if mm and mm.group(1) == prefix},
        key=lambda s: (len(s), s))
    if len(letters) <= 1:
        return "only", letter
    pos = "middle"
    if letter == letters[0]:
        pos = "first"
    if letter == letters[-1]:
        pos = "last" if pos != "first" else "first"
    return pos, letter


def main():
    ap = argparse.ArgumentParser(description="Produce the final .srt from the .WIP.srt (longer display time + injected credits).")
    ap.add_argument("srt")
    ap.add_argument("--config", help="config file (default: finalize.config.json next to the srt, then at the repo root)")
    ap.add_argument("--no-inject", action="store_true", help="don't inject the subtitles of the config")
    ap.add_argument("--out", help="output file (default: the input name without '.WIP', i.e. <base>.srt)")
    ap.add_argument("--extend-ms", type=int, default=None, help="override ExpandSubtileDuration of the config (default 300)")
    ap.add_argument("--min-ms", type=int, default=None, help="override MinimumSubtitleDuration of the config (default 1000)")
    ap.add_argument("--gap-ms", type=int, default=0, help="keep this gap before the next subtitle (default 0)")
    ap.add_argument("--eol", choices=["crlf", "lf", "keep"], default="crlf", help="line endings of the FINAL file (default crlf)")
    args = ap.parse_args()

    if not os.path.isfile(args.srt):
        print("ERROR: not found: " + args.srt, file=sys.stderr)
        return 2
    if args.out:
        target_path = args.out
    elif args.srt.endswith(".WIP.srt"):
        target_path = args.srt[: -len(".WIP.srt")] + ".srt"
    else:
        print("ERROR: the input is not a *.WIP.srt file: give the output with --out (never overwrite the input).", file=sys.stderr)
        return 2
    if os.path.abspath(target_path) == os.path.abspath(args.srt):
        print("ERROR: the output would overwrite the input.", file=sys.stderr)
        return 2

    # ---- config
    extend_ms, min_ms, injections = 300, 1000, []
    config_path = find_config(args)
    if args.config and not config_path:
        print("ERROR: config not found: " + args.config, file=sys.stderr)
        return 2
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            if "ExpandSubtileDuration" in cfg or "ExpandSubtitleDuration" in cfg:
                extend_ms = parse_timespan(cfg.get("ExpandSubtileDuration", cfg.get("ExpandSubtitleDuration")))
            if "MinimumSubtitleDuration" in cfg:
                min_ms = parse_timespan(cfg["MinimumSubtitleDuration"])
            for inj in cfg.get("SubtitlesToInject", []) or []:
                origin = inj["Origin"]
                if origin not in ("Start", "End"):
                    raise ValueError("Origin must be 'Start' or 'End', got %r" % origin)
                injections.append({
                    "origin": origin,
                    "all": bool(inj.get("InjectInAllFiles", True)),
                    "offset": parse_timespan(inj["OffsetTime"]),
                    "duration": parse_timespan(inj["Duration"]),
                    "lines": [str(x) for x in inj["Lines"]],
                })
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            print("ERROR: bad config %s: %s" % (config_path, e), file=sys.stderr)
            return 2
        print("config: " + config_path)
    else:
        print("NOTE: no %s found (srt folder or repo root): no subtitle injected, built-in timing (+300 ms, min 1 s)." % CONFIG_NAME)
    if args.extend_ms is not None:
        extend_ms = args.extend_ms
    if args.min_ms is not None:
        min_ms = args.min_ms

    with open(args.srt, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    if METADATA_HEADER in text:
        print("ERROR: the file still has metadata blocks (cues not finalized yet): not processed.", file=sys.stderr)
        return 1
    matches = list(TIMING.finditer(text))
    if not matches:
        print("ERROR: no timing line found", file=sys.stderr)
        return 1
    cues = [[to_ms(*m.groups()[0:4]), to_ms(*m.groups()[4:8])] for m in matches]

    # ---- 1) display time
    stats = {"full": 0, "limited": 0, "unchanged": 0, "min_applied": 0}
    problems = []
    new_ends = []
    for i, (start, end) in enumerate(cues):
        target = max(end + extend_ms, start + min_ms)
        limit = None
        if i + 1 < len(cues):
            nxt = cues[i + 1][0]
            if nxt < start:
                problems.append("cue at %s: the next cue starts before it (out of order)" % fmt(start))
            limit = nxt - args.gap_ms
        new_end = target if limit is None else min(target, limit)
        if new_end < end:
            if limit is not None and end > cues[i + 1][0]:
                problems.append("cue at %s overlaps the next cue by %d ms (left as is)" % (fmt(start), end - cues[i + 1][0]))
            new_end = end
        if new_end == end:
            stats["unchanged"] += 1
        elif new_end == target:
            stats["full"] += 1
        else:
            stats["limited"] += 1
        if end + extend_ms < start + min_ms and new_end > end:
            stats["min_applied"] += 1
        if new_end - start < min_ms:
            problems.append("cue at %s is still only %d ms long (the next cue starts too early)" % (fmt(start), new_end - start))
        new_ends.append(new_end)

    out = []
    pos = 0
    for m, (start, _end), new_end in zip(matches, cues, new_ends):
        out.append(text[pos:m.start()])
        out.append("%s --> %s" % (fmt(start), fmt(new_end)))
        pos = m.end()
    out.append(text[pos:])
    result = "".join(out)

    # ---- 2) injected subtitles (the BOM is set aside while editing, put back at the end)
    bom = "\ufeff" if result.startswith("\ufeff") else ""
    result = result[len(bom):]
    nl = "\r\n" if result.count("\r\n") * 2 >= result.count("\n") else "\n"
    where, letter = part_position(args.srt)
    injected = []
    if not args.no_inject:
        existing = list(zip([c[0] for c in cues], new_ends))   # the dialogue subtitles (start, final end)
        part_base = os.path.basename(args.srt)
        part_base = part_base[: -len(".WIP.srt")] if part_base.endswith(".WIP.srt") else os.path.splitext(part_base)[0]
        durations = None
        for inj in injections:
            if not inj["all"]:
                wanted = "last" if inj["origin"] == "End" else "first"
                if where not in ("only", wanted):
                    continue
            label = "%s subtitle \"%s\"" % (inj["origin"], inj["lines"][0][:30] if inj["lines"] else "")
            wanted_ms = inj["duration"]
            if inj["origin"] == "Start":
                # starts at OffsetTime from the start of the video (negative = before the start: clamped to 0)
                s = inj["offset"]
                e = s + wanted_ms
                if e < 0:
                    problems.append("%s is entirely before the start of the video: injected at 0 with duration 0" % label)
                if s < 0:
                    s = 0
                e = max(e, s)
                if any(cs <= s < ce for cs, ce in existing):
                    e = s                                        # a dialogue is showing: no room, duration 0
                else:
                    nxt = [cs for cs, _ce in existing if cs >= s]
                    if nxt:
                        e = max(s, min(e, min(nxt) - args.gap_ms))   # crunched to fit before the first dialogue
            else:
                if durations is None:
                    durations = read_parts_durations(os.path.dirname(os.path.abspath(args.srt)))
                dur = None if durations is None else durations.get(part_base)
                if dur is None:
                    print("ERROR: %s needs the duration of %s.mp4 in %s (one 'name.mp4 HH:MM:SS.mmm' line per part); "
                          "nothing written (use --no-inject to skip the injections)." % (label, part_base, PARTS_DURATION_NAME), file=sys.stderr)
                    return 1
                # Origin End: the subtitle starts OffsetTime BEFORE the end of the video (negative = after the end)
                s = dur - inj["offset"]
                e = s + wanted_ms
                if s < 0:
                    s = 0
                    e = max(e, s)
                overl = [ce for cs, ce in existing if ce > s and cs < e]
                if overl:
                    s = max(s, max(overl) + args.gap_ms)         # crunched to fit after the last dialogue
                    if s > e:
                        s = e                                    # no room: duration 0
                if max(ce for _cs, ce in existing) > dur:
                    problems.append("%s: a dialogue subtitle ends after the video duration (%s)" % (label, fmt(dur)))
            if e - s < wanted_ms:
                problems.append("%s crunched from %.1f s to %.1f s to avoid overlapping the dialogue" % (label, wanted_ms / 1000.0, (e - s) / 1000.0))
            injected.append((s, e, inj["lines"]))

    for start, end, lines in sorted(injected, key=lambda x: x[0]):
        block = "0%s%s --> %s%s%s%s%s" % (nl, fmt(start), fmt(end), nl, nl.join(lines), nl, nl)
        heads = list(NUMBER_LINE.finditer(result))
        cue_starts = [to_ms(*TIMING.search(result, h.end()).groups()[0:4]) for h in heads]
        idx = next((i for i, st in enumerate(cue_starts) if st > start), None)
        if idx is None:   # after every existing subtitle: append at the end
            tail = re.search(r"(\r?\n)*\Z", result).group(0)
            result = result[: len(result) - len(tail)] + nl + nl + block.rstrip("\r\n") + (tail if tail else nl)
        else:             # keep the file sorted by start time
            result = result[: heads[idx].start()] + block + result[heads[idx].start():]

    # ---- 3) renumber 1..N
    counter = [0]

    def renum(m):
        counter[0] += 1
        return "%s%d%s" % (m.group(1), counter[0], m.group(3))

    result = NUMBER_LINE.sub(renum, result)
    if counter[0] != len(cues) + len(injected):
        print("ERROR: %d cues expected but %d number lines found after processing: nothing written." % (len(cues) + len(injected), counter[0]), file=sys.stderr)
        return 1
    if args.eol != "keep":
        # the FINAL file must be Windows CRLF (the WIP file may mix CRLF/LF): convert every line ending
        result = result.replace("\r\n", "\n")
        if args.eol == "crlf":
            result = result.replace("\n", "\r\n")
    result = bom + result

    with open(target_path, "w", encoding="utf-8", newline="") as f:
        f.write(result)
    print("%d subtitles + %d injected -> %s" % (len(cues), len(injected), target_path))
    print("end extended by the full amount: %d | limited by the next subtitle: %d | unchanged: %d | minimum duration applied: %d"
          % (stats["full"], stats["limited"], stats["unchanged"], stats["min_applied"]))
    if injections and not injected and not args.no_inject:
        print("NOTE: %d subtitle(s) to inject in the config, none for this part (%s)." % (len(injections), where))
    for p in problems:
        print("WARNING: " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
