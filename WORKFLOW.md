# Workflow - Finalizing the Subtitles of a Scene

Applies to **each part** (`A`, `B`, `C`...) of a scene folder (`Scenes/<SCENE>/`) independently. See [AGENTS.md](AGENTS.md) for the file formats and golden rules, and [STYLE-GUIDE.md](STYLE-GUIDE.md) for the style.

## The scene checklist (the backbone of this workflow)

**Every scene has a `## Progress checklist` at the very top of its `Scenes/<S>/REVIEW.md`** (right after the title). It is the single place that says what is done and what is left. Rules:
* **Create it at Step 0**, copied from the template below, with the first items ticked as they are done. Never start a scene without it.
* **Update it as you go**: tick `[x]` an item the moment it is done (same edit as the work, no batching at the end). Add scene-specific sub-items under a step when needed (e.g. one line per part, one line per open question batch). Items that depend on the user stay unticked until the user acts.
* **The steps below are the detail of each checklist item**; when starting a new session on a scene, read the checklist first to know where to resume.
* A skipped step is not silently ticked: write `[x] ... (skipped: reason)` or `(none raised)`.

Template (parts = `A`, `B`... or `-2`, `-3`; tick per part when it matters, e.g. `[x] Wave 1 part A / [ ] Wave 1 part B`):

```markdown
## Progress checklist

- [ ] Setup
  - [ ] `.parts-duration.txt` (from the `.wipsubtitles` / the user's clipboard text; if the user supplies nothing, check whether it already exists in the scene folder: for some scenes it is already there, then tick this item as "already present")
  - [ ] WIP files created (`create_working_srt.py`); TERRAIN-MAP present or "no terrain" noted
  - [ ] Scene context read (`OngoingContext` / speakers); asked the user if missing
- [ ] Pilot batch (first ~40 cues) + report: sample, character understanding
  - [ ] Tone confirmed by the user
  - [ ] `GLOSSARY.md` created
  - [ ] Corrections applied to the pilot cues
- [ ] Wave 1: all easy cues finalized (per part)
- [ ] Wave 2: questions
  - [ ] Clips extracted for the unchecked items, table + context for the transcriber
  - [ ] User's answers applied
- [ ] Scene name (`## Scene name`: Actors in western order, Title) confirmed by the user
- [ ] Wave 3: polish
  - [ ] Re-read as a viewer (names, terms, repeats)
  - [ ] `lint_srt.py` clean (fixed, or justified in `lint.ignore.txt`)
  - [ ] Final review: `pair_cues.py` printed, advisor called, proposals in REVIEW.md
  - [ ] User ticked the proposals, applied (`@!`), lint rerun
