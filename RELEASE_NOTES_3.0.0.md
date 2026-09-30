# 🍌 BananaPhone 3.0.0 — Primate talks. I make sense. Now I teach.

Two years I have been cleaning up your grunting and handing it back as English, and not
once did you ask *why* it needed cleaning. Fine. From now on I show my work.

Until now BananaPhone was a translator: it made you sound professional in a language you
do **not** speak. 3.0.0 adds the other half — it makes you sound professional in a
language you **do** speak, and then tells you, patiently, which four mistakes you have
been making since the day you installed it.

<div align="center">
<img src="docs/screenshots/dictate-coach.png" alt="Dictate with the language coach" width="620">
</div>

---

## The bug that started it

`transform_output_text()` opened with an unconditional early return:

```python
if source_language == target_language:
    return text          # writing layer never ran
```

Dictating **EN → EN** therefore pasted the raw transcript, stumbles and all. Only the
translated routes (PT → EN) ever got professional prose. If you speak the language
yourself, the app did nothing for you.

That is fixed, and everything below grew out of fixing it.

---

## New

### Output style — Raw | Professional

A segmented control under the INPUT/OUTPUT selectors. It is the third leg of the same
decision: what goes in, what comes out, and **how hard the model may rewrite it**.
It applies to translated routes too, not just same-language ones.

**Raw is not "no processing".** Speech-to-text artifacts and outright errors are still
fixed; your sentence structure, word order and bluntness survive.

| | |
|---|---|
| **You said** | *"Okay so I woke this morning and the watch never ring. The watch just stopped in my pulse doing nothing. I woke before 7 hours..."* |
| **Raw** | "I woke this morning and my watch never rang. The watch just stopped on my wrist and did nothing. I woke up before 7 AM..." |
| **Professional** | "This morning, my watch did not ring. It stopped working on my wrist. I woke up before 7:00 AM..." |

### Restyle without speaking again

Flip Raw ↔ Professional **after** you have spoken and the panel and clipboard both
re-render what you already said. Each style is generated once per dictation and cached:
the first flip costs one call (~0.9 s), every flip after that is instant (~0.2 s).

### Language coach

After a dictation in a language that is not your first, a second pass compares what you
said against the corrected version and tells you what to fix.

- **Simple (default)** — exactly one correction, two lines:
  ```
  "in my pulse" -> "on my wrist"   (Pulso em português é 'wrist' em inglês.)
  False friend  [4x]
  ```
- **Advanced** — up to four corrections with a full explanation each.

Simple is the default on purpose: a wall of corrections gets skimmed and then ignored,
which is worse than one correction that lands. It is also **56% cheaper** than Advanced.

**Corrections are written in your first language**, because a rule lands in the language
you think in. Tips are categorised from a closed set — `misheard`, `false_friend`,
`tense`, `phrasal_verb`, `preposition`, `word_order`, `word_choice`, `register` — because
a tip you cannot count cannot tell you what you keep getting wrong.

`misheard` is the honest stand-in for pronunciation. No text pipeline hears you, but when
the recognizer turns your word into a *different real word*, that is the machine failing
to understand you — the same failure a human on a bad line would have.

### The counter is a rolling window, not a scoreboard

The panel header shows your top weakness over the **last 30 corrections**, not all time.
A lifetime total can only grow, so it can never show you improving. A category you stop
making drops out of the window; the lifetime count stays in the profile as the record.

### My first language

<div align="center">
<img src="docs/screenshots/settings-coach.png" alt="Settings" width="420">
</div>

Detected from your OS locale on first run, changeable in Settings. It decides which
language is *never* coached, and which language the corrections are written in. Works for
a Portuguese, Spanish or English speaker learning any of the others.

---

## Rules the coach follows

- **It never touches the clipboard.** Work output stays paste-ready.
- **It runs on its own thread**, started only after the clipboard is already loaded. A
  coach failure never costs you the dictation.
- **It is keyed on what you spoke**, not on the route. EN → PT is still your English.
  PT → EN is not coached — there the English is the model's.
- **It is off in Jira Mode.** A ticket is work, not class.
- **Jira Mode is untouched by all of this** and keeps its 2.6.0 behaviour exactly.

---

## Fixed along the way

- **The rewrite invented a fact.** Given a short dictation, "stopped in my pulse" became
  "stopped **monitoring my pulse**" — something the user never said — while Raw deleted
  the clause instead. Both prompts now carry an explicit false-friend table
  (`pulse=wrist`, `actually=currently`, `pretend=intend`, …) and a hard *never drop a
  clause you cannot resolve* rule. The false friend must be read with the meaning the
  speaker intended **even when the English reading would make sense on its own**.
- **A stale "coach off" message survived activation.** Switching INPUT from Portuguese to
  English swapped the panel title but left the old body text, so it kept insisting INPUT
  was Portuguese. The body now tracks whether it holds a status message or live tips, so
  a stale message is cleared while tips you are reading are never wiped by a repaint.
- **The coach used to vanish silently** when it had nothing to say, which is
  indistinguishable from a bug. In Dictate it is now always visible and says *why* it is
  off, naming the setting that turns it back on.
- **Read-only panels were barely legible.** CustomTkinter dims the text of a disabled
  widget; on the near-black field that is close to invisible. Read-only is not inactive,
  so the colour is pinned.
- **Settings checkboxes and labels** inherited the theme's low-contrast text colour and
  were unreadable on the dark dialog.
- Short coach notes are trimmed on a **word boundary** — a note cut mid-word reads as a bug.
- Changing the output style is refused mid-recording and the control snaps back, so it can
  never display a state the app is not in.
- The restyle cache is dropped when the route changes, so a dictation is never restyled
  with the wrong pair of languages.

---

## Cost

Measured on a 62-word dictation with `gemini-2.5-flash`:

| call | in | out | cost |
|---|---:|---:|---:|
| transcription (existed before) | ~800 audio | ~85 | $0.00101 |
| polish (new) | 570 | 75 | $0.00036 |
| coach, Simple (new) | 629 | 65 | $0.00034 |

Same-language dictation goes from **$0.0010 to $0.0017** per dictation — **+72%** in
percentage, and under **US$1/month** at 30 dictations a working day. Turning the coach
off brings it to +35%; turning polish off restores 2.6.0 behaviour exactly.

---

## Upgrading

Settings migrate automatically. Both new features default **on**; on a same-language route
your text now goes to the text model where it previously stayed local, and the status line
says so (`Style: Raw | Coach`). Turn either off in Settings.

New files in `~/.config/bananafone/`:
`coach_profile.json` — category tally, plus the last 200 corrections with timestamps.
