#!/usr/bin/env python3
"""
lint_srt.py - READ-ONLY style check of finalized subtitles, driven by a config file the user can edit.

It flags, per cue: words/phrases the style guide forbids or discourages (regex rules), and numeric limits on the
real timing (line length, number of lines, reading speed, orphan last word). It never modifies anything.

Config: lint.config.json (rules + limits + repeats, see its "_help"; "repeats" flags a word used in too many cues close together). Looked up in this order:
    --config FILE  >  <folder of the .srt>/lint.config.json  >  <repo root>/lint.config.json
False positives: <folder of the .srt>/lint.ignore.txt (or --ignore FILE), one line per case:
    <rule-id> <HH:MM:SS>        e.g.   he-him-cock 00:12:34     (matches the cue start by prefix; '#' = comment)
    <rule-id> *                 switches the rule off for the whole scene (e.g. 'he-him-cock *' when real people are talked about)

Usage:
    python tools/lint_srt.py <file.WIP.srt | file.srt> [...] [--min-severity info|warn|error]
                             [--rule ID] [--strict] [--summary] [--config FILE] [--ignore FILE]
    --strict   exit code 1 if any 'error' is found (default: always 0)
    --summary  only the count per rule
    --rule ID  only this rule (or limit name)

Cues that still have a metadata block (not finalized) are skipped (their text is not final).
Only the Python standard library is needed.
"""
import argparse
import json
import os
import re
import sys

TS = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
CUE_HEAD = re.compile(r"^(﻿?)(\d+)[ \t]*\r?\n" + TS + r" --> " + TS + r"[ \t]*\r?\n", re.MULTILINE)
HEADER = "------- Metadatas -------"
SEVERITIES = {"info": 0, "warn": 1, "error": 2}


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def fmt(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def parse(text):
    heads = list(CUE_HEAD.finditer(text))
    cues = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end].strip("\r\n \t")
        cues.append({"number": int(m.group(2)), "start": to_ms(*m.groups()[2:6]), "end": to_ms(*m.groups()[6:10]),
                     "lines": [l.rstrip("\r") for l in body.split("\n")] if body else [], "pending": body.startswith(HEADER)})
    return cues


def find_file(explicit, srt_path, name):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    folder = os.path.dirname(os.path.abspath(srt_path))
    for c in (os.path.join(folder, name), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), name)):
        if os.path.isfile(c):
            return c
    return None


def load_ignore(path):
    result = []
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        result.append((parts[0], parts[1]))
    return result


