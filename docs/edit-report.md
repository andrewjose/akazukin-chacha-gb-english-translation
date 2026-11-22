# Akazukin Chacha (GB) - editor pass v1 (2026-11-22)

> **Repository note.** These notes were written in the original work tree, where `re/`, `engine/` and `ui/` each had
> their own `tools/`. In this repository the build tools are in `tools/re/`, `tools/engine/` and `tools/ui/`, and every
> generated file goes to `build/work/` (see the README). Screenshots, save states, test ROMs, extracted strings,
> captured graphics and the headless test harnesses referred to below are not published (they contain game data);
> everything the build needs is regenerated from your own ROM.

Inputs: tl/out/out_dlg1..6.json (1314) + out_names_ui.json (163), not modified.
Outputs: `merged.json` (all 1477 `{id, en[, short8]}`), `batches_v1/out_*.json` (corrected copies, same format as tl/out),
`canon.csv`, `speakers.csv`, `portraits.png`, glossary.md "## Added by editor".
Reproduce (this order; regenerates merged.json and batches_v1/ byte-identically, checked with cmp):
1. `python3 -I tools/apply_edits.py`: translators' tl/out files -> global terms -> per-line EDITS -> names/UI edits -> `manual_edits.json` (applied last; main-session and round-2 edits live here, never edit merged.json by hand).
2. `python3 -I tools/fix_spacing.py`: round-2 typography (spaces after WAIT/FACE/PAUSE, stutter hyphens); also syncs batches_v1/.
3. `python3 -I tools/validate_all.py` (0 errors), `python3 -I tools/make_canon.py`, then `engine/tools/build.py --tr edit/merged.json`.

