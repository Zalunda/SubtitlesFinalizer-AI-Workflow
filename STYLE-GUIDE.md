# Style Guide - Subtitles Finalizer

The goal of the translation is **English that a real person would say out loud**, short and with punch, faithful to what was said and to the mood of the scene. This builds on the lessons learned comparing the AI output with earlier hand-reviewed subtitles: the older, manually reviewed lines were usually more natural, with more contractions, fragments and attitude.

When `[manual-input] {OngoingContext}` gives a direction for the scene, it **overrides** this guide on tone and vocabulary.

## 1. Spoken register

* **Always contract** (`you're`, `I'm`, `it's`, `don't`, `can't`, `we'll`...) except for deliberate emphasis or a really formal speaker.
* **Casual forms** for casual/teasing/aroused speakers: `gonna`, `wanna`, `gotta`, `kinda`, `c'mon`, `huh?`, `right?`. Not for shy/polite speakers (clean contractions only).
* **Clip the questions**: `Feel good?` `Getting turned on?` `Wanna see more?` `Hungry, Kou?` `About the same age?` rather than `Does it feel good?` / `Are you getting turned on?` / `Do you want to see more?`...
* **Prefer a tagged statement or a fragment** to a formal question: `You like boobs, huh?` / `No one's ever done that for you, huh?`
* **Plain, short, concrete words**: `hard` (not `stiff`), `kidding` (not `teasing`), `jerk off` (not `fantasize`), `cum` (not `climax`). Avoid `quite`, `rather`, `definitely`, `I wonder if`, `would you like to`, `after all`, `as expected`.
* **Restructure like English does** (don't keep the Japanese clause order or possessives): `You're so big I can barely fit you in my mouth.` not `You've gotten so big you barely fit in my mouth.`
* **Punch over completeness**: a short clip (< ~2 s) should be ~4-6 words or fewer. When two renderings are possible, pick the shorter, blunter one.
* **Don't pad**: no words that aren't in the Japanese to "smooth" the line (`してみ？` = `Do it.`, not `Do it right in front of me.`).
* **Exclamation marks are earned**: only for shouted / very excited delivery. Calm, whispered or teasing lines end with `.` or `?`. No `Okaaay!` stretches unless the Japanese is drawn out.
* **Vary the fillers**: `ほら` is not always `Look.`: use `Come on.` / `Go on.` / `See?` / `Here.`, or drop it. Never repeat the same filler 3+ times in a short span. `だめ？` must be rendered by what it means in context (`Should I stop?` / `Can't take it?` / `Not allowed?`), consistently.
* **Avoid "the X you love so much"** (`the head you love so much`, `the breasts you love`...): it doesn't sound natural to the user. Say `your favorite spot` / `this part` / just the noun, or restructure.
* **`大好きな X` / `your favorite X`**: `your favorite boobs` reads awkwardly (the user never understood it). Drop the 大好きな or restructure; don't write `the X you love so much` either.
* **Repeated body words**: when `boobs` / `cock` / `pussy` come back in lines close to each other, replace some by `them` / `it` / `there`: not every line needs the noun.
* **Vary `cum`**: in scenes with a lot of `are you gonna cum / did you cum / don't cum yet / you came so much` the word becomes a wall. Rotate: `close?`, `already?`, `finish`, `let go`, `give in`, `lose it`, `shoot`, `blow`, `a lot came out`, `so much came out`, `juice`... Keep `cum` where the Japanese is `イク`/`出る` in a real peak (Tier 3). Not every line can be varied: the lint (`cum-repeat`, 3 in 6 cues) only flags clusters, the user decides.
* **Avoid `like this` / `like that`** (user rule, 3DSVR-1410): `Wanna cum in my mouth like this?`, `Can I put it in like this?`, `Don't cum like this, okay?`, `Just like this...` sound unnatural; the Japanese is usually このまま / こんなに / そう and carries no manner clause. Restructure or drop it (`right here`, `in my mouth`, `yet`, `keep doing that`...). Sometimes fine (`hold you like this`). The lint rule `like-this` flags it (verb `you like that` is ignored).
* **Lint = flags, not rules** (user decision, 3DSVR-1410): the extra `lint.config.json` entries (repeat counters for `so good`, `come on`, `hey`, `hard`, `twitching`, `deep`...; `no-contraction`, `double-cant`, `dont-refusal`, `ever-before`, `shall`/`perhaps`, typo guards) only flag cues for a second look. Keep the line when it is right in context, and silence a known false positive in the scene's `lint.ignore.txt`. The POV-man may be answering off-camera, so `You said...` is valid and is NOT flagged.
* **Match the speaker**: a teasing older woman is relaxed, slangy, a little bossy; a shy girlfriend is softer and hesitant but still contracted; neither writes essay English.

* **Vocabulary choices confirmed by the user**: `生` (bareback) = `raw` (not `bare`); `お姉様` = `Mistress` when the outfit/tone is domme-ish, `Big Sis` otherwise (decide per scene).

## 2. Pronouns / who is talked to

* Respect each cue's `Vector:` in the analysis: `To POV (Use 'You')`, or to a third person (`He/His/It`), or the POV-man's inner monologue (`I`).
* When speaking *to* the POV-man about his body, use `you` / `your cock` / `it`, never a bare third-person `he` / `him`.
* Keep names consistent for the whole scene (nicknames, `Senpai`, honorific choices). Decide once, in wave 3 check all.

## 3. Moans, stutters, climax

* No parentheticals or sound tags (`(sighs)`, `[moan]`) in subtitles.
* **No adverbial `lots`** (user rule, decided on 3DSVR-1702 and CRVR-286): `touch me lots`, `service you lots`, `please cum lots`, `look at it all you like` (when it comes back in every line) read as non-native English for いっぱい / たくさん. Rotate `so much`, `a lot`, `more`, `all over`, `closely`, `as much as you want`, `plenty`, `over and over`, or drop it. `lots of X` (`lots of cum`, `lots of fun`) and `lots more` are natural and stay. The lint rule `adverbial-lots` flags the adverbial use.
* **No written laughs** (`Hehe`, `Haha`, `Hihi`, `ふふっ`/`えへへ` rendered as text) in subtitles (user rule, confirmed on CRVR-286, SIVR-108, HNVR-141, SIVR-102): drop them, don't replace them with another written laugh. If nothing else is left in the cue (a cue that is only a laugh), ask the user before deleting it, or use what is really said in the audio. The lint rule `laugh-sound` flags them.
* Tier 3 (frantic / climax): broken syntax is wanted: ASCII `--` for cut-off words, `-` for stutters (`c-cumming`), ALL CAPS only on a real vocal peak. Don't translate every repeat of `イク、イク、イク...`: keep 2-3 escalating fragments (`I'm cumming-- c-cumming, I'm CUMMING!`).
* Mouth-full speech: when she speaks with his cock in her mouth (the `Gap Summary` / analysis says she is sucking/licking while talking), reflect the obstruction by softening sibilants/dentals (`s`/`z`/`t`/`th` -> `th`/`f`) on a few key words: `Mm, thith ith amazing...`, `In my mouf... pleathe cum lotth inthide...`. Don't slur the whole line; the original AI translation often already did it: keep it (the finalizer can't hear the audio, so trust the analysis and the original).
* Use ASCII `--` and `-`, never the Unicode em-dash `—`.

