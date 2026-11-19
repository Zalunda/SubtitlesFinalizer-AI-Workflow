# SubtitlesFinalizer - Agent Working Guidelines

This folder is where the user and an AI assistant put the **finishing touch** on subtitle files (`.srt`) that were produced by an automatic AI transcription/translation process (Japanese adult VR videos translated to English). You don't need to know how that process works: everything you need is described in this folder.

The AI output is good but not final. Your job is to be the last editor:

1. **Fix / improve the translation** (natural, punchy, spoken English; fix mishearings and context errors).
2. **Split lines at the right spot** (at real speech pauses, not mid-phrase).
3. **Split or merge subtitles** when it makes sense (readability, reading speed, speaker changes).
4. **Ask the user** when the transcription / analysis is suspicious and only the video can tell.

Read these before working on a scene:
* [WORKFLOW.md](WORKFLOW.md): the exact step-by-step process, the file conventions, the "waves".
* [STYLE-GUIDE.md](STYLE-GUIDE.md): the translation and subtitle style rules (register, splitting, timing, vocabulary).

---

## 1. Folder Layout

```text
SubtitlesFinalizer/
├── AGENTS.md / CLAUDE.md / WORKFLOW.md / STYLE-GUIDE.md
├── tools/                                          helper scripts (see section 6)
├── Release/                                        git-ignored: files prepared by tools/publish_srt.py --release in one folder per batch, Release/<date>/ (<scene>-<part>.srt/.asig + CHANGES-<date>.txt for the forum, which includes the text of Release/POST-TEXT.txt)
└── Scenes/
    ├── --RELEASED/<date>/<SCENE-ID>/              scenes already released, moved there by batch (WORKFLOW.md, "Prepare the batch")
    └── <SCENE-ID>/                                 e.g. Scenes/HNVR-141/
        ├── <SCENE>-<P>.final-ai-debug.srt          INPUT  (read-only, source of truth)
        ├── <SCENE>-<P>.Worker.manual-input-preparer.TERRAIN-MAP.srt   INPUT (read-only audio terrain, see 2.2). OPTIONAL: without it, no silence is assumed anywhere
        ├── <SCENE>-<P>.WIP.srt                     WORK IN PROGRESS (the only file you edit), created by tools/create_working_srt.py
        │                                             from the two inputs above
        ├── <SCENE>-<P>.srt                         FINAL file (plain name), produced at the very end by tools/finalize_srt.py from the .WIP.srt
        ├── REVIEW.md                               (starts with the `## Progress checklist` of the scene: see WORKFLOW.md, "The scene checklist"; read it first when resuming) THE single channel with the user for the WHOLE scene (all its parts in one file): cues finalized with a doubt (R: notes of apply_cues, tagged with the part letter), clip tables (with a context for the transcriber), open questions with an `Answer:` line, scene-wide notes, a `## Scene name` section (`Actors:` / `Title:`, used for the release), `## Publish questions` (copies of a video not updated because its size differs). In chat, only say "created/updated REVIEW.md" + counts (see WORKFLOW.md)
        ├── GLOSSARY.md                             Scene glossary + character notes (created after the pilot batch, see WORKFLOW.md)
        └── <SCENE>-<P>.mp4                         Optional video, for the user only (git-ignored; never read it)
