# Akazukin Chacha (GB) - English engine: VWF, fonts, encoding, inserter

> **Repository note.** These notes were written in the original work tree, where `re/`, `engine/` and `ui/` each had
> their own `tools/`. In this repository the build tools are in `tools/re/`, `tools/engine/` and `tools/ui/`, and every
> generated file goes to `build/work/` (see the README). Screenshots, save states, test ROMs, extracted strings,
> captured graphics and the headless test harnesses referred to below are not published (they contain game data);
> everything the build needs is regenerated from your own ROM.

Tags: **[runtime]** seen in PyBoy, **[static]** from code/data, **[guess]**.
Base facts (encoding, pointer tables, LZ, print loop) are in [re-notes.md](re-notes.md); this file covers what the engine work changed.

## Build
```
python3 build.py --rom ORIG.gb                               # repo root: extract, engine build, UI build, BPS
python3 -I tools/engine/typeset_check.py                     # after a build: report + build/work/engine/shots/typeset/*.png
# engine step alone (paths from tools/common/paths.py: CHACHA_ROM, CHACHA_WORK, RGBDS_DIR):
CHACHA_ROM=ORIG.gb python3 -I tools/engine/build.py --tr build/work/tl/merged.json --out OUT_ENGINE.gb
```
- `build.py` options: `--tr FILE|DIR ...` (default tl/out), `--test overrides.json` ({id: en} applied last), `--placeholder`
  (untranslated dialogue becomes `[dlg_XXX]` + its control tokens instead of an error), `--layout PATH` (default tmp/layout.json).
- Output is deterministic (same input -> same md5). Exit code 1 only on missing translations (without --placeholder).
- `build.py` runs `make_font.py` (font assets) and `asm.py` (rgbds: `src/vwf.asm`, `src/defs.inc`) itself.

## Files
| path | what |
|---|---|
| `tools/fontdef.py` | the hand-drawn proportional font (original art, ASCII 20-7E + heart/note/drop) |
| `tools/make_font.py` | -> `font/glyphs.png` (sheet, red = advance), `vwf_glyphs.bin`, `vwf_widths.bin`, `font9000.bin` (tile block for $9000), `fixed.tbl`, `fixed8.png` |
| `src/vwf.asm`, `src/defs.inc` | VWF engine + bank-0 hooks (rgbds) |
| `tools/asm.py` | assemble + copy bank-0 patch ranges and the VWF bank |
| `tools/build.py` | encoder, line breaking, page splitting, placement, tables, patches, checksums |
| `tools/typeset_check.py` | typesetting checks + contact sheets |
| `tools/runtime_test.py`, `tests/test_strings.json` | headless tests |
| `tools/credits_test.py ROM TAG` | forces the ending (03:$5071) from the hallway, one frame per credits page -> shots/credits_TAG.png |
| `tools/ending_test.py`, `tools/ending2_test.py`, `tools/visit_test.py`, `tools/force_msg.py` | endings (copies of playtest tools; output to engine/shots; reset VWF WRAM after loading playtest states saved with older builds), force-print one message ID from a state |
| `tools/wram_scan.py` | free-WRAM finder (static refs + runtime sweeps) |
| `shots/` | `before_*` (original ROM) / `after_*` (test ROM) screenshots, `sheet_typewriter_after.png`, `typeset/` |

## 1. Text encoding (dialogue, nick/item/name tables)
- 20-7E = ASCII (glyph = code-20h), 80 = heart, 81 = note, 82 = drop, FF = space (game pads with FF). [static]
- Controls unchanged: EF END, F0 SCROLL, F1 SHAKE, F2 CLR, F3 WAIT, F4 NICK, F5 NICK2, F6 ITEM, F7 ITEM2, F8 NAMEC8D3, F9 xx FACE, FB lo hi CALL, FC PAUSE, FD PASSWORD, FE NL.
- Tokens in `en`: `<FACE:xx> <NL> <WAIT> <CLR> <SCROLL> <PAUSE> <END> <NICK> <NICK2> <ITEM> <ITEM2> <NAMEC8D3> <SHAKE> <PASSWORD> <CALL:$addr|id> <HEX:..> <HEART> <NOTE> {drop}`.
- Codes < 20h and 83-EE draw nothing (VWF ignores them).

