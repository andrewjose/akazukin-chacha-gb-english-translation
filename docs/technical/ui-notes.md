# Akazukin Chacha (GB) - UI layer (screens, labels, password, title)

> **Repository note.** These notes were written in the original work tree, where `re/`, `engine/` and `ui/` each had
> their own `tools/`. In this repository the build tools are in `tools/re/`, `tools/engine/` and `tools/ui/`, and every
> generated file goes to `build/work/` (see the README). Screenshots, save states, test ROMs, extracted strings,
> captured graphics and the headless test harnesses referred to below are not published (they contain game data);
> everything the build needs is regenerated from your own ROM.

Tags: **[runtime]** seen in PyBoy, **[static]** from code/data, **[guess]**.
Engine facts (VWF, canvas 00-3B, encoding) are in [engine-notes.md](engine-notes.md); RE facts in [re-notes.md](re-notes.md).

## Build
```
python3 build.py --rom ORIG.gb        # repo root: engine build -> build/work/engine/chacha_en_text.gb, then -> build/chacha_en.gb
# or by hand (CHACHA_ROM / CHACHA_WORK / RGBDS_DIR in the environment, see tools/common/paths.py):
python3 -I tools/engine/build.py --tr build/work/tl/merged.json --out OUT_ENGINE.gb
python3 -I tools/ui/build_ui.py OUT_ENGINE.gb OUT.gb --tr build/work/tl/merged.json
```
- `build_ui.py IN OUT [--tr merged.json]`: input must be the engine build (512 KB, banks 18h-1Fh empty - asserted).
  Every byte changed outside 18h-1Fh is asserted against the original / engine value first. Deterministic.
- Tests / shots (all headless PyBoy):
  - `python3 tools/shots_ui.py ROM TAG [--reach]` -> `tmp/sh/TAG_*.png` (HUD, HUD with items, report card, results pass/fail, game over, title, password).
  - `python3 tmp/t_pwtest.py ROM TAG` -> password round trip (encode at runtime, show via FD, type it on the entry screen, load, compare WRAM). Prints MATCH.
  - `python3 tmp/t_pwerr.py ROM TAG` -> wrong password error + redraw. `tmp/t_cred.py` credits, `tmp/t_open.py` opening sheet.
  - `python3 tools/triptych.py NAMES...` -> `shots/NAME.png` = original | engine build | UI build.
  - `tools/force.py`: force-calls a routine from the main thread (hook at `$026D`, after the VBlank wait) - how the results /
    game over / credits / world map screens were reached without playing to them.

## Files
| path | what |
|---|---|
| `src/ui.asm`, `src/ui_defs.inc` | bank-0 patches + UI bank 18h code (rgbds) |
| `tools/build_ui.py` | label layout, layout-tilemap edits, data generation (`tmp/gen/data.asm` + blobs), assemble, patch, checksums |
| `tools/ptext.py` | label renderer: engine VWF font (`engine/tools/fontdef.py`), bold = 1 px emboldening like the menu font; `big_tiles` = 16 px rank text (DejaVu Sans Condensed Bold 13, 1-bit) |
| `tools/stamps.py` | results stamps "Well done!" / "Try again" (original ring kept) |
| `tools/logo.py` | title logo "Akazukin ChaCha" (128x24, DejaVu Sans Condensed Bold, downsampled + outline/shadow) |
| `tools/sgb_border.py` | renders the SGB border (bank 0D) to PNG |
| `tools/xref.py`, `tools/findlists.py`, `tools/trace.py`, `tools/kana.py` | RE helpers (call/ld refs, $04A2 blit lists, call tracing, kana decode) |
| `COVERAGE.md` | screen list |
| `shots/` | before/after triptychs + sheets |

## Design [static, all screens runtime-checked]
- **No fixed 8x8 letters anywhere any more.** Every label is precomposed at build time into word tiles (proportional, bold)
  and copied to VRAM at runtime by `Blit` (bank 18h): record = `bank, src, vram, ntiles, tile0, map (0 = none), cols`.
  Copy: STAT mode 0/1 wait per 2 bytes (same budget as the engine). The copy loop is in bank 0 (`CopyTiles`) because the data sits
  in banks 19h+ (switching banks under code running in 18h crashed - first build).
- Static labels: the tile ids are written into the ROM layout tilemaps; dynamic slots (hand items, cmd, rank word, rank, quest)
  write the tilemap at runtime.