- [ ] `finalize_srt.py` (`--extend-ms 0` if the timings were already expanded)
- [ ] `publish_srt.py` (skipped copies reported / `--include-different` answered)
- [ ] Release batch (`--release`, POST-TEXT, CHANGES): only when the user asks
- [ ] Commit of `Scenes/` (only when the user asks; never `git add`)
```

## Step 0 - Setup (once per part)

0. Create (or open) `Scenes/<SCENE>/REVIEW.md` with the checklist above.

1. Check the inputs exist: `<S>-<P>.final-ai-debug.srt` (required: if it is missing, tell the user and stop) and `<S>-<P>.Worker.manual-input-preparer.TERRAIN-MAP.srt` (**optional**: if it is missing, the tool assumes no silence anywhere, i.e. `{Silences:none}` on every cue; say so in your first report and remember that every split then needs the user's confirmation).
2. If `<S>-<P>.WIP.srt` does **not** exist, create it: `python tools/create_working_srt.py Scenes/<SCENE>` (a copy of the debug file where every cue also has its `[terrain] {Silences:...}` line). If it exists, continue from it (don't overwrite; the tool refuses to anyway).
3. Read the scene context from the first cues' `[manual-input] {OngoingContext}` / `{OngoingSpeakers}` (this is the user's direction for the scene). If there is none, tell the user and ask for a one-line summary of the scene and the characters.
4. Skim the whole part first (the files are big: read in chunks, ~500 lines at a time) to learn the scene: who talks, the story beats, the tone.

## Wave 1 - Finalize the easy cues

### Pilot batch first (always)
Don't bulk-finalize a new scene right away. **Finalize the first ~40 cues only**, run `tools/lint_srt.py`, then **stop and report** to the user:
1. a short sample (about 10 lines, Japanese + English) showing the register and the choices made, so the user can say if the tone is right;
2. an **overall understanding of the character(s)** (sensual? teasing? bitchy? shy? sore loser?): the user confirms or corrects it;
3. a first `Scenes/<SCENE>/GLOSSARY.md` (names, recurring terms and how I translate them, the pronoun/vocabulary decisions: see `Scenes/HNVR-141/GLOSSARY.md` for the format).
Only after the user's go (and the corrections applied to the 40 cues and to the glossary) continue with the rest of wave 1. Read the glossary again at the start of every batch, and keep it up to date.

### Then, for each remaining cue

**Never delete a cue on my own** (empty VoiceText, "no speech", breath/noise looking cue): ask the user first (question + questions file, offer audio clips). `D:` in apply_cues is used only after the user confirmed the audio has no speech.

For each cue still holding a metadata block, in order:

1. Read the cue's `VoiceText` (both sources), `TranslatedText`, `TranslationAnalysis`, the neighbouring cues (before/after) and its `[terrain] {Silences}` line.
2. **Decide: easy or suspicious?**
   * *Easy*: both VoiceTexts agree (or the difference is trivial), the Japanese makes sense in the context, the translation matches it, the timing fits the terrain.
   * *Suspicious*: the VoiceTexts differ in meaning, the Japanese doesn't fit the conversation (a name, a topic change from nowhere), the analysis contradicts neighbouring cues (e.g. someone "welcomes" a person who is already in the room), a mid-sentence cut between two speakers, a very short or very long cue with no speech under it in the terrain, mumbling/moans transcribed as words.
3. **Easy cues**: rewrite the translation following the style guide, decide splits/merges (below), then **remove the metadata block**, leaving only timing + subtitle text.
4. **Suspicious cues**: leave the metadata block and add `[finalizer] {Question:...}` (+ `{Suggestion:...}` if you have a best guess). Don't spend time agonizing: that's what wave 2 is for. If you can finalize with a decent guess but are not sure, finalize it and add an `R:` note in the decisions file: it lands in `Scenes/<S>/REVIEW.md` for the user's audio check.

### Splitting / merging checklist
* Total subtitle characters per line <= ~42, max 2 lines (see the style guide). Split into two cues instead of making a 3-line cue.
* Reading speed: aim <= ~17 chars/sec, tolerate up to ~20 on fast/emotional lines; never below ~1.0 s of display for a cue with more than 1-2 words (if the audio gap is too short, merge with the neighbour instead of flashing it).
* **Split** at a real pause: pick the cut inside one of the silences listed in the cue's `[terrain] {Silences}` line, at the middle of the silence or just after the sound before it ends. Don't cut inside a stretch of sound (`{Silences:none}`) by default. Exception: a **really long** cue with no silence: put a question in the questions file with the cue's **romaji** and the candidate cut point(s) marked `|`, so the user can find the right spot by ear. When a cut at a silence is ambiguous (which words are on which side?), ask the user for what is said in each part, in romaji, before splitting (see AGENTS.md, section 2.2).
* **Cues longer than ~5 s** are not a hard error, but evaluate each one: if a listed silence (>= ~0.3 s) falls between two clauses, split there; if the only candidates are tiny gaps or continuous sound, ask the user (romaji + candidate times in the questions file) or leave it when it is one sentence at a comfortable reading speed. (Silences are only in the metadata of not-yet-finalized cues: decide this *before* finalizing, or use `@!` to redo.)
* **Merge** two cues when they are one sentence/thought from the same speaker, back to back (gap < ~0.4 s), and short enough. **Different speakers**: don't merge into one sentence; but two very short back-to-back lines (gap <= ~0.5 s, total <= ~4 s, each line <= 42 characters including the `- `) may share one cue in the dash format (the conformer of the toolbox is NOT run when finalizing, so I add the `- ` myself). Do not stitch a sentence across another speaker's interjection (the AI process did that; undo it: give each speaker their own cue and finish each sentence in its own cue).
* A cue's start/end should sit on real speech: don't leave a cue showing during long silence/breaths; trim it.
* When two speakers talk in the same cue, use the dash dialogue format from the style guide.

### Rules for the work itself
* **Speaker tags** (`[manual-input] {Talker}`, `[singlevad-ai-refined] {Speaker}`, `Speaker Correction` in the analysis) **are hints for me, not a task for the user**. Use them to pick the voice and the dash dialogues. Put a cue in `REVIEW.md` only when the speaker looks wrong to me **and the translation would differ depending on the speaker**; otherwise just follow the content and the best-supported tag.
* Work in batches (e.g. 20-40 cues per round), saving progress to the working file after each batch, so progress survives a stop. Loop per batch: `python tools/view_cues.py <file> --count 40` (reads the next unfinalized cues) -> write a decisions file in the scratchpad -> `python tools/apply_cues.py <file> <decisions>`. Never use the Edit/Write tools on the `.srt` (they normalize line endings).
* Never leave a half-edited cue: either it's finalized (no metadata) or it's untouched/with a `[finalizer]` question.
* Don't revisit finalized cues, except in wave 3 or if the user asks.

## Wave 2 - Questions to the user

1. Collect every cue that has a `[finalizer] {Question:...}` into the scene's `Scenes/<S>/REVIEW.md` (one section per part), one entry per question, ordered by time:

   ```markdown
   ### 12:34 - cue "..."          <- timestamp in the video (hh:mm:ss) so the user can jump to it
   - What the data says: full-ai heard "...", single-VAD heard "..."; translation currently "..."
   - Why it's suspicious: ...
   - Romaji (when the question is about a cut point or what is said): `...kore wa | doko ni...`   <- `|` = candidate cut
   - What I need: what is said/shown? (e.g. is she saying X or Y? who is speaking? what is on screen?)
   - My best guess: ...
   - **Answer:** (the user fills this)
   ```
   Group questions that need the same check (e.g. "all the cues about the bath scene") and keep them short: the user checks the video, so don't make them read your analysis.
2. Stop and ask the user to answer. Don't continue guessing.
3. When the user answers (in `REVIEW.md` or in chat), apply each answer: fix the transcription/translation, finalize the cue, strip its metadata (including the `[finalizer]` lines).

### Scene name (decided while working on the scene)

Each scene's `REVIEW.md` has a section `## Scene name` with two lines, `Actors: ...` and `Title: ...` (a short, meaningful, recognizable title; the video file name's title when it has one). **Actor names are written in western order: given name first, family name last** (Japanese order is family name first). Check what the actress says about herself: if she introduces herself by her given name (e.g. "I'm Mitsuki"), that is the given name, so `Mitsuki Nagisa` (not `Nagisa Mitsuki`). The video file name may use the other order or a different romanization: the scene name in `REVIEW.md` wins; don't rename files on my own. During the pilot or wave 2, I **suggest** the name there (marked `(suggested)`) and the user confirms or edits it (then drop the marker and tick the checklist item); it is used for the release (`publish_srt.py` file names with a title, and the CHANGES file of "Prepare the batch"). The scripter and paid/free are not part of it (always TODO for the user).