## 8. Rules inherited from the AI translation prompt ("Maverick" protocol)

These are the rules the translating AI was given. The finalizer must stay consistent with them (the user wanted the style guide to include them).

**Structure and rhythm**
* A clip whose analysis says `Cadence: 1 part` is **one smooth sentence with no internal `...`**. Use `...` only for real structural pauses (2-3 parts): one English chunk per spoken chunk, **same order as the speech** (`At me... in that naughty way... have you been looking all along?`, never inverted).
* **Boundary smoothing**: when two cues are back to back (gap <= ~0.4 s) and the first ends on a starter/conjunction that belongs to the second's clause (`Like,`), move that word to the start of the second cue.
* **Breath/moan integration**: if she audibly pants or gasps between words, show it at the break (`Senpai, your-- ahh... your cock is pressing against me...`, `Like this... nn, right on my skin...`). Tier 2 openings: `Ah...`, `Haa...`, `Mm...`. Tier 1: clean, single hyphen only for a nervous stammer (`U-Um...`).
* Tier 3: clean complete sentences are **forbidden**; `--` mid-word, `-` stutters, ALL CAPS on a real vocal peak, 2-3 escalating fragments instead of 5-7 repeats (already in section 3).

**Erotic idiom and meaning**
* Translate the erotic and emotional reality, not the literal text; default tones: affectionate, caring, cute, casual, playful, teasing, sensation, service. Avoid descriptive/explanatory phrasing.
* `気持ちいい` about **her own** pleasure: keep the core meaning (`feels so good`). Exception: when the POV-man is just fondling her with his hands and she asks `気持ちいい？`, don't use a literal `Does it feel good?`: use the situation (`Having fun?`, `Enjoying yourself?`, `Do they feel nice in your hands?`).
* `声が出ちゃう` -> `I'm gonna moan` / `You're gonna make me moan` (never `make noise`); `おっきい声出ちゃって` -> `I moaned so loud`; `変な気分になっちゃう` -> `You're getting me all worked up` / `It's putting me in a naughty mood`.
* `すごい` / `やばい` during pleasure -> `Oh god...`, `So good...`, `This is insane...`, `This is too much...` (avoid flat `Amazing` / `dangerous`).
* **Denial protocol**: `だめ`, `やめて`, `無理` during arousal are sensory overload, not refusals: use `Can't` / `Too much` (`I can't--!`, `I can't take you touching me there!`), not `No, no`.
* **Scenario metaphors / double entendres**: when natural and short, weave the scene's premise (`OngoingContext`: hospital -> `overtime`, `discharge`, `bedside manner`; a timed challenge -> `rising to the challenge`) into the line, never longer than the clip allows.
* **Agency for body parts (user-approved, HNVR-141 pilot)**: a cock or a pussy has few states (hard, not hard, twitching), so the same line gets boring. Give `it` / `your cock` / `my pussy` an **attitude or an action** instead: `waking up`, `fired up`, `ready to burst`, `raring to go`, `at attention`, `wide awake`, `restless`, `joining in`, `perks up`, `burning up`, `unstoppable`, `drenched and waiting`, `off limits`. Goal = **more variety**, and it is often *shorter*; plain `hard` / `swollen` is still fine sometimes.
  * **Never `he` / `him` for the cock** (important, confirmed by the user): the subject stays `your cock` / `it`.
  * Only for **state descriptions** (パンパン, ビクビク, ムクムク, 熱い, 硬い, すごい...) in a playful/teasing Tier 1-2 line. Never in Tier 3 moans, commands or feelings. Don't add facts the Japanese doesn't carry (`begging`, `desperate`) unless the tone is there. Don't use the same image twice within a few cues.
  * The pussy is riskier (the Japanese is usually blunt: `欲しい？` = `Want my pussy?`): only when she is teasing, and only if the line doesn't get longer than the clip allows.