- Far calls: bank-0 stubs `ld a,ID / jr FarDispatch`; `FarDispatch` stores the id in `wFarId`, pushes bank 18h ($02B2),
  calls `UiEntry` (18:$4000, jump table via `jp wJmp` in WRAM, hl preserved), pops ($02D4). A is clobbered by stubs.
- WRAM: `$D3B0-$D3BA` (wFarId, wJmp x3, wBank, wN, wT0, wMapLo/Hi, wCols, wNoMap) - same never-referenced zero run
  `$D302-$D3F2` the engine uses ($D3D0-$D3EB) [static + runtime sweep; guess that nothing indexes into it].

### Bank-0 changes
| addr | was | now |
|---|---|---|
| `$1434-$14E6` | HUD init + cmd records $1476 + hand-slot printer $1494 (HUD-only; engine had patched $1496/$14A1 in it) | `HudInit` (entry kept at $1434), `FarDispatch`, 11 stubs, `FontHook`, `RepExit`, `CopyTiles`; free `$14A6-$14E6` |
| `$14E7` | HUD blit list | unchanged (asserted) |
| `$1913` | `ld hl,$1A83 / call $04A2` (report card layout) | `call Stub_Report` + 3 nop |
| `$196E` | `call $32BC` (rank word copy, de=$1A8C+6k) | `call Stub_RankWord` |
| `$1A00` | `ld a,4 / ld [$C8D9],a / ret` (report card exit) | `jp RepExit` (same + re-blit HUD tiles) |
| `$1A06-$1A3B` | rank kanji hatsu/go..ichi/toku (2x2 tiles B2+4*C916 at $988D) | `call FarDispatch(ID_RANK) / jr $1A3C`; free `$1A0D-$1A3B` |
| `$2D86` | `ld bc,$100 / ld de,$5F23 / ld hl,$8800 / jr $2DFB` (2nd half of the font load) | `jp FontHook` (same load, pop, then re-blit HUD tiles) |
| `$2D92`, `$2D9E` | OBJ font copy (title sprites) bank 03 / $5976 | bank 18h / `ObjFontLZ` |
| `$3F30` | FD printer loop (`ld b,$0E / ld hl,$CE60 ...`) | `jp Stub_PwPrint` |

### Other banks
| addr | change |
|---|---|
| 02:$7812 (HUD 20x6) | rows 3-4 label cells blanked; "Run" tile ids |
| 02:$520B (report card 20x18) | rows 1,3,4,5,7,9,11,13 re-lettered (deco -◯- moved to cols 2-4 / 15-17) |
| 02:$7902 (results 20x18) | rows 1,3,4,5,7,8,9,11,13,15 re-lettered (◯ moved to cols 2 / 17) |
| 02:$7A6A / 02:$7B6A | results stamps (256 B raw each) redrawn: "Well done!" / "Try again" |
| 03:$4E24, $4E61, $4F25 | `call Stub_Result` (after $2DA5), `call Stub_Quest`, `call Stub_GameOver` |
| 03:$6961 (password 20x18) | title row (◯ -> tile 5F copy), "End" tile ids at row 16 cols 13-15 |
| 04:$423A | `call Stub_Title` (after the OBJ font copy: logo + copyright tiles) |
| 04:$4439, $451D, $4526, $453C | `call Stub_PwInit` (before $0316), `call Stub_PwErr`, 3x nop, `call Stub_PwErrDone` |
| 04:$4B33 | title menu sprite codes 00-0B (OBJ word tiles) |
| 18h | code, records, tables, PwXlat, ObjFontLZ |
| 19h-1Ah | tile blobs (~15 KB) |

## Screens
### HUD (window $9C00, all field/dungeon scenes) [runtime]
- Tiles **3C-53**: cmd label 3C-40 (5 cells, $9C62, by C915 partner: Magic/Rush/Morph/Pot/Brew/Ninja), "Run" 41-43 (static),
  left hand 44-4B ($9C82, C91E), right hand 4C-53 ($9C8B, C91D). Item names: full English name if <= 64 px bold, else `short8`
  (only "Angry Anchor" -> "Anchor"). Empty hand ($FF) -> "Left"/"Right".
- **The game reloads the font after drawing the HUD** (hall scene: $1434 then $2D6D) [runtime], and the report card reuses
  3C-71 without redrawing the HUD on exit. Hence `FontHook` (every $2D6D) and `RepExit` re-blit the HUD tiles (no tilemap writes).
  Consequence: tiles 3C-53 hold HUD words after every font load; any screen that still used fixed letters there would show
  HUD pieces (none left that I know of).