def main():
    ap = argparse.ArgumentParser(description="Read-only style check of finalized subtitles.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--config")
    ap.add_argument("--ignore")
    ap.add_argument("--min-severity", choices=list(SEVERITIES), default="info")
    ap.add_argument("--rule")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    errors_found = 0
    for path in args.files:
        if not os.path.isfile(path):
            print("ERROR: not found: " + path, file=sys.stderr)
            return 2
        cfg_path = find_file(args.config, path, "lint.config.json")
        if not cfg_path:
            print("ERROR: lint.config.json not found (give --config)", file=sys.stderr)
            return 2
        try:
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            rules = []
            for r in cfg.get("rules", []):
                if r.get("enabled", True) is False:
                    continue
                flags = 0
                for ch in r.get("flags", "i"):
                    flags |= {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}.get(ch, 0)
                rules.append((r["id"], r.get("severity", "warn"), re.compile(r["pattern"], flags), r.get("message", "")))
            limits = {k: v for k, v in cfg.get("limits", {}).items() if v.get("enabled", True) is not False}
            skip = re.compile(cfg["ignore_cue_text"]) if cfg.get("ignore_cue_text") else None
            repeats = []
            for r in cfg.get("repeats", []):
                if r.get("enabled", True) is False:
                    continue
                flags = re.IGNORECASE if "i" in r.get("flags", "i") else 0
                repeats.append((r["id"], r.get("severity", "info"), re.compile(r["pattern"], flags),
                                int(r.get("window", 6)), int(r.get("max", 3)), r.get("message", "repeated word")))
        except (KeyError, ValueError, re.error) as e:
            print("ERROR: bad config %s: %s" % (cfg_path, e), file=sys.stderr)
            return 2
        ignore = load_ignore(find_file(args.ignore, path, "lint.ignore.txt"))

        with open(path, "r", encoding="utf-8", newline="") as f:
            cues = parse(f.read())
        label = os.path.basename(path)
        findings = []   # (severity, rule, cue, message)
        pending = 0
        for c in cues:
            if c["pending"]:
                pending += 1
                continue
            text = "\n".join(c["lines"])
            if skip and skip.search(text):
                continue
            dur = (c["end"] - c["start"]) / 1000.0
            for rid, sev, rx, msg in rules:
                if rx.search(text):
                    findings.append((sev, rid, c, msg))
            lim = limits.get("max_line_length")
            if lim and any(len(l) > lim["value"] for l in c["lines"]):
                findings.append((lim["severity"], "max_line_length", c, lim["message"]))
            lim = limits.get("max_lines")
            if lim and len(c["lines"]) > lim["value"]:
                findings.append((lim["severity"], "max_lines", c, lim["message"]))
            chars = len(" ".join(c["lines"]))
            for name in ("max_cps", "target_cps"):
                lim = limits.get(name)
                if lim and dur > 0 and chars / dur > lim["value"]:
                    findings.append((lim["severity"], name, c, "%s (%.1f cps)" % (lim["message"], chars / dur)))
            lim = limits.get("orphan_last_line")
            if lim and len(c["lines"]) == 2 and len(c["lines"][1].split()) <= lim["value"]:
                findings.append((lim["severity"], "orphan_last_line", c, lim["message"]))

        # repeated words in cues close to each other (e.g. 'cum' 3 times in 6 cues): the cue that reaches the limit is flagged
        done = [c for c in cues if not c["pending"] and not (skip and skip.search("\n".join(c["lines"])))]
        for rid, sev, rx, window, maximum, msg in repeats:
            hits = [1 if rx.search("\n".join(c["lines"])) else 0 for c in done]
            for i, c in enumerate(done):
                if hits[i] and sum(hits[max(0, i - window + 1):i + 1]) >= maximum:
                    findings.append((sev, rid, c, "%s (%d of the last %d cues)" % (msg, sum(hits[max(0, i - window + 1):i + 1]), window)))

        kept = []
        for sev, rid, c, msg in findings:
            if SEVERITIES[sev] < SEVERITIES[args.min_severity]:
                continue
            if args.rule and rid != args.rule:
                continue
            t = fmt(c["start"])
            if any(ir == rid and (it == "*" or t.startswith(it)) for ir, it in ignore):
                continue
            kept.append((sev, rid, c, msg))

        print("== %s (%s): %d cues, %d findings%s" % (label, os.path.basename(cfg_path), len(cues), len(kept),
                                                         ", %d cues skipped (metadata still there)" % pending if pending else ""))
        counts = {}
        for sev, rid, c, msg in kept:
            counts.setdefault((rid, sev), 0)
            counts[(rid, sev)] += 1
            if sev == "error":
                errors_found += 1
        if not args.summary:
            for sev, rid, c, msg in sorted(kept, key=lambda x: (x[2]["start"], x[1])):
                print("  %-5s %s [%s] %s :: %s" % (sev.upper(), fmt(c["start"])[:8], rid, msg, " / ".join(c["lines"])))
        for (rid, sev), n in sorted(counts.items(), key=lambda kv: (-SEVERITIES[kv[0][1]], -kv[1])):
            print("  summary: %-5s %-18s %d" % (sev, rid, n))
    return 1 if (args.strict and errors_found) else 0


if __name__ == "__main__":
    sys.exit(main())
