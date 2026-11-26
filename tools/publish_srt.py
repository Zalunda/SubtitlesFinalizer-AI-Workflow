#!/usr/bin/env python3
"""
publish_srt.py - put the FINAL subtitles of a scene where they are used, and prepare the release for the web site.

    python tools/publish_srt.py <SCENE> [--dry-run] [--release] [--include-different] [--release-dir DIR] [--no-asig] [--title "Short title"]

<SCENE> is the scene folder name (3DSVR-1702, SIVR-130...) or its path (Scenes/SIVR-130). The tool starts from the final
files of the scene folder (the plain <base>.srt made by finalize_srt.py from each <base>.WIP.srt).

1. Default = DO IT (every old file is backed up first) and print the list of files that changed. --dry-run = only show.
   For each part, the final .srt goes next to EVERY copy of the video found in the VideoFolders of
   extract_audio[.private].config.json (searched in order, each recursively; exact name, then a name starting with
   <scene>-<part>). The FIRST copy found is the reference: any other copy whose size in bytes differs is a different
   version of the video (other duration?): its .srt is NOT touched, and the tool lists it so you can decide
   (--include-different to add the subtitles to those versions too).
   Before overwriting, the old .srt is copied to  <name>.srt.BACKUP-<yyyymmdd-HHMMSS>  (the extension is not .srt so a
   player never loads it; search for BACKUP to clean up). The copy is verified (same bytes), the old file is restored if
   it fails, nothing is ever deleted.
2. --release: also copies the .srt and the .asig (next to the first copy of the video) into the release folder
   (ReleaseFolder of publish[.private].config.json, "Release" in the repo by default (git-ignored), or --release-dir),
   renamed with ReleaseNameNoTitle / ReleaseNameWithTitle ("{scene}-{part}" / "{scene}-{part} - {title}"), same BACKUP
   rule. (The forum text is not made by this tool: see WORKFLOW.md, "Prepare the batch".)

Per-scene information (optional): the `## Scene name` section of Scenes/<SCENE>/REVIEW.md (lines `Actors:` and `Title:`),
or Scenes/<SCENE>/RELEASE.json (wins)
    { "Title": "Demon Possession", "Actors": "Mizuki Yayoi, Erika Ozaki, Hikaru Miyanishi",
      "Scripter": "chubbybogs", "ScriptType": "paid", "TopicUrl": "https://discuss.eroscripts.com/t/..." }
Missing values are taken from the video file name ("<SCENE>-<PART> - <Actors> - <Title> [<scripter>].mp4") when possible.
--title overrides Title for this run.

Only the Python standard library is needed.
"""
import argparse
import datetime
import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TIMING = re.compile(r"\d\d:\d\d:\d\d[,.]\d\d\d\s*-->\s*\d\d:\d\d:\d\d[,.]\d\d\d")
PART_RE = re.compile(r"^\S*?\d+[ _-]([A-Z](?:-[A-Z])?)(?=[ .\[]|$)")
PART_NUM_RE = re.compile(r"^\S*?\d+[-_]([A-Z]?\d{1,2})(?=[ .\[]|$)")   # MNSVR-001-2, VRKM-0809-R1, IPVR-380_2
PART_BRACKET_RE = re.compile(r"\[([A-Z])\]")                   # SSIS-698 - ... [D]


def funscript_has_signature(video_base):
    """True when '<video>.funscript' already holds the audio signature (then no .asig is needed)."""
    fs = video_base + ".funscript"
    if not os.path.isfile(fs):
        return False
    with open(fs, "r", encoding="utf-8-sig", errors="replace") as f:
        return '"audioSignature"' in f.read()


def release_part(name):
    """Part token for the release file name ('A', 'A-B', '2', 'D'), or None for a single file with no part."""
    m = PART_RE.match(name) or PART_NUM_RE.match(name) or PART_BRACKET_RE.search(name)
    return m.group(1) if m else None
DEFAULTS = {
    "ReleaseFolder": "Release",   # relative = inside the repo (git-ignored); the user copies from there to the web-site folder
    "ReleaseNameNoTitle": "{scene}-{part}",
    "ReleaseNameWithTitle": "{scene}-{part} - {title}",
    "BackupTag": "BACKUP",
    "ProcessUrl": "https://discuss.eroscripts.com/t/how-to-create-subtitles-for-a-scene-2026/346926",
    "SyncUrl": "https://discuss.eroscripts.com/t/vrnoobies-jav-scripts-on-slr/180121/2",
    "ScriptType": "paid",
}