### Report card (SELECT; bank 0 $18FB-$1A05) [runtime]
- Layout 02:$520B via list $1A83. Pool **3C-71** (canvas 00-3B = VWF comment/skill/name; 72/73/74 = deco/gauge).
  Labels: "Report Card", Name, Rank, EXP, Skill, "Days left" (digit tile D2+n at $9970 kept), "To Parents".
  Gauge dot 73 = original . glyph uploaded on this screen (engine '.' looked like a dash).
- Rank word ($98ED, 6 cells, tiles from the pool): Poor / So-so / Almost / Close (thresholds 19h/32h/4Bh unchanged).
- Rank (C916 0-6): shokyuu go kyuu yonkyuu sankyuu ni kyuu ikkyuu tokkyuu -> **Novice, Grade 5..Grade 1, Special**: 16 px text, 7x2 cells at $988C,
  tiles B2-BF (the old kanji tiles; kyuu CE-D1 no longer shown). Same routine on the results screen.

### Results / end of day (03:$4E0E, layout 02:$7902, list 03:$4F58) [runtime via force-call]
- "Exam Results", Name, Rank, "Days left" + digit ($990E), "Task:", quest goal (16 cells $9942, tiles C0-CF; uses the long
  `alt_long` wording from tl/out: "Bring back the Holy Cup" ...), "Your score:", score digits ($99A7, kept) + "points", "Urara" + seal.
- Stamp: 02:$7A6A (score >= 32h: yokudekimashita -> "Well done!") / 02:$7B6A (ganbarimashou -> "Try again").
- 03:$4EF8-$4F15 (after the key press: 2 tiles from table 03:$4F42 to $9909) not identified; the screen is cleared and the game
  moves on immediately in my force-call [runtime]; codes look like kana pairs [guess: unused/debug]. Not changed.

### Game over (03:$4F16) [runtime via force-call]
- "GAME OVER" centred in the original 10 cells at $9905 (tiles 3C-45).

### Password ("Diary Spell") [runtime: round trip verified]
- Internal codes unchanged: the encoder `$1FF5` maps 6-bit values through 00:$22A3 (00-36, 70-77, 7B); the entry screen reads the
  code **from the BG tile under the cursor** (04:$481A) and decodes via $22E8. So only glyphs change:
  - entry screen: tiles 00-36 get Latin glyphs, 77 '>', 7B '*' (70-76 keep ? ! - . ♡ ♪ drop); letters assigned in grid reading order:
    `ABCDE FGHIJ KLMNO / PQRST UVWXY Z3467 / 9abd e f g hijkm / n q r ty#%& + = $</` (digits 0 1 2 5 8 and @ left out:
    they read like O I Z S B / 0 in an 8 px bold font).
    Full table: `tmp/pw_alphabet.json`.
  - FD in dialogue: `DoPwPrint` translates CE60 through `PwXlat` (same table; ♡♪drop -> VWF 80/81/82) and prints via $3FD2.
- Screen tiles: portraits use 40-4E, 50-5E, E0-EE (animation frames); labels: "Diary Spell" 37-3E, "End" 60-62 (same cells as owari,
  the end action is by cursor position), ◯ deco copied to 5F. Error rows (window $9D01/$9D41, regular weight to fit): 37-3F + 63-6C;
  the title is re-blitted after the error (`DoPwErrDone`).
- Runtime test: state C8FC=3, C8FD=2, C916=1, C928=45 -> CE60 `18 20 11 2D FF 08 09 7B 7B FF 00 30 35 00` -> FD shows
  `YbRt IJ** A%<A` -> typed on the grid by cursor+A -> loads with identical WRAM (MATCH) [runtime]. Re-run after any change: `python3 tmp/t_pwtest.py out.gb ui`.

### Title [runtime]
- Menu = 12 OBJ sprites (04:$4240: 2 rows x 6, x=$40.., codes from 04:$4B33) using the OBJ font copy ($2D91 -> $8000).
  The copy now comes from `ObjFontLZ` (original font + "New Game" / "Continue" word tiles at 00-0B). The translations say
  Start/Resume; with proportional tiles the standard "New Game"/"Continue" fit (alt_long) - change `UIT['new'/'cont']` to revert.
- Logo (tiles 50-7F, loaded from 03:$5FE7 -> $9500) replaced after load by "Akazukin ChaCha" (Akazukin dark, ChaCha light, black outline).
- Copyright row 14 (was ©ayahana min/shuueisha .terebi toukyou .NAS): "©Min Ayahana/Shueisha/TV Tokyo/NAS" in tiles 00-13 (font canvas is
  unused on the title), cols 0-19. "©TOMY 1995" unchanged.