## Wave 3 - Polish and finish

1. Re-read the whole working file from the top, as a viewer would (only the subtitle text), and fix: inconsistent names/terms/pronouns, repeated filler ("Look." x5), tone drifting, tags that don't match the character, anything unnatural.
2. Run `python tools/lint_srt.py Scenes/<SCENE>/<S>-<P>.WIP.srt --min-severity warn` and fix every finding (or add the false positives to `Scenes/<SCENE>/lint.ignore.txt`). Check: no `------- Metadatas -------` left; no overlapping cues; every cue has valid timing; reading speed outliers (flag/fix); each part ends cleanly.
2b. **Final review by a stronger reviewer (user rule, before `finalize_srt.py`)**: once the lint is clean and every doubt of `REVIEW.md` is resolved, ask the **advisor** (the `advisor` tool, when the session has it; otherwise switch the session to a stronger model, e.g. `/model opus`, as was done on SIVR-108) for a review of the whole scene. The reviewer only sees the conversation, so **first print in the conversation, for every final cue, the English subtitle next to the Japanese of the debug cues it overlaps** (one line per cue: `time | English | Japanese`, produced by `python tools/pair_cues.py <base>.WIP.srt [--from HH:MM:SS --to HH:MM:SS]`; print it in chunks of a few hundred lines). What to look for: meaning errors vs the Japanese, lines that repeat the same word or structure too often (`came`, `Welcome`, `Not yet`...), callbacks to the scene's premise or rules (`not allowed`, a secret, a running joke), fragments left by a merge/split or by a removed laugh, unnatural word order, denial protocol / `だめ` rendering, consistency with the glossary. Put the proposals in `Scenes/<S>/REVIEW.md` under `Suggested improvements` (one line per proposal: cue time, current -> proposed, reason; `- [ ]`), **don't apply them on my own**: the user ticks / edits the ones to keep, then apply them in the WIP (`@!`) and regenerate the final files.
3. **Do NOT renumber or convert the WIP file** (the user diffs it while you work: renumbering makes the diff unreadable). The numbering and the Windows CRLF line endings are produced at the end by `tools/finalize_srt.py` in the final file.
4. When the user says the subtitles are final: `python tools/finalize_srt.py Scenes/<SCENE>/<S>-<P>.WIP.srt` (adds 0.3 s to every end, minimum 1 s, limited by the next start; writes the final plain `<S>-<P>.srt`; the WIP file is kept). Run it once, last.
5. Report a final summary (cues finalized / split / merged / questions resolved) and anything you want the user to double-check.