## 2. Fixed 8x8 menu font (tilemap text, `font/fixed.tbl`, tile index = code)
- 00-3B: **VWF canvas** (never put fixed text here). 3C-55 `A-Z`, 56-6F `a-z`, 70 `?`, 71 `!`, 72 `-`, 73 `.`,
  74-7F original tiles (74 heart = WAIT cursor, 75 note, 76 drop, 77 cursor, 78-7F frame pieces), FF blank. [static, HUD runtime]
- Glyphs = VWF art emboldened 1 px and centred in the cell (matches the weight of the original kana).
- No digits / `,` `'` `:` in the fixed font (the original font had no digits either; HP is graphics). Unsupported chars -> blank + warning.
- Used by: cmd records ($1476, 5 bytes), `fixed` fields (battle menu rows, report card, password, game over, title), quest strings, item hand-slot names.

## 3. VWF engine [runtime: opening, scroll, CLR, B-replay, report card, names]
Bank-0 patches (all in `src/vwf.asm`):
| addr | was | now |
|---|---|---|
| `$3C46-$3C63` | bank-by-ID reader | table lookup: ptr 10:$4000+2*ID, bank 10:$4AB2+ID (same as RE insert.py), entry `$3C4B` kept for B-replay |
| `$3C64` MsgStartFlag / LineFlag | (free) | `wMsgStart=1`, then `wLineHi=0` -> next char starts a new VWF line (every message start) |
| `$3C6F` ScrollHook | (free) | LineFlag + `jp $3C7F` (the F0 jump-table entry at `$3C26` points here) |
| `$3C75` DualOff | (free) | `xor a / ld [CE97],a / ld [wDual],a / ret` |
| `$1ED0` | ending script end: `xor a / ld [CE97],a / ret` | `jp DualOff` |
| `$3C26` | jump table F0 -> $3C7F | -> ScrollHook |
| `$3D99` | `push af / ld hl,$C8CE` | `call ClrHook / nop` (box clear: also message start when C8D9 != 0, F2, B-replay) |
| `$3FD2-$3FEA` | put-char (tile index into tilemap) | trampoline: push bank 17h, `call VwfPutChar`, pop bank; ClrHook (wSlot=$FF) |
| `$3D6E` | `ld a,$0E` | `ld a,$10` (B-replay table bank) |
- `$3FD2` is called by the main text loop, the F4-F8 name printer ($3E17) and the password printer ($3F36): all three now go through the VWF. [static]
- VwfPutChar (17:$4000) preserves all registers. Algorithm:
  - New line when: wSlot=$FF (box cleared), wLineHi=0 (message start / scroll), or C8E8/9 != saved line start (NL moved the cursor).
    **C8E8 is no longer advanced per char**: it stays at the line start (only the text engine reads it [static: all refs in $3B5B-$3FFF]).
  - Canvas allocation: each line takes consecutive logical cells of its box's range, starting after the previous line's cells
    (`wBase` + cells used, wrapping inside the range). Logical 0-59 = tiles 00-3B, 60-87 = tiles 54-6F. [runtime]
    - **single** (normal): range 0-59. A box clear restarts at 0; lines (NL/SCROLL) advance. Report card: 3 messages (~57 cells)
      printed without clearing stay intact (its labels use 3C-71).
    - **dual** (two-box ending scenes: the ending script $1E9E prints alternately into the $9800 box at (4,1) and, with CE97=1,
      into the window box at (1,1)): turned on by a box clear while CE97=1. The $98xx box owns logical 0-43 (tiles 00-2B),
      the window box 44-87 (tiles 2C-3B + 54-6F). A clear / new page / scroll only recycles the box's own range, so the other
      box keeps its text however many messages or pages one box prints. [runtime: all 6 leads + time-up]
    - dual off: at the end of the ending script (`$1ED0`, which clears CE97, now `jp DualOff`), and at any message start
      without a box clear (report card / instant text, `wMsgStart`). [runtime incl. stale dual state on the report card]
    - build.py errors if any page (or any 4 visible rows of a scrolling page) of an ending message dlg_198-1CA / 1E3-1EB
      needs more than 44 cells (dlg_1E2, 47 cells, is printed before the first window box: warning only).
    - tiles 54-6F (fixed-font lowercase) are not displayed in field/ending scenes (UI layer: HUD = 3C-53) [UI NOTES + runtime].
  - Glyph: 8 rows 1bpp, advance from the widths table. Current cell kept in `wBuf` (WRAM), spill into `wRight`; both tiles rewritten in full (16 bytes each,
    colour 3 on 0) with a STAT mode-0/1 wait per row (2 writes per wait, ~10 M-cycles after the check, safe), tilemap entry written per touched cell (row wrap like $1F4A).
  - New line also runs `BlankRow`: the 15 tilemap cells from the line start (row-wrapped) that still show a canvas tile (00-3B) are set to $FF;
    frame/graphics tiles are left alone. Fixes stale tails when a box continues with <NL> and no <CLR> (credits dlg_54D/54F/550/552/554/555). [runtime: shots/credits_after_blank.png]
  - Clip: a glyph that would end past 120 px is dropped (inserter guarantees this never happens).
  - Typewriter: unchanged (per-char delay C8D9 in the main loop). Portrait upload, WAIT cursor (18,5), shake: untouched. [runtime]