### Alternate $9000 loads [runtime via force-call]
- 02:$467C (+02:$4DFF -> $8800) via $2DCD (00:$17FA, 08:$401B): **world map** graphics (full 128 tiles, no text). Map tilemap 02:$4EED.
  No dialogue on that screen seen; if a scene printed text there it would be broken in the original too.
- 02:$7C8A (0x150 -> tiles 00-14) via $2DB9 (01:$4830): **dungeon automap** pieces (lines, icons). No text. (In the original the HUD
  kana there are corrupted because they share tiles 00-14; the English HUD uses 3C-53 and stays intact.)

### SGB border (bank 0D: CHR 0D:$4000/$5000, map 0D:$6000, palettes 0D:$6800) [static render: tools/sgb_border.py]
- Contains Japanese: top logo aka zukin chacha, left panel ad (ribon masukottokomikkusu / RMC / hatsubaichuu / vertical title / ayahana min / nedan 390-),
  "hoora♪", "bau bau". All 256 border tiles are used; text tiles are unique (editable in place), the sky tile 4B is shared.
- `tools/sgb_en.py` (called by build_ui, asserts bank 0D untouched before): logo -> "Akazukin ChaCha" (red/green, palette 1;
  the tiny ribon masukottokomikkusu line is removed and its 7 tiles give the logo's 3 shared sky cells + the cloud cell (26,1)
  their own tiles), hatsubaichuu -> "On sale!", vertical title -> rotated "Akazukin ChaCha", ayahana min -> rotated "Min / Ayahana",
  nedan -> "Price", hoora♪ -> "Look! ♪", bau bau -> "Arf" "arf". Map entries changed: (0-6,1) -> 4B, (18,1) (21,1) (25,1) (26,1).
  [static only: PyBoy has no SGB; render `python3 tools/sgb_border.py ROM out.png`, shots/sgb_border_en.png]

### Other
- 0E:$5022-$506F (shiine/marin/yakko/orin/reberu/tairyoku/keikenchi/...): only referenced by the broken FA handler ($3F00) [static] -> unused.
- No shops in the game (dlg_028 jokes about it); the appraiser is dialogue.
- Credits (03:$5071) are dialogue (dlg_54B-558) -> VWF; see ENGINE_REQUESTS.md for leftover cells.

## Playtest round 2 (other leads' ending art) [runtime, shots/r2_endings_ui.png]
- Pictures are found from their records (bank 0B): after bank/len/src, commands `00|01 msgid` (text on map 0/1) and
  `xx ptr` = 6x20 tilemap in the record's bank, blitted at $98C0 by $1F36. `sfx_art.record_tilemaps()` reads them,
  so no runtime tilemap capture is needed. The tile data was first captured at runtime from the load hook ($1E5F/$1E62),
  because the streams back-reference VRAM before $8900; those back-references only ever read zeros, so the build now
  decompresses each stream straight from the ROM with a 0x900-byte zero prefix (`lz2.decompress(rom, off, len, bytes(0x900))`),
  which reproduces the captures byte for byte. Nothing captured is stored in the repository.
- 0D:72E2 (Shiine, record 0B:7E73): yokuyattazo! -> "Well done!" (regular, 2 px spaces), vertical chikushoo -> rotated "Dang it!".
- 0C:6865 (ChaCha, 0B:7F15): shuumai -> "Pastries!" (DejaVu Cond. Bold 11, heart kept), hautsu -> "Oof!" (small heart kept).
- 06:775E (Suzu, also seen in Marin's run, 0B:7F90): po -> grey "///" blush hatching (the -♥ to the right is kept).
- 0C:76CC (Marin, 0B:7F63): gyoe ~ -> "Gyaaah" (12 px, white outline; the ~ ~ ~! swoosh is kept); the small vertical
  todo ga ("the walrus...") is removed (no room for a readable English word in 8x20 px).
- All recompressed in place (the new streams are smaller); records are unchanged.

## Holy Falls sign (playtest round 3) [runtime: shots/falls_sign.png, falls_scene_ui.png]
- Side-view falls scene (Magic Forest room 13,3; B > Down > A with the Straw Cup): the small sign next to the spring is a
  2-sprite 8x16 OBJ pair (tiles 48-4B, OBP0), loaded from LZ stream 0B:6D3D (0x40 bytes, 57 compressed) at $8480.
- taki ("falls") cannot be lettered legibly on the 6x10 px board face -> water-drop mark (colour 3, highlight colour 1);
  board frame and right shading kept. Recompressed in place (50 bytes). Test: tmp/t_falls.py ROM TAG 300.