```
`<P>` is the part letter (`A`, `B`, `C`...): a scene can have several parts, each with its own set of files. Treat each part independently.

---

## 2. The Input Files

### 2.1 `*.final-ai-debug.srt` (subtitles + metadata)
A normal SRT, except each cue has a `------- Metadatas -------` block after the timing line. Each metadata line looks like `[source] {Key:Value}` (values can span several lines until the closing `}`).

| Source / Key | Meaning |
| :--- | :--- |
| `[full-ai] {VoiceText}` | Japanese heard by the first, full-audio AI transcription pass. |
| `[singlevad-ai-refined] {VoiceText}` | Japanese heard when the AI re-listened to *just this clip* (with images). The text the translation is based on. |
| `[singlevad-ai-refined] {TranslatedText}` | The English translation = the cue text in the final subtitle. |
| `[singlevad-ai-refined] {TranslationAnalysis}` | AI description of the clip: `Vector:` (who she talks to / pronoun rule), `State:` (mood + Tier 1-3 arousal), `Cadence:` (number of spoken parts), then a visual/vocal analysis. May start with `Gap Summary:` (what happened since the previous clip). |
| `[singlevad-ai-refined] {Speaker}` | Speaker when it matters (multi-speaker scenes). |
| `[manual-input] {...}` | Human-provided input: `OngoingContext` (scene premise, tone instructions), `OngoingSpeakers`, `Speaker`, or a manual `VoiceText`. **These are the user's instructions: always obey them.** |

**Any metadata whose key starts with `Ongoing` (`OngoingContext`, `OngoingSpeakers`...) applies to EVERY following cue** until a later cue overrides it with a new metadata of the same name. It is usually written only once, on the first cue that needs it. **All the parts (A, B, C...) of a scene folder are ONE long scene as far as metadata is concerned**: an `Ongoing*` set in part A still applies in parts B and C (confirmed by the user), until overridden. (Other rules, like "treat each part independently" for the working files, still hold.)

**How the files are produced (why the signals can disagree):**
1. `[full-ai] VoiceText` = the first transcription, done on the **whole audio file**.
2. An automated process then adjusts the subtitle timings; the user can also change timings, merge or split subtitles.
3. `[singlevad-ai-refined]` receives only the **audio clip of each subtitle as it is after those changes** and transcribes/translates again.
   * The user may have "messed up" a timing, so the clip can **miss words** (cut off at the start/end) or contain **the neighbour's words**. The `[full-ai]` text can then be used to **complete a sentence** whose missing words aren't in the next subtitle.
   * Often `[full-ai]` simply **repeats the previous or next subtitle's text** (the whole-file pass lined up differently). In that case follow `[singlevad-ai-refined]`.
   * Both are AI guesses; the real arbiter is the user's ears (questions file).

How to read the signals:
* `[full-ai]` vs `[singlevad-ai-refined]` **VoiceText disagreeing** = a suspicious transcription. Investigate, and ask the user if you can't resolve it from context.
* A `TranslationAnalysis` is the AI's *interpretation*, not ground truth. When the AI mishears a word, its analysis usually invents a story that justifies the mishearing. Never treat it as proof the translation is right.
* The cue text in the debug file is **not shown** in the metadata block; the translation is in `{TranslatedText}`.

### 2.2 `*.TERRAIN-MAP.srt` and the `[terrain] {Silences}` line (audio: where speech is possible)
The audio of the scene was analyzed. The result is `<S>-<P>.Worker.manual-input-preparer.TERRAIN-MAP.srt`: every cue is a *piece of sound* (`A`..`Z` cycling letters = **voiced speech**, `~` = **breath / rustle / unvoiced sound**); the gaps between cues are **silence** (no sound above the noise level).

You normally **don't read that file**. `tools/create_working_srt.py` already merged it into the working file: every cue's metadata block has a line

```
[terrain] {Silences:from 00:23:25.234 to 00:23:26.132; from 00:23:27.001 to 00:23:27.350}
```
listing the silences (longer than 100 ms) that **overlap that subtitle**, with their real start and end (a silence can begin before the subtitle or end after it; times are `HH:MM:SS.mmm`). `{Silences:none}` means continuous sound under the subtitle: **don't split it inside**. A silence listed as `from <time> to the end` is after the last sound of the audio.

Use it to decide **where a subtitle can be cut or timed**: a split between two sentences should land in a listed silence; a cue should not extend across a long silence unless the speaker is really still talking; a cue that sits almost entirely inside a silence has no sound under it (trim it). Breaths (`~`) count as sound, so a breath is not listed as silence; open the TERRAIN-MAP.srt only if you need to tell speech from breath around a given time.

**Cutting inside continuous sound (`{Silences:none}`) is allowed only for a really long cue** (too long to read in one go). I can't hear the audio, so I need the user's ears to find the spot:
* Give the user the **romaji** (romanized Japanese, so they can sound it out and match it to what they hear) of the cue's `VoiceText`, with the timestamp, in the questions file (or in chat). Mark the candidate cut point(s) I'm considering with `|`.
* The user listens, picks the spot, and tells me the time of the cut (or confirms mine). I then split there.

**Cutting at a listed silence** is normally my own call, but when the two halves are ambiguous (the VoiceTexts disagree, or I'm not sure which words belong to which side of the pause), ask the user what is said **in each part, in romaji**, before splitting.
The format is deliberately simple and can be improved. If you need other info (levels, voicing...), say so and propose it.

---

## 3. Golden Rules

* **NEVER modify `*.final-ai-debug.srt` or `*.TERRAIN-MAP.srt`.** They are inputs; the user regenerates them.
* **The working file is `<SCENE>-<P>.WIP.srt`** (the plain `<SCENE>-<P>.srt` is the final file, generated from it at the end; never edit it by hand). At the start of a part, create it with `python tools/create_working_srt.py Scenes/<SCENE>` (a copy of the debug file + the `[terrain] {Silences}` line of each cue; don't copy the debug file by hand). **If `<SCENE>-<P>.WIP.srt` already exists, do not overwrite it** (the tool refuses too): continue from it.
* **File formatting:** keep the UTF-8 **BOM**. The files mix CRLF/LF; the user said that is not important while working (the tools keep whatever is there), **but the final file must be Windows CRLF**: `tools/finalize_srt.py` produces it (CRLF + numbering); **the WIP file is never converted or renumbered** (the user diffs it while you work). Don't write other scripts that reformat/re-encode files. **Never use the Edit/Write tools on a `.srt`**: the Edit tool silently rewrites the whole file with a single line ending (verified: it turned the mixed CRLF/LF working file into all-CRLF). Read cues with `tools/view_cues.py` and write decisions with `tools/apply_cues.py` (both below), which only touch the cues they name.
* **Cue numbers do not matter while working.** When you split or merge cues, don't renumber by hand (no wasted tokens): **never renumber the WIP file** (the user diffs it: renumbering ruins the diff); the final file is renumbered by `tools/finalize_srt.py`. Do keep the timing lines valid (`HH:MM:SS,mmm --> HH:MM:SS,mmm`).
* **Never delete a subtitle without the user's own confirmation, in two steps (user rule, NHVR-070).** An empty or "no speech" VoiceText is not proof: the AI may have missed words, and I can't hear the audio. (1) Keep the cue (with a `[finalizer] {Question:...}`) and **only put its clip in the transcriber table** (`extract_audio.py`, include the neighbouring line of the same voice when there is one); **don't ask the user anything yet**. (2) When the transcriber's answer comes back: if it heard words, use them. If it heard nothing (or only an unintelligible murmur), **the transcriber's "nothing" is NOT a confirmation**: list the cue under `Ear checks (you)` in `REVIEW.md` and ask the user to listen. Only after the user confirms that there is no speech do I delete it (`D:` in apply_cues). Same for trimming a cue down to almost nothing.
* **Never invent content.** Only translate what was said. If the meaning is unclear, don't guess silently: flag it (see Workflow wave 2).
* **No silent defaults for missing information.** If a scene has no `OngoingContext` or an unknown speaker, say so and ask; don't assume. **Exception (user decision): the TERRAIN-MAP is optional.** Without it, every cue gets `{Silences:none}` (no silence anywhere) and the tool says so; then no split is possible by the terrain, and any split of a cue goes through the romaji / user-confirmation procedure of 2.2.
* **Obey `[manual-input]` metadata** (`OngoingContext` etc.): it carries the user's creative direction for this scene (e.g. "more about teasing the POV-man").
* **Adult content:** the material is explicit adult video. Translate it faithfully and uncensored, in the tone of the scene; don't sanitize or moralize.
* **Git (two repositories):** the root folder (tools, `.md`, configs: public) and `Scenes/` (the working files: private, its own `git init`, ignored by the root repo through `/Scenes/`) are **two separate git repos**. **NEVER run `git add`** (the user inspects and stages changes manually), and **never commit or push on my own**. Commit only when the user asks ("commit what I staged"), always with this process:
  1. `git status` + `git diff --cached --stat` in the repo(s) concerned (root and/or `Scenes/`: run each command inside its own folder); commit **only what is staged**; if something is unstaged or nothing is staged, say so and don't stage it for the user. **For every scene folder in the staged files of `Scenes/`, check that its `<clean name>.wipsubtitles.zip` is there** (staged or already tracked); if one is missing, say so before the commit.
  2. **Show the user a preview of the commit message first** (short subject line + a few bullets of what changed, in the style of the existing `git log`) and **wait for the go** before committing.
  3. Commit with that message (end it with the attribution footer required by the session, when there is one), then show `git log --oneline -1`. Never `--amend`, `--no-verify` or force options unless the user asks.
  4. **Push only when the user explicitly asks**, and name the repo and its visibility (root = public, `Scenes/` = private) before pushing. Pushing publishes the content. Before a push of the public repo, check that no scene file is tracked (`git ls-files | findstr Scenes` must print nothing) and that no `*.private.config.json` is.
  `.mp4`/audio files and `*.private.config.json` are git-ignored (see the `.gitignore` files).
* **Report faithfully**: if you only finished part of a wave, or a step was skipped, say so.

---

## 4. Finalized vs. Not-Yet-Finalized Cues (the state of the working file)

The working file mixes both kinds of cues, and **the presence of the metadata block IS the state**:

* **Not finalized** = the cue still has its `------- Metadatas -------` block. (Initially, all of them.)
* **Finalized** = the metadata block has been **removed** and the cue contains only the final subtitle text (1-2 lines). Once you're sure about a translation, strip the metadata: that cue is done and must not be touched again unless the user asks.
* **Question pending** = the metadata block is kept and you add a line `[finalizer] {Question:<short question for the user>}` (and optionally `[finalizer] {Suggestion:<your best-guess translation>}`). When the user answers, resolve the cue and strip the metadata.

Splitting/merging:
* **Split** a cue = make 2+ cues with timings that tile the original range (cut inside a silence listed in the cue's `[terrain] {Silences}`). Finalized pieces get no metadata; if a piece is still uncertain, copy only the relevant metadata to it.
* **Merge** cues = one cue spanning the combined range. Merge same-speaker, back-to-back (small gap) cues into one sentence. Different speakers may only be put in one cue as a **dash dialogue** (`- ...` / `- ...`, STYLE-GUIDE section 6) when both lines are short and back to back; **the user does not run the toolbox conformer while finalizing with the assistant, so the assistant adds the dashes itself**. Never stitch one speaker's sentence across another speaker's interjection.
* Keep a split/merged cue's text within the style guide's limits (line length, reading speed).

---

## 5. Working Mode: Waves

Work in **waves** (details in [WORKFLOW.md](WORKFLOW.md)):
1. **Wave 1: the easy ones.** Go through the whole part and finalize every cue you are confident about (translation, split points, merges). Leave anything suspicious untouched (with a `[finalizer] {Question:...}` line).
2. **Wave 2: questions.** Write the questions in the scene's `REVIEW.md` (timestamp, what you see in the data, what you need to know). The user checks the video and answers; you apply the answers.
3. **Wave 3: polish.** Final pass over the whole file (consistency, reading speed, cue overlaps, check no metadata is left), the numbering and the CRLF conversion are done by `tools/finalize_srt.py` (never renumber the WIP file: the user diffs it).

Keep the user informed in short plain updates. At the end of each wave, report: how many cues were finalized, how many remain, and the list of open questions.

---

## 6. Tools

* **`tools/create_working_srt.py`** (Python 3, standard library only): creates the work-in-progress `<S>-<P>.WIP.srt` from `<S>-<P>.final-ai-debug.srt` + `<S>-<P>.Worker.*.TERRAIN-MAP.srt`.
  * `python tools/create_working_srt.py Scenes/<SCENE>` processes every part of the folder; or `--debug <file> --terrain <file>` for a single part; `--min-ms 100` is the minimum silence length.
  * The output is the debug file, byte for byte (BOM, line endings), plus one `[terrain] {Silences:...}` line in each cue's metadata block (see 2.2).
  * It **never overwrites** an existing working file (it prints "skipped"), and reports an error when a part has SEVERAL TERRAIN-MAP files. **A missing TERRAIN-MAP is allowed**: the WIP is created with `{Silences:none}` on every cue (assume no silence anywhere) and a note is printed.
  * Inputs are never modified.

* **`tools/renumber_srt.py`** (Python 3, standard library only): renumbers the cues of one or more `.srt` files 1..N in file order, in place.
  * `python tools/renumber_srt.py <file.srt> [...]`; `--dry-run` only reports.
  * Only the number lines change (BOM, CRLF/LF mix, timings, text, metadata untouched). Refuses to write if a cue has no number line. Also reports overlapping / out-of-order cues.

* **`tools/view_cues.py <working.srt> [--from <cue# | HH:MM:SS>] [--count N] [--brief] [--all] [--old] [--oneline]`** (`--old` shows the overlapping cues of `<base>.OLD.srt`, an earlier hand-reviewed version, as a source of good phrasings only; `--oneline` = one compact line per cue with the exact start time, speaker, Japanese, translation and OLD, to work through a part quickly)**: read-only compact view of the not-yet-finalized cues: timing + cps, Japanese (both VoiceTexts, `DIFF!` when they differ), current translation, the full `TranslationAnalysis` (the visual paragraph is omitted with `--brief`), silences, manual-input and other metadata. Use it instead of reading the raw file. The analysis is a hint, never proof.
* **`tools/apply_cues.py <working.srt> <decisions.txt> [--dry-run]`**: writes my decisions into the working file: finalize (`@<start>` + text), split (timing lines inside the block), merge (`@<start1>+<start2>`), or question (`Q:` / `S:` lines, metadata kept), or redo an already finalized cue (`@!<start>`), or insert a cue where none exists (`@^<start>` + one timing line + text, for a voice that has no cue). A block with only `D:` **deletes** the cue (no speech: breath, noise, empty VoiceText). Any finalize/split/merge block can carry `R: <doubt>` lines: the cue is finalized as usual and a line `- [ ] <part> HH:MM:SS | text | doubt` is appended to `REVIEW.md` (the single review file of the scene folder, shared by all its parts), the list of cues the user should re-check by ear (or with `extract_audio.py` + a second transcription). Use it instead of keeping doubts only in chat. Format at the top of the script. All-or-nothing validation; keeps BOM and line endings; warns on lines > 42 chars, > 2 lines, > 20 cps. Put the decisions file in the session scratchpad, not in the repo.

* **`tools/extract_audio.py <working.srt> --at HH:MM:SS [--at ...] [--cue N] [--range S E] [--pad-ms N]`**: cuts the audio of subtitles (or of a time range) out of the scene's `.mp4` with ffmpeg into 16 kHz mono `.wav` files in a `clips/` folder next to the `.srt` (git-ignored), named `<base>.<start>_<end>.wav`. The user gives those clips to the transcriber to redo a transcription. The assistant never listens to or reads the video: the tool only hands it to ffmpeg. **Standing rule: before reporting a part, extract the clips of all unchecked `REVIEW.md` items yourself, without asking (see WORKFLOW.md, "Audio clips for the review items").** Offer it when a cue stays doubtful after the romaji questions (or when the transcription itself looks wrong); **extracting clips preemptively is always an option**: extract the doubtful clips and tell the user to run them through the transcriber. **The transcriber AI does not see the file names**, so the match between a transcription and a clip is fuzzy: send the clips in a known order and give the user a numbered table (order, cue time, current text, **duration**); the durations help to match the answers back to the cues. Ask the user to answer in the same order.

* **`tools/finalize_srt.py <base>.WIP.srt [--config FILE] [--no-inject] [--out FILE] [--extend-ms N] [--min-ms N] [--gap-ms N]`**: the very last step, **run when the subtitles are final, always immediately followed by `publish_srt.py`** (user rule: "finalize" = both, on the user's go) (it also does the CRLF conversion and the numbering). Writes the **plain `<base>.srt`** (the final file) from the `.WIP.srt`, which is never modified (so a second run can't add the time twice). It adds 300 ms to every end, makes every subtitle at least 1 s long, never past the next subtitle's start (starts untouched), **injects the credit subtitles listed in the config**, and renumbers. Refuses a file that still has metadata. Prints a report (extended / limited by the next cue / still < 1 s).
  * **Config**: `finalize.config.json` at the repo root (or one next to the `.WIP.srt` to override it), same shape as the FunscriptToolbox output rule: `MinimumSubtitleDuration`, `ExpandSubtileDuration`, `SubtitlesToInject` (`Origin` Start/End, `InjectInAllFiles`, `OffsetTime`, `Duration`, `Lines`). The assistant reads it when creating the final file: to change the credits or the timing rules, edit that file, not the tool.
  * **Injected subtitles never overlap the dialogue**: they are added after the timing pass and *crunched* (shortened) to fit; with no room at all they are still injected, **with duration 0** (the credits are mostly a marker in the text file, so their reading speed is not checked). A warning lists each crunch. `Origin: Start` = starts at `OffsetTime` and is cut at the first dialogue (credits 0-10 s + first dialogue at 3.07 s -> 0-3.07 s); a negative `OffsetTime` = before the start of the video (clamped to 0, SRT has no negative time). `Origin: End` = **starts `OffsetTime` before the end of the video** and lasts `Duration` (`OffsetTime` = `Duration` -> ends exactly at the video end); a **negative `OffsetTime` puts it after the end of the scene**; its start moves later if a dialogue subtitle is still showing.
  * `InjectInAllFiles: true` = in every part; `false` = first part only for `Start`, last part only for `End` (parts = the sibling `.WIP.srt` files of the folder, part token `A`, `D`, `R1`, `2`...).
  * **`<clean name>.parts-duration.txt`** (in the scene folder, extracted by me from the scene's `.wipsubtitles` file, `TimelineMap.Segments`, see WORKFLOW.md Setup): one line per part, e.g. `HNVR-141-A.mp4 00:29:40.970`. Needed for any `Origin: End` injection: if it is missing (or has no line for the part), the tool stops with an error instead of guessing.

* **`tools/lint_srt.py <file.WIP.srt> [...] [--min-severity warn] [--rule ID] [--summary] [--strict]`**: read-only style check of the finalized cues, driven by **`lint.config.json`** (repo root; the user can read and edit it: regex `rules` with severity/message/enabled, numeric `limits` for line length, lines, cps, orphan last word). Known false positives go in `<scene folder>/lint.ignore.txt` (`<rule-id> <HH:MM:SS>`). Run it before finalizing and fix or justify every `warn`/`error`; when a style rule is added to STYLE-GUIDE.md, add its pattern to `lint.config.json` too. `lint.config.json` also has `repeats` (a word used N times in the last M cues: `cum`, `boobs`, `cock`), reported as `info`.

* **`tools/pair_cues.py <base>.WIP.srt [--debug FILE] [--from HH:MM:SS] [--to HH:MM:SS] [--cue-numbers]`**: read-only. Prints, for every finalized subtitle, `time | English | Japanese` where the Japanese is the VoiceText (or OnScreenText) of the debug cues it overlaps (priority: `[manual-input]`, `[singlevad-ai-refined]`, `[full-ai]`). Cues that still have metadata and the injected credits of a final `.srt` are skipped. It is the evidence to print in the conversation before asking the **advisor** (or a stronger model) for the final review of a scene (WORKFLOW.md, wave 3, step 2b).

* **`tools/publish_srt.py <SCENE> [--dry-run] [--release] [--release-dir DIR] [--no-asig] [--title "..."] [--include-different]`**: the step after `finalize_srt.py`; **I run it, the user never does** (he asks me). It copies each final `.srt` next to **every copy** of the video found in the `VideoFolders` of `extract_audio[.private].config.json` (searched in order, recursively), after saving the old `.srt` as `<name>.srt.BACKUP-<date-time>` (never deleted; the user cleans them up by searching for `BACKUP`). It does it by default (no preview) and prints the list of files changed. **The first copy found is the reference: a copy whose size in bytes differs is not touched**; the tool prints it and writes it in `Scenes/<S>/REVIEW.md` under `## Publish questions`; I report them to the user ("files X, Y, Z were not processed because the video size differs, add the subtitles anyway?") and, only on his yes, run again with `--include-different`. `--release` also fills the git-ignored `Release/` folder (`<scene>-<part>.srt/.asig`, the `.asig` from the first copy, or `<scene>-<part> - <title>` with `--title` / `Scenes/<S>/RELEASE.json`); the forum text is made by me on request (WORKFLOW.md, "Prepare the batch"). Settings: `publish.config.json` (+ `publish.private.config.json`, git-ignored).

### Improving the tooling (the user is open to it)

The user said the terrain formats can change and that you may need more helper scripts. If a repetitive or error-prone step keeps coming up (e.g. "show me the terrain and subtitles around 12:34", "list cues with reading speed over 20 cps", "renumber the SRT", "list cues where the two VoiceTexts differ"):
* **Propose it to the user first** (what it does, what input it needs). Don't silently add large tooling.
* Put helper scripts in a `tools/` folder here, read-only with respect to inputs, and document them in `WORKFLOW.md`.
* If the change would be in the process that *generates* the input files (e.g. a different TERRAIN-MAP format), you can't do it from here: describe the change you'd like to the user.