- WRAM used: `$D3D0-$D3F0` (defs.inc; UI layer uses $D3B0-$D3BA). Never referenced by absolute address in the ROM and always 0 in runtime sweeps of the opening/hallway/menus [static + runtime];
  part of a 241-byte zero run after $D300/$D301 - an indexed buffer reaching it can't be fully excluded [guess]. Move = edit defs.inc.
- Font load: font block LZ at 17:$6000, `$2D6E` bank = 17h, `$2D7A` addr = $6000 (only the $9000 load; the $8000 OBJ copy still uses 03:$5976).
  03:$5F23 (0xC4 bytes, the $8800 load that runs with the same pushed bank) mirrored at 17:$5F23. [runtime]

## 4. Tables and banks
| bank | content |
|---|---|
| 10h | ptr table $4000 (0x559 x2), bank table $4AB2 (0x559), dialogue from $500B |
| 10h-14h | dialogue (all 7 batches: up to 14:$5FC4); 15h-16h free for growth (limit DLG_BANK_LAST=16h) |
| 17h | VWF code+font $4000-$453E, nick/item/name tables + strings $453E-~$4E01, item short-name table, $5F23 mirror, font LZ $6000 |
| 18h-1Fh | untouched (UI agent) |
- Name tables rebuilt in bank 17h, any length: `$3E0A`=17h (bank), nick `$3DD2/$3DE8`, item `$3DF4/$3DFC`, name `$3E04`. Slot->string mapping from strings.json `ptr_locs`. [runtime: NICK/NICK2/NAME/ITEM2]
- Hand slots / HUD (`$1434-$14E6`) belong to the UI layer (ui/tools/build_ui.py, bank 19h tiles); build.py no longer patches `$1496/$14A1` or writes a short-name table.
  Full chain: `ui/tools/build_all.sh` (engine build.py --tr edit/merged.json, then build_ui.py). UI also owns banks 18h-1Fh, WRAM $D3B0-$D3BA, `$2D86` FontHook, `$3F30`.
