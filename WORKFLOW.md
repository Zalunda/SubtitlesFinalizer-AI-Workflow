# Workflow - Finalizing the Subtitles of a Scene

Applies to **each part** (`A`, `B`, `C`...) of a scene folder (`Scenes/<SCENE>/`) independently. See [AGENTS.md](AGENTS.md) for the file formats and golden rules, and [STYLE-GUIDE.md](STYLE-GUIDE.md) for the style.

## Step 0 - Setup (once per part)

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
4. **Suspicious cues**: leave the metadata block and add `[finalizer] {Question:...}` (+ `{Suggestion:...}` if you have a best guess). Don't spend time agonizing: that's what wave 2 is for. If you can finalize with a decent guess but are not sure, finalize it and add an `R:` note in the decisions file: it lands in `<S>-<P>.review.md` for the user's audio check.

### Splitting / merging checklist
* Total subtitle characters per line <= ~42, max 2 lines (see the style guide). Split into two cues instead of making a 3-line cue.
* Reading speed: aim <= ~17 chars/sec, tolerate up to ~20 on fast/emotional lines; never below ~1.0 s of display for a cue with more than 1-2 words (if the audio gap is too short, merge with the neighbour instead of flashing it).
* **Split** at a real pause: pick the cut inside one of the silences listed in the cue's `[terrain] {Silences}` line, at the middle of the silence or just after the sound before it ends. Don't cut inside a stretch of sound (`{Silences:none}`) by default. Exception: a **really long** cue with no silence: put a question in the questions file with the cue's **romaji** and the candidate cut point(s) marked `|`, so the user can find the right spot by ear. When a cut at a silence is ambiguous (which words are on which side?), ask the user for what is said in each part, in romaji, before splitting (see AGENTS.md, section 2.2).
* **Cues longer than ~5 s** are not a hard error, but evaluate each one: if a listed silence (>= ~0.3 s) falls between two clauses, split there; if the only candidates are tiny gaps or continuous sound, ask the user (romaji + candidate times in the questions file) or leave it when it is one sentence at a comfortable reading speed. (Silences are only in the metadata of not-yet-finalized cues: decide this *before* finalizing, or use `@!` to redo.)
* **Merge** two cues when they are one sentence/thought from the same speaker, back to back (gap < ~0.4 s), and short enough. **Different speakers**: don't merge into one sentence; but two very short back-to-back lines (gap <= ~0.5 s, total <= ~4 s, each line <= 42 characters including the `- `) may share one cue in the dash format (the conformer of the toolbox is NOT run when finalizing, so I add the `- ` myself). Do not stitch a sentence across another speaker's interjection (the AI process did that; undo it: give each speaker their own cue and finish each sentence in its own cue).
* A cue's start/end should sit on real speech: don't leave a cue showing during long silence/breaths; trim it.
* When two speakers talk in the same cue, use the dash dialogue format from the style guide.

### Rules for the work itself
* Work in batches (e.g. 20-40 cues per round), saving progress to the working file after each batch, so progress survives a stop. Loop per batch: `python tools/view_cues.py <file> --count 40` (reads the next unfinalized cues) -> write a decisions file in the scratchpad -> `python tools/apply_cues.py <file> <decisions>`. Never use the Edit/Write tools on the `.srt` (they normalize line endings).
* Never leave a half-edited cue: either it's finalized (no metadata) or it's untouched/with a `[finalizer]` question.
* Don't revisit finalized cues, except in wave 3 or if the user asks.

## Wave 2 - Questions to the user

1. Collect every cue that has a `[finalizer] {Question:...}` into `<S>-<P>.questions.md`, one numbered entry per question, ordered by time:

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
3. When the user answers (in `questions.md` or in chat), apply each answer: fix the transcription/translation, finalize the cue, strip its metadata (including the `[finalizer]` lines).

## Wave 3 - Polish and finish

1. Re-read the whole working file from the top, as a viewer would (only the subtitle text), and fix: inconsistent names/terms/pronouns, repeated filler ("Look." x5), tone drifting, tags that don't match the character, anything unnatural.
2. Run `python tools/lint_srt.py Scenes/<SCENE>/<S>-<P>.WIP.srt --min-severity warn` and fix every finding (or add the false positives to `Scenes/<SCENE>/lint.ignore.txt`). Check: no `------- Metadatas -------` left; no overlapping cues; every cue has valid timing; reading speed outliers (flag/fix); each part ends cleanly.
3. **Do NOT renumber or convert the WIP file** (the user diffs it while you work: renumbering makes the diff unreadable). The numbering and the Windows CRLF line endings are produced at the end by `tools/finalize_srt.py` in the final file.
4. When the user says the subtitles are final: `python tools/finalize_srt.py Scenes/<SCENE>/<S>-<P>.WIP.srt` (adds 0.3 s to every end, minimum 1 s, limited by the next start; writes the final plain `<S>-<P>.srt`; the WIP file is kept). Run it once, last.
5. Report a final summary (cues finalized / split / merged / questions resolved) and anything you want the user to double-check.

## Audio clips for the review items (standing rule, user decision)

**Single channel (user decision): `<S>-<P>.review.md` is the ONLY place for questions, doubts and clip tables of a part. Do not repeat them in the chat.** When a part is done, write/update the review.md (sections: *Clips to transcribe* with the numbered table, *Open questions* with an `Answer:` line each, *Cues finalized with a doubt*) and tell the user only: `I created/updated <S>-<P>.review.md` + the counts (cues finalized, questions, clips). Questions that used to go to `questions.md` go to the review.md too. The user answers in the file or in chat; tick the items when resolved.

**Before showing the report of a part, always extract the audio clips of every unchecked item of `<S>-<P>.review.md` (and of any open question that audio can answer) with `tools/extract_audio.py`. Never ask the user whether to do it.** Then put in the report a numbered table (order, cue time, current text, duration, what to check) so the user can send the clips to the transcriber in that order.
* `--at HH:MM:SS` takes the cue that *contains* that time: use a time inside the cue (a second after its start), not the review line's rounded time, or the tool picks the previous cue. Check the printed time ranges.
* If `<S>-<P>.mp4` is only a `.lnk` shortcut, resolve its target (PowerShell `WScript.Shell` `CreateShortcut(...).TargetPath`) and pass it with `--video`.
* Delete the `.wav` clips once the user has answered.

## Reporting format (end of each wave)

Short and concrete: `Wave 1 of part A: 312 cues finalized (18 split, 9 merged), 41 left with questions. Questions are in HNVR-141-A.questions.md.` Mention anything that surprised you (a systematically bad stretch, a speaker mix-up) because it may point to an upstream problem in the AI process the user can fix.