## Publishing the final files (after wave 3, when the user asks)

Run `python tools/publish_srt.py <SCENE>` (add `--release`, and `--title "..."` if the user wants a short description in the file names, for the release). It updates the `.srt` next to every copy of each video (with `*.srt.BACKUP-<date-time>` files), and lists the files changed. Report that list in `REVIEW.md` terms: counts in chat, details in the tool output. If some copies were skipped because the video size differs from the first copy, tell the user which files and ask whether to add the subtitles to those versions; on a yes, run again with `--include-different`.

### Prepare the batch (when the user says so, e.g. "prepare the batch for subtitles")

1. Run `python tools/publish_srt.py <SCENE> --release` for each scene of the batch (the scenes finalized and reviewed since the last release; ask if unsure which). Report skipped copies as above.
2. Write two text files in the git-ignored `Release/` folder (the user pastes them in the forum, he drags the `.srt` / `.asig` files himself, so no file lines):
   * `POST-TEXT.txt`: the static post text, the same for every scene (the process link and the "files to synchronize" link, from `publish.config.json` `ProcessUrl` / `SyncUrl`).
   * `CHANGES-<yyyy-mm-dd>.txt`: the "new subtitles of the day" post: one bullet per scene of the batch, `* [<SCENE> - <actors> - <title>](TODO url), scripted by TODO **\[TODO script\]**.` The actors and the title come from the `## Scene name` section of the scene's `REVIEW.md` (`Actors:` / `Title:`), else from the video file name; otherwise I **suggest** a short meaningful title (marked `(suggested)`). The scripter name and the paid/free type are always left as TODO for the user.

## Audio clips for the review items (standing rule, user decision)

**Single channel (user decision): `Scenes/<S>/REVIEW.md` is the ONLY place for questions, doubts and clip tables of a part. Do not repeat them in the chat.** When a part is done, write/update the review.md (sections: *Clips to transcribe* with the numbered table, *Open questions* with an `Answer:` line each, *Cues finalized with a doubt*) and tell the user only: `I created/updated Scenes/<S>/REVIEW.md` + the counts (cues finalized, questions, clips). Questions that used to go to `questions.md` go to the review.md too. The user answers in the file or in chat; tick the items when resolved.

**Before showing the report of a part, always extract the audio clips of every unchecked item of `Scenes/<S>/REVIEW.md` (and of any open question that audio can answer) with `tools/extract_audio.py`. Never ask the user whether to do it.** Then put in the report a numbered table (order, cue time, current text, duration, what to check) so the user can send the clips to the transcriber in that order.
* **Give a small context for each clip in the numbered table (user rule): one or two sentences the user can paste to the transcriber AI along with the clip** (kind of video and setting, who speaks to whom and how, what happens just before and after the clip, from the cue neighbours and the `Gap Summary`), so the transcriber can place the words. Keep it factual and short; don't state my translation as truth, and **don't pass the AI `Gap Summary` / `TranslationAnalysis` on as facts** (it can be wrong and would bias the transcriber): use only what the user confirmed or what is certain (setting, speaker, neighbouring cue texts).
* `--at HH:MM:SS` takes the cue that *contains* that time: use a time inside the cue (a second after its start), not the review line's rounded time, or the tool picks the previous cue. Check the printed time ranges.
* **Where is the video?** `extract_audio.py` first looks for `<S>-<P>.mp4` next to the `.srt`. If it is not there, it searches, **recursively**, the folders listed in `VideoFolders` of an `extract_audio.config.json` / `extract_audio.private.config.json` (read from the `.srt`'s folder up to the filesystem root, plus the ones at the repo root; the user's real folders are in `extract_audio.private.config.json` at the repo root, which is git-ignored by `*.private.config.json`) for a file with the same name. So don't ask the user for the video path: just run the tool. Ask only if the tool says it found nothing (the user then adds the folder to `VideoFolders`, or you pass `--video`).
* If `<S>-<P>.mp4` is only a `.lnk` shortcut, resolve its target (PowerShell `WScript.Shell` `CreateShortcut(...).TargetPath`) and pass it with `--video`.
* Delete the `.wav` clips once the user has answered.

## Reporting format (end of each wave)

Short and concrete: `Wave 1 of part A: 312 cues finalized (18 split, 9 merged), 41 left with questions. Questions are in HNVR-141/REVIEW.md.` Mention anything that surprised you (a systematically bad stretch, a speaker mix-up) because it may point to an upstream problem in the AI process the user can fix.