- FA handler (unused) still reads 0E:$5032 via the name printer's bank -> now bank 17h garbage; unused in the script. [static]
- Old dialogue spans in 06/07/08/0E filled with EF (free), old name tables in 0E unused.

## 5. Inserter layout rules (build.py)
- Box: 120 px x 4 rows; special boxes (`BOXSPEC`): report card comments dlg_000/002/.../00A 120x3, skills dlg_001/.../00B 104x1, dlg_00C (name) 48x1.
- Name slots measured at the widest table value (now nick 39 px, item 55, name 56) and never broken.
- Line breaking per paragraph (between hard breaks): minimum lines, then minimum squared slack (balanced), penalty for one stranded word on the last line.
  Breaks at spaces and after explicit hyphens. `<NL>` = hard break. Leading spaces after `<NL>` are kept (indent, credits); after `<SCROLL>` dropped.
- `<SCROLL>`: hard break; emitted as NL while the box has a free row, as F0 once the box is full (page then may exceed 4 rows: scroll mode).
- CALL (FB): callee laid out on its own; the caller continues from the callee's end (same line if it has no trailing NL; a space is inserted), rows counted across.
  A CALL after text on the same line: the callee's first row is measured from the current pen; if pen + space + first row > 120 px the line is broken
  before the CALL (dlg_0A3, the only case), else a space is added. Callers and callees are kept in one bank.
- Any row wider than its box or page over its rows is a build ERROR (exit 1).
- Page > 4 rows (no scroll): retry with pyphen en_US hyphenation (>= 3 letters each side); if still too long, split at the latest sentence end (then clause, then word)
  that makes page 1 fit, inserting WAIT (if not already there) + CLR; repeat. BOXSPEC strings are never split (reported).
- Current script: 0 splits, 0 hyphens, 0 overflowing lines; dlg_006 (4 rows, max 3) and dlg_007 (2 rows, max 1) too long for the report card.

## 6. Tests [runtime, `tools/runtime_test.py`]
- Test overrides (`tests/test_strings.json`) on the opening: dlg_167 long multi-box (auto-split x3 + CLR + NICK2), dlg_168 SCROLL (6 lines), dlg_17B NAMEC8D3 (C8D3 poked to 09) + ITEM2 (C8D5=0B) + symbols/digits.
- Shots: `after_wait01-10.png` / `before_wait01-10.png` (each WAIT), `sheet_typewriter_after.png` (every 24 frames), `after_hud_items.png` (C91E/C91D poked in the $1434 HUD init),
  `after_report.png` (SELECT), `after_replay_*.png` (B at WAIT replays the message).
- Checked by eye: spacing, descenders (g j p q y), portrait intact, WAIT heart, no garbage tiles in the dialogue box, scroll moves lines up and reuses tiles cleanly.
- Not reached: a real enemy encounter (the HUD "battle window" is permanent; Magic/Run/Left/Right + item slots verified there), an item list menu (none found; items show in the HUD and via ITEM2 in dialogue).

## Known issues / open
- **Report card labels** (onamae/reberu/keikenchi/tokugi/shusseki/... from 0E:$5022-$506F and layout data) still use kana tile codes; codes 00-3B now hit the VWF canvas -> garbage. UI agent: re-letter with fixed.tbl codes (3C-73, FF).
- Same for any other screen that writes kana tile codes directly (password grid, title, game over beyond the inserted fields): only codes 3C-7F/FF are safe.
- PASSWORD (FD) prints CE60 (kana tile codes from the encoder $1FF5) through the VWF -> wrong glyphs. Needs a password charset remap (UI/password work).
- Other $9000 loads (02:$467C 0x800 via $2DCD, 02:$7C8A 0x150) not traced: if a text scene uses them, the VWF canvas there is untested.
- dlg_006/dlg_007: translation too long for the report card boxes (shorten).
- Line pitch is 8 px: descenders touch the next line's capitals (no leading available in 4 rows).