def load_extract_audio():
    spec = importlib.util.spec_from_file_location("extract_audio", os.path.join(HERE, "extract_audio.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_publish_config():
    cfg = dict(DEFAULTS)
    for name in ("publish.config.json", "publish.private.config.json"):   # the private one wins
        p = os.path.join(ROOT, name)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    cfg.update(json.load(f))
            except (OSError, ValueError) as e:
                print("WARNING: bad config %s: %s" % (p, e), file=sys.stderr)
    return cfg


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def count_cues(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return sum(1 for line in f if TIMING.search(line))


def kb(path):
    return "%.1f KB" % (os.path.getsize(path) / 1024.0)


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def info_from_video_name(video_path):
    """(actors, title, scripter) from '<SCENE>-<PART> - <Actors> - <Title> [<scripter>][AI].mp4' when possible."""
    name = os.path.splitext(os.path.basename(video_path))[0]
    tags = re.findall(r"\[([^\]]+)\]", name)
    name = re.sub(r"\s*\[[^\]]*\]", "", name).strip()
    segs = [s.strip() for s in name.split(" - ")]
    actors = title = scripter = ""
    if len(segs) >= 3:
        actors, title = segs[1], " - ".join(segs[2:])
    elif len(segs) == 2:
        actors = segs[1]
    if tags:
        scripter = tags[0]
    return actors, title, scripter


_INDEX = {}


def find_all_videos(folders, video_name, scene, part):
    """ALL the copies of the video, in the search order of VideoFolders (each folder searched recursively, listed once).
    A copy = the file named video_name, or an .mp4 starting with '<scene>-<part>' + space/dash/dot (renamed video).
    A '*.FAST.mp4' (low-quality working proxy) is never a copy: ignored."""
    wanted = video_name.lower()
    prefixes = {("%s-%s" % (scene, part)).lower()}
    # a numbered part (TMAVR-269_2) is often renamed with its letter (TMAVR-269-B - ...): 1->A, 2->B...
    num = release_part(os.path.splitext(video_name)[0])
    if num and num.isdigit() and 1 <= int(num) <= 26:
        prefixes.add(("%s-%s" % (scene, chr(64 + int(num)))).lower())
    # the folder name may differ from the video's id (3DSVR-647 vs 3DSVR-0647): also use the id taken from the file name
    m = re.match(r"^(\S*?\d+[ -]%s)(?=[ .\[]|$)" % re.escape(part), video_name)
    if m:
        prefixes.add(m.group(1).lower())
    out, seen = [], set()
    for root in folders:
        root = root.strip().strip('"')
        if not os.path.isdir(root):
            continue
        if root not in _INDEX:
            _INDEX[root] = [os.path.join(d, n) for d, _s, fs in os.walk(root) for n in fs if n.lower().endswith(".mp4")]
        for path in _INDEX[root]:
            low = os.path.basename(path).lower()
            if low.endswith(".fast.mp4"):
                continue  # a low-quality working proxy (<name>.FAST.mp4), never a real copy of the video
            ok = low == wanted or any(low.startswith(pf) and low[len(pf):len(pf) + 1] in (" ", "-", ".") for pf in prefixes)
            key = os.path.normcase(os.path.abspath(path))
            if ok and key not in seen:
                seen.add(key)
                out.append(path)
    return out


def backup_then_copy(src, dst, tag, apply_it, log):
    """Copy src over dst (a BACKUP of the old dst is made first). Returns True if the copy was (or would be) done."""
    if os.path.isfile(dst):
        if sha(src) == sha(dst):
            log("    up to date: %s" % dst)
            return False
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = "%s.%s-%s" % (dst, tag, stamp)
        if not apply_it:
            log("    would back up the old file to: %s" % os.path.basename(backup))
            log("    would overwrite: %s" % dst)
            return True
        shutil.copy2(dst, backup)
        try:
            shutil.copyfile(src, dst)
            if sha(src) != sha(dst):
                raise OSError("verification failed")
        except OSError as e:
            shutil.copyfile(backup, dst)
            log("    ERROR (%s): the old file was restored: %s" % (e, dst))
            return False
        log("    done (old file saved as %s): %s" % (os.path.basename(backup), dst))
        return True
    if not apply_it:
        log("    would create: %s" % dst)
        return True
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    log("    created: %s" % dst)
    return True


def main():
    ap = argparse.ArgumentParser(description="Publish the final subtitles of a scene (real folder + release folder).")
    ap.add_argument("scene", help="scene folder name (SIVR-130) or path (Scenes/SIVR-130)")
    ap.add_argument("--dry-run", action="store_true", help="only show what would be done (default: do it, with BACKUPs)")
    ap.add_argument("--include-different", action="store_true", help="also update the copies of the video whose size differs from the first copy")
    ap.add_argument("--release", action="store_true", help="prepare the release folder (.srt + .asig)")
    ap.add_argument("--release-dir", help="release folder (default: ReleaseFolder of publish[.private].config.json)")
    ap.add_argument("--no-asig", action="store_true", help="don't copy the .asig files into the release folder")
    ap.add_argument("--title", help="short title of the scene for the release file names (overrides RELEASE.json)")
    args = ap.parse_args()
    apply_it = not args.dry_run
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folder = args.scene if os.path.isdir(args.scene) else os.path.join(ROOT, "Scenes", args.scene)
    if not os.path.isdir(folder):
        print("ERROR: scene folder not found: " + args.scene, file=sys.stderr)
        return 2
    scene = os.path.basename(os.path.abspath(folder))
    ea = load_extract_audio()
    pcfg = load_publish_config()
    rel = {}
    rp = os.path.join(folder, "RELEASE.json")
    if os.path.isfile(rp):
        with open(rp, "r", encoding="utf-8-sig") as f:
            rel = json.load(f)

    rv = os.path.join(folder, "REVIEW.md")   # '## Scene name' section: lines 'Actors: ...' / 'Title: ...' (RELEASE.json wins)
    if os.path.isfile(rv):
        txt = open(rv, "r", encoding="utf-8-sig").read()
        m = re.search(r"^## Scene name[^\n]*\n(.*?)(?=^## |\Z)", txt, re.M | re.S)
        if m:
            for key in ("Actors", "Title"):
                mm = re.search(r"^%s:[ 	]*(.+?)[ 	]*$" % key, m.group(1), re.M)
                if mm and "TODO" not in mm.group(1) and key not in rel:
                    rel[key] = mm.group(1)

    wips = sorted(glob.glob(os.path.join(folder, "*.WIP.srt")))
    if not wips:
        print("ERROR: no .WIP.srt in " + folder, file=sys.stderr)
        return 2

    print("Scene %s: %d part(s)%s" % (scene, len(wips), "" if apply_it else "  [DRY RUN: nothing is written]"))
    problems = 0
    no_scene_asig = []   # parts with no <base>.asig in the scene folder (warning only)
    parts = []   # (part label, final, [(video, real_srt, asig), ...])
    for wip in wips:
        base = wip[: -len(".WIP.srt")]
        final = base + ".srt"
        name = os.path.basename(base)
        m = PART_RE.match(name)
        part = m.group(1) if m else name
        print("\n== part %s: %s" % (part, os.path.basename(final)))
        if not os.path.isfile(final):
            print("   ERROR: no final .srt (run finalize_srt.py first)")
            problems += 1
            continue
        with open(wip, "r", encoding="utf-8-sig", errors="replace") as f:
            if "------- Metadatas -------" in f.read():
                print("   ERROR: the WIP still has metadata: not finalized")
                problems += 1
                continue
        if os.path.getmtime(final) + 1 < os.path.getmtime(wip):
            print("   WARNING: the WIP is newer than the final .srt: run finalize_srt.py again")
            problems += 1
        print("   final: %d cues, %s" % (count_cues(final), kb(final)))
        scene_asig = base + ".asig"   # the audio signature of the video the timings were made on, kept in the scene folder
        if os.path.isfile(scene_asig):
            print("   scene .asig: %s, %s" % (os.path.basename(scene_asig), kb(scene_asig)))
        else:
            print("   WARNING: no %s in the scene folder (copy it from the toolbox work folder)" % os.path.basename(scene_asig))
            no_scene_asig.append(part)
        cfg = ea.load_config(final)
        videos = find_all_videos(cfg["VideoFolders"], name + ".mp4", scene, part)
        if not videos:
            print("   real folder: no video found (add its folder to VideoFolders of extract_audio.private.config.json)")
            parts.append((part, final, []))
            continue
        entries = []
        print("   %d copy(ies) of the video found (search order of VideoFolders):" % len(videos))
        for i, video in enumerate(videos, 1):
            base_v = os.path.splitext(video)[0]
            real = base_v + ".srt"
            asig = base_v + ".asig"
            asig = asig if os.path.isfile(asig) else None
            print("   [%d] video: %s  (%s)" % (i, video, "asig " + kb(asig) if asig
                                              else "no .asig, signature in the .funscript: not needed" if funscript_has_signature(base_v)
                                              else "NO .asig"))
            if not os.path.isfile(real):
                print("       real .srt: none yet -> would be created")
            elif sha(real) == sha(final):
                print("       real .srt: up to date (same bytes)")
            else:
                newer = "NEWER than the final file (edited since?)" if os.path.getmtime(real) > os.path.getmtime(final) else "older than the final file"
                print("       real .srt: DIFFERENT: %d cues, %s, %s" % (count_cues(real), kb(real), newer))
            same = os.path.getsize(video) == os.path.getsize(videos[0])
            if not same:
                print("       DIFFERENT VIDEO SIZE: %d bytes (first copy: %d)" % (os.path.getsize(video), os.path.getsize(videos[0])))
            entries.append((video, real, asig, same or args.include_different))
        parts.append((part, final, entries))

    if problems:
        print("\n%d problem(s) above: fix them first (nothing is written)." % problems)
        if apply_it or args.release:
            return 1

    changed, skipped, unchanged = [], [], []
    print("\n== " + ("REAL FOLDERS" if apply_it else "REAL FOLDERS (dry run)"))
    for part, final, entries in parts:
        if not entries:
            print("  part %s: no video found" % part)
            continue
        for video, real, asig, ok in entries:
            if not ok:
                skipped.append((part, real))
                continue
            if backup_then_copy(final, real, pcfg["BackupTag"], apply_it, lambda m: None):
                changed.append((part, real))
            else:
                unchanged.append((part, real))
    print("%s (%d):" % ("Files changed" if apply_it else "Files that would change", len(changed)))
    for part, real in changed:
        print("  [%s] %s" % (part, real))
    print("Already up to date: %d" % len(unchanged))
    if no_scene_asig:
        print("\nWARNING: no .asig in the scene folder for part(s) %s: copy the .asig of the toolbox work folder "
              "next to the .WIP.srt as <base>.asig" % ", ".join(no_scene_asig))
    if skipped:
        print("\nNOT CHANGED, the video file has a different size than the first copy (%d). Add the subtitles to those versions?" % len(skipped))
        for part, real in skipped:
            print("  [%s] %s" % (part, real))
        print("(to say yes, ask the assistant: it runs the tool again with --include-different)")
        if apply_it:   # the single channel with the user: the question goes in the scene's REVIEW.md
            rv = os.path.join(folder, "REVIEW.md")
            old = open(rv, "r", encoding="utf-8-sig").read() if os.path.isfile(rv) else ""
            add = [("- [ ] %s | %s | video size differs from the first copy" % (part, real)) for part, real in skipped
                   if real not in old]
            if add:
                head = "" if "## Publish questions" in old else "\n## Publish questions (subtitles NOT copied: the video file has a different size than the first copy; write `Answer: yes` or `no` on the line)\n\n"
                with open(rv, "a", encoding="utf-8", newline="\n") as f:
                    f.write(("" if old.endswith("\n") or not old else "\n") + head + "\n".join(add) + "\n")
                print("(also written in %s)" % rv)

    if args.release:
        rdir = args.release_dir or pcfg["ReleaseFolder"]
        if not os.path.isabs(rdir):
            rdir = os.path.join(ROOT, rdir)
        actors = rel.get("Actors", "")
        title = args.title or rel.get("Title", "")
        scripter = rel.get("Scripter", "")
        for part, final, entries in parts:
            if entries:
                video = entries[0][0]
                a, t, s = info_from_video_name(video)
                actors = actors or a
                scripter = scripter or s
                if not title and not args.title and rel.get("UseVideoTitle", False):
                    title = t
        print("\n== RELEASE folder: %s  (title: %s)" % (rdir, title or "-"))
        for part, final, entries in parts:
            asig = entries[0][2] if entries else None   # the first copy in search order
            if not asig and os.path.isfile(final[: -len(".srt")] + ".asig"):
                asig = final[: -len(".srt")] + ".asig"   # no .asig next to the video: use the one kept in the scene folder
            pattern = pcfg["ReleaseNameWithTitle"] if args.title else pcfg["ReleaseNameNoTitle"]
            rpart = release_part(os.path.basename(final)[: -len(".srt")])
            if rpart is None:   # a single file with no part token: "<scene>.srt", not "<scene>-<whole file name>.srt"
                pattern = pattern.replace("-{part}", "")
            rname = safe_name(pattern.format(scene=scene, part=rpart or "", title=args.title or "", actors=actors))
            print("  part %s -> %s.srt" % (part, rname))
            dst = os.path.join(rdir, rname + ".srt")
            backup_then_copy(final, dst, pcfg["BackupTag"], apply_it, print)
            if not asig and not args.no_asig:
                if entries and funscript_has_signature(os.path.splitext(entries[0][0])[0]):
                    print("  part %s: no .asig, but the .funscript has the audio signature: no .asig needed" % part)
                else:
                    print("  part %s: WARNING no .asig found" % part)
            if asig and not args.no_asig:
                print("  part %s -> %s.asig" % (part, rname))
                backup_then_copy(asig, os.path.join(rdir, rname + ".asig"), pcfg["BackupTag"], apply_it, print)
    return 0


if __name__ == "__main__":
    sys.exit(main())