* **Vary `すごい` / `やばい`**: they are very frequent; rotate `insane`, `crazy`, `too much`, `oh god`, `unstoppable`, `something else`... instead of one translation.

**Economy**
* **Smart tag compression**: avoid clunky tails (`, isn't it?`, `, don't you think?`); bake the nuance into the clause (`really`, `so`, `still`), front-load real questions (`May I touch it?`), and for teasing `...でしょ？` use a direct assertion (`You know how good this feels.`).
* **No "for me"** at the end of `-てください` requests (`cum for me`, `lie back for me`) unless `私のために` is said.
* **Trim the fat**: prune `just`, `even`, `well`, `actually`, `basically`, `kind of`, `be the one to`, `go ahead and`, unless vital to a shy/sassy inflection. **Only prune a filler that has no counterpart in the Japanese.** Keep it when the Japanese says it (user rule): `〜ちゃえ / 〜ちゃいなよ / 〜しなよ` -> `just` (`Just cum!`, not `Cum!`), `なんか` -> `kinda`, `まあ` -> `well`, `〜も` -> `even` (`I even showed you my pussy!`), `ちょっと` -> `just/a bit`. If she says several syllables in Japanese, don't shrink the English to one short word.
* **Red-flag words**: `properly` (`ちゃんと`) is a sign of a stiff translation: restructure (`doing my job`, `wiping you down`, `the right way`...). `amazing` and a long `this is insane` can also be too much for a short clip: `insane...` / `too much...` alone is enough.
* Zero parentheticals / sound tags; keep the persona and the `Vector:` pronoun rule.