## Validation
- `tools/validate_all.py`: 1477 entries, **0 errors** (32 warnings = double spaces from tokens/credits, harmless).
  Covers ids, ASCII charset, token order/count, HEART/NOTE, 85-char box segments (CALL = callee's last box), callee identity and
  trailing `<NL>`, fixed-field widths/HEX bytes, fixed-menu charset (A-Z a-z ? ! - . space) for cmd/quest/fixed and every short8,
  name/item widths, banned variant spellings, name-table names used in dialogue.
- Engine measurer: `engine/tools/build.py --tr edit/merged.json` -> 0 overflow strings, 0 auto splits, 0 hyphens;
  `typeset_check.py`: line_over 0, page_over 0, stranded 0 (layout in tmp/layout.json, sheets in tmp/sheets/).
  Report cards fit their boxes (120x3 / 104x1).

## Lines changed: 141 (of 1477)
| category | lines |
|---|---|
| term unification | 83 |
| callee / CALL patterns | 16 |
| recurring-pattern templates | 16 |
| box fit / font charset | 14 |
| voice / mistranslation | 10 |
| speaker identity | 6 |
(a line can be in two categories; full list in tmp/changes.json)

## Task 1: speakers and name tokens
- Portraits rendered statically from the FACE handler `$00:3E25` (table 04:$4B48: gfx base + expression strip table, 3 strips of 3 tiles).
  The translators' map is **correct**: 0 ChaCha, 1 Riiya, 2 Shiine, 3 Marin, 4 Yakko, 5 Suzu, 6 Seravi, 7 Dorothy, 8 Principal Urara,
  9 Mr. Rascal, A Ms. Mayachon, B Barabaraman, C Elizabeth, D an unnamed thief (only dlg_180).
  0E/0F = party slots (C915 lead, C924 partner). High nibble = expression, except **C**: face+0x0E, so C0 = pig, C1 = cat, C2 = dog
  (Riiya's wolf pup) regardless of who is transformed.
  Corrections to translator notes: batch 2's "appraiser lady" (x7) is Dorothy, its "unknown My my my" (x8) is Urara; batch 4's FACE:47 is Dorothy.
- `<NICK>` / `<NICK2>` (`$3DC4`/`$3DDA`): nick table 0E:$4AB2[speaker CE41 * 6 + target]. **NICK2 = C8D1 = C915 = the chosen lead
  character, NICK = C8D2 = C924 = the chosen partner.** The player picks BOTH (pair table 04:$4ACE indexed [partner][lead] -> dlg_167..17A),
  so either can be any of the six; in battle `01:4A18` temporarily swaps them so NICK2 = the acting character. The form depends on the
  speaker row: only Riiya has non-name forms (Shiine "Dumb Dog", Dorothy "Doggy", Marin "Riiya<3"). All 113 NICK lines re-read: they
  already read right for any name; no line assumed a fixed gender/person. `<NAMEC8D3>` = enemy/char name table, `<ITEM2>` = item table.

## Task 2: decisions (canon.csv)
Trapsalot Dungeon; Darkalot Cave; Fly Shroom (Haetake/Flycap dropped, "the elusive Fly Shroom"); Mericle; Maze of Trials + lowercase
"guardian"; Holy Cup; Holy Water (always capitalized = item); Holy Spring (at the) Holy Falls; **Diary Spell** everywhere incl. UI
(`-Diary Spell-`, `Wrong Diary Spell!`); Yakko Brand (no hyphen; bottles carry "a Yakko Brand label"); Lord Seravi for Yakko
(Sewaviii / Shewaviii baby talk); enchou sensei = Principal Urara; Flying Squirrel Ninja Art unchanged.
Name table changes (to match dialogue): item_12 Ribbon -> **Ribon** (the magazine), item_0D -> **Sage's Staff**, item_21 Holy Seal ->
**Holy Sticker**, item_26 Sea Snail -> **Turban Shell**, name_2E Head Monk -> **Milady** (jp is ojousama). Dialogue now uses the
name-table forms: Shock Frog, Dress/Tee Orca, Skele-Crew, Gag Shroom, Shady Brew, Pickle Stone, Trophy.

## Task 3: patterns and callees
- Urara opener: dlg_120 (= $4C9C) and dlg_1DD (= $751D) identical: `Oh my, my!<PAUSE> Dear me!<NL>` (one line, as in JP); dlg_1B4 opens the same.
- Callees dlg_1F1 / 282 / 28E got their trailing `<NL>` back (JP has it) and callers lost the leading space; 2D5, 31C, 36A, 394, 0B9, 096 checked in every caller.
- One laugh each: Yakko "Oh-ho-ho-hooo!", Rascal "Ha-ha-ha-ha!", chesuto "Hi-YAAAH!"; Yakko potion names identical between hint lines and battle (Hot-Hot Napalm Bomb, Whoa-Whoa Virtual Reality, Peppy Power-Up).
- **Original-game bug, needs a decision in the inserter**: dlg_172 (Shiine partnered with lead Riiya: "Oh, it's just Dumb Dog...") calls
  `$57BE` in its own bank 06, which is the tail of dlg_135 (Rascal: "As a teacher, what am I supposed to do?!"). The intended target is
  clearly `orphan_0E_57BE` (Riiya: "I'm not a dog! I'm a WOLF!"), left behind in bank 0E. Recommend repointing dlg_172's CALL to
  orphan_0E_57BE (place it in the same bank). Text left as-is in merged.json (token rule); sub_06_57BE equals the dlg_135 tail.

## Task 4: voice / accuracy fixes
- dlg_1E2: kigen = kigen: "your time limit has run out" (was "too much danger").
- dlg_1CA: kyoushi = kyoushi: "surpassing me, your teacher" (was "mirror image").
- dlg_408: Forest Bear song (o jou san o nige nasai): "Run away, run away, little miss!" (was "Mr. Monk").
- dlg_427: "Call me Milady!"; dlg_034 C2 yelp "Hau?!"; dlg_1DE/1E0 Dorothy haughtier; 141, 209, 29D, 2BE, 3BC, 0AC smoothed.
- Yakko: the JP is mostly snooty-feminine (wayo/kashira) with Hakata outbursts only in 4E1/4F5/4FB/532 (+ 3AB). Kept her as a snooty rival
  with gruff outbursts in exactly those lines instead of slangifying all of her lines. Suzu stays earnest/polite (no de gozaru in this JP).
- `*action*` asterisks removed (not in the font): "Thud...", "Rip!", "Heh heh." etc.
- Report cards shortened for the measured boxes: dlg_006 "Visit Apple Class, not just Banana Class! Great at sea magic.", dlg_007 "Summons sea life.".

## Remaining uncertain lines
- dlg_180 (face 0D) "I've been spotted" vs "Found it!": speaker unidentified.
- dlg_3BD P.S. signed "Student Rep Mary" with the cat face (C1): unknown character.
- dlg_4D4 shinreisai (Marin news joke), dlg_472 Riiya's riddle answer, dlg_466 "<NICK2>, doggy time!" kept as translated.
- dlg_16F / 173 / 172 are only shown for specific pairs (Marin lead, etc.), as in JP.
- quest_1 "Get mushroom", quest_4 "Fetch water" kept (13/11-cell limits too short for "Fly Shroom"/"Holy Water" with a verb).

## Round 2 (playtest typography, 2026-11-22)
Edited merged.json in place (keeps main session's dlg_172 / dlg_557 edits; backup tmp/merged_before_r2.json).
`tools/fix_spacing.py` adds the missing space after WAIT/FACE/PAUSE groups where a sentence or ellipsis ends and a word follows
(opening ellipses and "Y...Yakko" stutters left alone) and hyphenates PAUSE-joined stutters. dlg_03B "taste awesome" -> "taste great" (fit).
validate_all.py treats dlg_172's inlined reply as intended. The main session's edits (dlg_172 inlined Riiya reply, dlg_557 "The End")
and the dlg_03B fit are in manual_edits.json, so the pipeline above reproduces the current merged.json exactly.
Changed: dlg_124 1B5 1F7 1FE 201 206 237 292 2A3 2AD 2FB 32A 373 381 400 442 453 466 474 03B 0AC 0B5 05C 066.
