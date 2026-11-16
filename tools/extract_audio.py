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
    --pad-ms N       add N ms of context before and after (default: config PadMs, 0 = exactly the subtitle's timing)
    --video FILE     the video (default: <srt base name>.mp4 next to the .srt; if it is not there, the folders listed in
                     VideoFolders of the config are searched, see above)
    --out-dir DIR    where to write (default: a 'clips' folder next to the .srt)
    --rate HZ        sample rate (default 16000)
    --channels N     1 = mono (default), 2 = stereo
    --ffmpeg PATH    ffmpeg executable (default: 'ffmpeg' from the PATH)

Settings (extract_audio.config.json, same idea as finalize.config.json; extract_audio.private.config.json = same format,
for machine-specific values like your video folders, never committed): "VideoFolders" (list of folders searched recursively for the
video when it is not next to the .srt), "SampleRate", "Channels", "PadMs", "Ffmpeg". The tool reads every extract_audio[.private].config.json
found from the .srt's folder up to the filesystem root, plus the one at the repo root; the nearest file wins for the single values and
the "VideoFolders" lists are added together. So the repo-root extract_audio.config.json (public) holds the defaults and an empty VideoFolders, and your
private extract_audio.private.config.json (also at the repo root, git-ignored) holds the real folders. Command-line options override the config.
Video not next to the .srt: the tool looks for <srt base name>.mp4 (same name, without ".WIP") in the VideoFolders.

Each line printed is numbered in the order of the arguments: the transcriber AI does not see file names, so send the clips in
that order and give the user the numbered table with the durations.

Output file name:  <base>.<start>-<end>.wav   e.g.  HNVR-141-C.00-21-03.897_00-21-06.204.wav

Only the Python standard library and ffmpeg are needed.
"""
import argparse
import json
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


CONFIG_NAMES = ["extract_audio.private.config.json", "extract_audio.config.json"]   # in a same folder, the .private one wins
DEFAULTS = {"VideoFolders": [], "SampleRate": 16000, "Channels": 1, "PadMs": 0, "Ffmpeg": "ffmpeg"}


def load_config(srt_path):
    """Merge every extract_audio[.private].config.json from the .srt's folder up to the filesystem root, plus the repo root
    (parent of tools/). Nearest wins for single values; VideoFolders are concatenated (nearest first)."""
    paths = []
    folder = os.path.dirname(os.path.abspath(srt_path))
    while True:
        for name in CONFIG_NAMES:
            cand = os.path.join(folder, name)
            if os.path.isfile(cand):
                paths.append(cand)
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in CONFIG_NAMES:
        repo_cfg = os.path.join(repo_root, name)
        if os.path.isfile(repo_cfg) and repo_cfg not in paths:
            paths.append(repo_cfg)
    cfg = dict(DEFAULTS)
    cfg["VideoFolders"] = []
    seen_scalar = set()
    for p in paths:   # nearest first
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            print("WARNING: bad config %s: %s" % (p, e), file=sys.stderr)
            continue
        for key, value in data.items():
            if key == "VideoFolders":
                cfg["VideoFolders"] += [v for v in value if v not in cfg["VideoFolders"]]
            elif key not in seen_scalar:
                cfg[key] = value
                seen_scalar.add(key)
    return cfg


def find_video_in_folders(folders, video_name):
    """Search each folder recursively for a file named video_name (case-insensitive); first match wins."""
    wanted = video_name.lower()
    for root in folders:
        root = root.strip().strip('"')
        if not os.path.isdir(root):
            print("note: VideoFolders entry not found: %s" % root, file=sys.stderr)
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if name.lower() == wanted:
                    return os.path.join(dirpath, name)
    return None


def main():
    ap = argparse.ArgumentParser(description="Extract the audio of subtitles into .wav files (ffmpeg).")
    ap.add_argument("source", help="the working .srt (or a video, with --range)")
    ap.add_argument("--at", action="append", default=[], metavar="TIME")
    ap.add_argument("--cue", action="append", default=[], type=int, metavar="N")
    ap.add_argument("--range", action="append", default=[], nargs=2, metavar=("START", "END"))
    ap.add_argument("--pad-ms", type=int, default=None)
    ap.add_argument("--video")
    ap.add_argument("--out-dir")
    ap.add_argument("--rate", type=int, default=None)
    ap.add_argument("--channels", type=int, default=None, choices=[1, 2])
    ap.add_argument("--ffmpeg", default=None)
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
    cfg = load_config(args.source)
    if args.pad_ms is None:
        args.pad_ms = int(cfg["PadMs"])
    if args.rate is None:
        args.rate = int(cfg["SampleRate"])
    if args.channels is None:
        args.channels = int(cfg["Channels"])
    if args.ffmpeg is None:
        args.ffmpeg = cfg["Ffmpeg"]
    if not os.path.isfile(video) and not args.video and is_srt:
        found = find_video_in_folders(cfg["VideoFolders"], os.path.basename(video))
        if found:
            print("video found through VideoFolders of the config: " + found)
            video = found
    if not os.path.isfile(video):
        print("ERROR: video not found: %s (use --video, or add its folder to VideoFolders in an extract_audio.private.config.json, e.g. extract_audio.private.config.json at the repo root)" % video, file=sys.stderr)
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