## 4. Splitting lines inside a cue

* **Max 2 lines, ~42 characters per line.** Prefer a short single line.
* Break at the **natural phrase boundary**, matching where the speaker pauses, then balance the lines (second line not much longer than the first). Never leave a single orphan word alone on a line (`...Rio.`); never break after a hyphen in a hyphenated word (`non-` / `alcoholic`).
* Don't break between an article/preposition and its noun, or between a short subject pronoun and its verb.
* A multi-part spoken line (real pauses) keeps the **same order** as the speech: each English chunk must match what is heard at that moment (don't invert the clauses). If the pause is long, make it two cues rather than `...`.

## 5. Splitting / merging cues

* Cut inside one of the silences of the cue's `[terrain] {Silences}` line. Inside a stretch of sound, cut only a **really long** cue (too long to read), and only once the user has confirmed the spot (see AGENTS.md, "Cutting inside continuous sound"): give them the romaji so they can find the place by ear.
* Reading speed: ~17 cps target, ~20 cps max for rapid lines. **Short display time is NOT fixed here**: a post-processing step run by the user afterwards adds ~0.3 s to every end and makes every subtitle at least 1 s long. So don't stretch, merge or drop a short cue (`There.`, `Right?`) just for display time; judge reading speed on the real audio timing. (Rule still to be discussed with the user.)
* Same speaker + back-to-back (gap < ~0.4 s) + one thought → merge. **Never merge across a speaker change as one sentence** (a short exchange of two speakers can share one cue in the dash format, see section 6), and don't let one speaker's sentence be split by another's interjection: finish each sentence in its own cue.
* **A sentence split over two cues** (pause too long to merge, gap >= ~0.4 s) ends its first cue with `,` or `...` (user rule, PPVR-020): `You showing me your cock...` / `was just to fix the noise...`. Never leave the first half with no ending mark. The second cue starts in lowercase and gets no leading `...`. Before keeping such a split, check it is not a merge candidate (same speaker, gap under ~1 s, short enough for 2 lines): keep it split when the pause is real (~0.7 s or more).
* Tiny fragments (`Then...` / `Right?` alone at < 0.5 s) should be attached to the neighbouring cue of the same speaker when the sentence continues.

## 6. Two speakers in one cue

Use the dash format, each speaker on their own line:

```
- Can you manage that?
- I can!
```
Only when both lines are short and back to back (gap <= ~0.5 s, total <= ~4 s, each line <= 42 characters **including the `- `**); otherwise use two cues. The toolbox conformer (which builds these dash cues automatically) is **not** run when finalizing with the assistant, so the assistant writes the `- ` itself: give the merge decision as `@<start1>+<start2>` with the two dash lines as text. Order = order of speech. Both lines get a dash, even when one is very short.

**Never let two cues overlap in time (user rule, 3DSVR-1072):** the user's player may hide the first subtitle when the second starts. When two speakers talk **at the same time** (e.g. a girl whispering over a PA announcement), they share the same audio: make **one dash cue** covering both, whatever the length of each line (shorten the less important line to fit 2 lines). A new cue inserted with `@^` must never overlap a neighbour; `renumber_srt.py --dry-run` and `finalize_srt.py` report overlaps: fix every one before finalizing.

## 7. Don't-lose-info checklist (before finalizing a cue)

* Does it say what the Japanese says (meaning, who it addresses, question vs statement)?
* Does it fit the conversation before and after (callbacks: "legs / hands", "dinner", etc.)?
* Is it the *shortest* natural way to say it?
* If the two VoiceTexts disagree or the line doesn't fit its neighbours, it is not finalized: ask (see WORKFLOW.md).
