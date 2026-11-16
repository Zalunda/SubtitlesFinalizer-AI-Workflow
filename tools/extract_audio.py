#!/usr/bin/env python3
"""
extract_audio.py - cut the audio of one or several subtitles (or of any time range) out of the scene's video
into .wav files, with ffmpeg, so they can be given to the transcriber to redo a transcription.

The video is never read by the assistant: it is only passed to ffmpeg. The .wav files are git-ignored.

Usage:
    python tools/extract_audio.py <working.srt> --at 00:21:03 [--at ...] [--cue N] [options]
    python tools/extract_audio.py <working.srt-or-video> --range 00:21:03.500 00:21:07.250 [options]

Selecting the subtitles (needs a .srt, normally the .WIP.srt; the video is the .mp4 with the same base name, without ".WIP", next to it, unless --video):
    --at TIME        the subtitle that contains TIME (or, if none, the first one that starts after it).
                     TIME is HH:MM:SS[.mmm] or HH:MM:SS,mmm. Can be repeated.
    --cue N          the subtitle with number N in the file (numbers as written in the file). Can be repeated.
    --range S E      an explicit time range (no subtitle needed). Can be repeated (give S E each time).

Options:
    --pad-ms N       add N ms of context before and after (default 0 = exactly the subtitle's timing)
    --video FILE     the video (default: <srt base name>.mp4 next to the .srt)
    --out-dir DIR    where to write (default: a 'clips' folder next to the .srt)
    --rate HZ        sample rate (default 16000)
    --channels N     1 = mono (default), 2 = stereo
    --ffmpeg PATH    ffmpeg executable (default: 'ffmpeg' from the PATH)

Each line printed is numbered in the order of the arguments: the transcriber AI does not see file names, so send the clips in
that order and give the user the numbered table with the durations.

Output file name:  <base>.<start>-<end>.wav   e.g.  HNVR-141-C.00-21-03.897_00-21-06.204.wav

Only the Python standard library and ffmpeg are needed.
"""
import argparse
import os
import re
import subprocess
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
CUE_HEAD = re.compile(r"^(﻿?)(\d+)[ \t]*\r?\n" + TS + r" --> " + TS, re.MULTILINE)
TIME_ARG = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})(?:[,.](\d{1,3}))?$")


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def parse_time(text):
    m = TIME_ARG.match(text.strip())
    if not m:
        raise ValueError("bad time %r (use HH:MM:SS[.mmm])" % text)
    return to_ms(m.group(1), m.group(2), m.group(3), (m.group(4) or "0").ljust(3, "0"))


def fmt(ms, sep="."):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d%s%03d" % (h, m, s, sep, ms)


def read_cues(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    return [{"number": int(m.group(2)), "start": to_ms(*m.groups()[2:6]), "end": to_ms(*m.groups()[6:10])}
            for m in CUE_HEAD.finditer(text)]


def main():
    ap = argparse.ArgumentParser(description="Extract the audio of subtitles into .wav files (ffmpeg).")
    ap.add_argument("source", help="the working .srt (or a video, with --range)")
    ap.add_argument("--at", action="append", default=[], metavar="TIME")
    ap.add_argument("--cue", action="append", default=[], type=int, metavar="N")
    ap.add_argument("--range", action="append", default=[], nargs=2, metavar=("START", "END"))
    ap.add_argument("--pad-ms", type=int, default=0)
    ap.add_argument("--video")
    ap.add_argument("--out-dir")
    ap.add_argument("--rate", type=int, default=16000)
    ap.add_argument("--channels", type=int, default=1, choices=[1, 2])
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args()

    if not (args.at or args.cue or args.range):
        ap.error("give at least one of --at, --cue, --range")
    if not os.path.isfile(args.source):
        print("ERROR: not found: " + args.source, file=sys.stderr)
        return 2

    is_srt = args.source.lower().endswith(".srt")
    base_path = os.path.splitext(args.source)[0]
    if base_path.endswith(".WIP"):
        base_path = base_path[: -len(".WIP")]   # HNVR-141-C.WIP.srt -> HNVR-141-C(.mp4)
    video = args.video or (base_path + ".mp4" if is_srt else args.source)
    if not os.path.isfile(video):
        print("ERROR: video not found: %s (use --video)" % video, file=sys.stderr)
        return 2
    base = os.path.basename(base_path)
    out_dir = args.out_dir or os.path.join(os.path.dirname(os.path.abspath(args.source)), "clips")

    ranges = []
    try:
        for s, e in args.range:
            ranges.append((parse_time(s), parse_time(e)))
        if args.at or args.cue:
            if not is_srt:
                print("ERROR: --at / --cue need the .srt as the first argument", file=sys.stderr)
                return 2
            cues = read_cues(args.source)
            for t in args.at:
                ms = parse_time(t)
                found = next((c for c in cues if c["start"] <= ms < c["end"]), None) or next((c for c in cues if c["start"] > ms), None)
                if not found:
                    print("ERROR: no subtitle at or after " + t, file=sys.stderr)
                    return 1
                ranges.append((found["start"], found["end"]))
            for n in args.cue:
                found = [c for c in cues if c["number"] == n]
                if len(found) != 1:
                    print("ERROR: %d subtitles numbered %d" % (len(found), n), file=sys.stderr)
                    return 1
                ranges.append((found[0]["start"], found[0]["end"]))
    except ValueError as e:
        print("ERROR: " + str(e), file=sys.stderr)
        return 2

    os.makedirs(out_dir, exist_ok=True)
    status = 0
    for n, (start, end) in enumerate(ranges, 1):
        start = max(0, start - args.pad_ms)
        end = end + args.pad_ms
        if end <= start:
            print("ERROR: empty range %s - %s" % (fmt(start), fmt(end)), file=sys.stderr)
            status = 1
            continue
        out = os.path.join(out_dir, "%s.%s_%s.wav" % (base, fmt(start, ".").replace(":", "-"), fmt(end, ".").replace(":", "-")))
        cmd = [args.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-ss", "%.3f" % (start / 1000.0), "-t", "%.3f" % ((end - start) / 1000.0), "-i", video,
               "-vn", "-ac", str(args.channels), "-ar", str(args.rate), "-c:a", "pcm_s16le", out]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            print("ERROR: ffmpeg not found (%s). Install it or use --ffmpeg PATH." % args.ffmpeg, file=sys.stderr)
            return 2
        if r.returncode != 0:
            print("ERROR: ffmpeg failed for %s - %s: %s" % (fmt(start), fmt(end), r.stderr.strip()), file=sys.stderr)
            status = 1
            continue
        print("%d. %s  (%s --> %s, %.2fs)" % (n, out, fmt(start), fmt(end), (end - start) / 1000.0))
    return status


if __name__ == "__main__":
    sys.exit(main())
