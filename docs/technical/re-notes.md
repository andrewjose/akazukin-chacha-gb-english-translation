# Akazukin Chacha (GB, J) - reverse-engineering notes

> **Repository note.** These notes were written in the original work tree, where `re/`, `engine/` and `ui/` each had
> their own `tools/`. In this repository the build tools are in `tools/re/`, `tools/engine/` and `tools/ui/`, and every
> generated file goes to `build/work/` (see the README). Screenshots, save states, test ROMs, extracted strings,
> captured graphics and the headless test harnesses referred to below are not published (they contain game data);
> everything the build needs is regenerated from your own ROM.

ROM: `Akazukin Chacha (Japan) (SGB Enhanced).gb`, CRC32 898609B4, MD5 9a5215658c60a1802b11f728c292b536.
Header: cart type 0x03 (MBC1+RAM+BATT flag, but 0x149 = 00, no SRAM), 0x148 = 03 (256 KB, 16 banks).

Tags: **[runtime]** = confirmed at runtime in pyboy; **[static]** = from disassembly/data; **[guess]**.
Addresses are `bank:$cpu` (file offset = bank*0x4000 + cpu-0x4000; bank 0 = cpu).

## Files
| path | what |
|---|---|
| `chacha.tbl` | full table + control codes |
| `strings.json`, `all_strings.csv` | every known string (1477 records) |
| `font_sheet.png` | decompressed font, codes 00-7F (+ the $8800 block, partly garbage without its VRAM prefix) |
| `freespace.txt`, `freespace_expanded_after_repack.txt` | free-space maps |
| `render_test/` | English render test: `before.png` / `after.png` / `compare.png` (top = original, bottom = test), test ROM, `eng_test.tbl`, `tr_test.json`, `expand_bank13_runtime.png` |
| `font/latin5x7.txt` | hand-made 5x7 Latin test glyphs |
| `tools/` | every script (below) |

Tools: `sm83dis.py` (SM83 disassembler), `hexdec.py` (hex + table dump), `tbl.py`/`chacha_common.py`/`make_tbl.py`,
`extract.py`, `insert.py`, `roundtrip_test.py`, `lz.py` (decompressor **and** compatible compressor),
`font_sheet.py`, `build_test_font.py`, `render_test.py`, `scan_text.py` (finds untabled kana text),
`freespace.py`, `trace_lz.py` (logs every LZ load at runtime), `emu.py` (pyboy helpers), `cmp_expand_runtime.py`, `dump_vram_sheets.py`.
Run everything with `python3 -I tools/<x>.py`.

## 1. Encoding (chacha.tbl)
- Code = BG tile index; LCDC = $E7 in dialogue (BG/window use $8800 signed mode), so codes 00-7F are the font
  tiles at $9000-$97FF. **[runtime]** (tilemap dump of the first dialogue page vs. ROM bytes).
- Proof: on-screen soredeha / mazuha paatonaa wo read from the tilemap as `0E 29 12 6E 19` / `1E 0C 6E 19 FF 50 6F 72 4A 4B 72 2C`;
  found in ROM at 0x1A288 / 0x1A28E **[runtime + static]**. All 1314 dialogue strings then decode with **zero unknown bytes** **[static]**.
- Layout: hiragana 00-2D (a..wawon gojuon), small aiueotsuyayuyo 2E-36, katakana 37-64 (a..wawon), small a..yo 65-6D,
  " 6E, ? 6F, ? 70, ! 71, - 72, . 73, ♡ 74, ♪ 75, drop 76, ▶ 77, frame/diamond tiles 78-7A, ○ 7B, frame pieces 7C-7F, FF = space (blank tile).
- **Dakuten/handakuten are separate characters in the next cell** (ga = `05 6E`, pa = `50 6F`). [runtime]
- 8E/8F = saki/nama (kanji tiles at $88E0/$88F0, present in the dialogue scene's VRAM, not in the font LZ). [runtime for that scene; guess elsewhere]
- **No digits and no Latin letters exist in the font.** Only "HP"/"DI" pieces in scene graphics. [runtime VRAM + static font]
- Control codes EF-FE (jump table $00:3C24) [static, usage counts from the full decode]:

| code | tag | args | meaning | uses |
|---|---|---|---|---|
| EF | END | 0 | end of string / return from FB | 1452 |
| F0 | SCROLL | 0 | copy rows 2-4 up, clear row 4, cursor to row 4 | 72 |
| F1 | SHAKE | 0 | screen shake | 0 |
| F2 | CLR | 0 | clear the 4 rows, cursor home | 275 |
| F3 | WAIT | 0 | wait for key, blinking ♡ (tile 74) at map (18,5); B (if C8FA=0) clears and replays the current message ID | 1586 |
| F4 / F5 | NICK / NICK2 | 0 | nickname string 0E:$4AB2[CE41*6 + C8D2/C8D1] | 16 / 108 |
| F6 / F7 | ITEM / ITEM2 | 0 | item name 0E:$4BD1[C8D4/C8D5] | 0 / 28 |
| F8 | NAMEC8D3 | 0 | enemy/char name 0E:$4C51[C8D3] | 33 |
| F9 xx | FACE | 1 | portrait: low nibble = face (0E/0F substituted from C915/C924), high nibble = expression; FF = no change; uploads 9 tiles to $8F50/$8F80/$8FB0 (3x3 portrait, tiles F5-FD) from table 04:$4B48 | 1415 |
| FA | FA | 0 | reads "pointer" from 0E:$5032[C8D6] - that is string data, so code is unused/broken | 0 |
| FB lo hi | CALL | 2 | call sub-string at addr **in the same bank** (nest counter C8D7) | 86 |
| FC | PAUSE | 0 | wait 32 frames | 1154 |
| FD | PASSWORD | 0 | encode state ($00:1FF5) and print 14 chars from CE60 | 2 |
| FE | NL | 0 | next row | 2107 |

Name strings (F4-F8 targets) are printed **raw** until EF by $00:3E17 (no control processing). [static]

## 2. Text blocks / pointer tables
| block | where (ptr table) | entries | strings at | pointer format | notes |
|---|---|---|---|---|---|
| dlg (master) | 0E:$4000-$4AB1 (file 0x38000) | 0x559 = 1369 IDs (1314 unique + 1 FB-only sub-string; 193 aliases) | IDs 000-0DD: 0E:$5070-$7586; 0DE-1EC: 06:$4000-$775D; 1ED-318: 07:$60D5-$7AE0; 319-558: 08:$4121-$7CB3 | LE16, bank implied by ID range | [static]; bank rule [runtime confirmed for 06 range, rest static] |
| nick | 0E:$4AB2 | 72 ptrs (12 speakers x 6) -> 24 unique | 0E:$4B42-$4BD0 | LE16 | raw, EF-terminated |
| item | 0E:$4BD1 | 64 | 0E:$4CBD-$4E94 | LE16 | also printed by $00:1495 into battle hand slots ($9C82 / $9C8B) |
| name (enemies + chars) | 0E:$4C51 | 54 (50 unique) | 0E:$4E95-$5021 (+ nick strings) | LE16 | |
| quest goals | 03:$4F7B | 6 | 03:$4F8D-$4FDB | LE16 | raw EF strings, printer not traced [static] |
| cmd | none (index*5) | 6 | 00:$1476 | fixed 5-byte records | battle special command (mahou/totsugeki/henshin/tsubo/kusuri/ninpou), copied to $9C62 [static] |
| fixed UI | - | 11 | see strings.json `fixed` | in tilemap/layout data | battle command window (02:$784F/$7863 raw 20-wide tilemap), title menu (04:$4B33/$4B39), password screen (03:$69B4, 04:$460F), report card (02:$5224/$5311/$7A2F), game over (03:$4F41), rank words (00:$1A8B) - in-place only |
| orphan | - | 2 | 06:$7451, 0E:$57BE | - | EF-terminated dialogue with no pointer (unused?) |

Stats text in bank 0E $5022-$506F (shiine/marin/.../reberu/tairyoku/keikenchi/kougekiryoku/konjou/subayasa/...) has no pointer found yet (status screen) - **open**.

### Counts (strings / JP chars excl. " ? and controls / bytes)
| block | strings | jp chars | bytes |
|---|---|---|---|
| dlg | 1314 | 30670 | 45532 |
| item | 64 | 373 | 472 |
| name | 50 | 308 | 397 |
| nick | 24 | 113 | 138 |
| quest | 6 | 68 | 79 |
| fixed | 11 | 125 | 189 |
| cmd | 6 | 20 | 30 |
| orphan | 2 | 32 | 48 |
| **total** | **1477** | **31709** | **46885** |

### How the reader selects banks [static, hook verified at runtime]
`$00:3B5B` (32 callers; bc = message ID, d,e = box x,y) -> `$00:3C46`: push bank 0E (bank stack $FF92-$FF98, 7 deep, `$02B2` push / `$02D4` pop),
read ptr from 0E:$4000+2*ID, then IDs >= 0xDE pop 0E and push 06 (>=0x1ED: 07, >=0x319: 08). Text pointer lives in C8E6/7,
cursor (tilemap addr) in C8E8/9, box origin in C8CE/F. FB calls never switch bank, so a callee must sit in the caller's bank.
`$00:3D6D` (B-replay inside WAIT) pushes 0E and calls `$3C4B` (mid-entry).

## 3. extract / insert
- `tools/extract.py` -> `strings.json` (fields: id, block, bank, addr, ptr_locs (file offsets), off, raw_hex, jp, max_bytes (incl. EF), ctx, aliases, calls, fixed, encoding, inside/contains) and `all_strings.csv`.
- `tools/insert.py OUT.gb --tr tr.json [--tbl X.tbl] [--expand]`: text uses the table (longest match, so DTE entries work) + tags (`<NL>`, `<WAIT>`, `<FACE:xx>`, `<CALL:dlg_XXX>` or `<CALL:$addr>`, `<HEX:..>`, or `hex:` prefix).
  - default mode: in place if it fits, else moved into space freed by other moved strings **in the same bank**; FB targets are re-resolved; strings nested inside a changed string get relocated. Fixed fields are padded with FF.
  - `--expand`: 512 KB, all master-table dialogue repacked into banks 10h+ (groups linked by CALL kept in one bank), new pointer table 10:$4000 + per-ID bank table 10:$4AB2, `$00:3C46` replaced by a 31-byte table lookup, `$00:3D6E` = 10h; the old dialogue spans (~45 KB in banks 0E/06/07/08) are filled with EF and become free. Name tables still in-place (extend if English names overflow; option: move tables and patch the bank byte at `$00:3E0A` and `$00:1496`).
  - header + global checksums fixed whenever the output differs.
- **Round trip PASS**: `tools/roundtrip_test.py` re-encodes all 1477 strings from their `jp` text through `chacha.tbl` and rebuilds -> md5 9a5215658c60a1802b11f728c292b536 (byte-identical). [static]
- **Expanded repack verified at runtime**: original Japanese repacked into banks 10-13 gives pixel-identical screenshots at 15 points of the opening (old spans wiped), and a string placed in bank 13 renders correctly (`render_test/expand_bank13_runtime.png`). Bank usage after repack: 10h-12h full, 13h 576 bytes; 13h-1Fh free (~207 KB).

## 4. Font and print routine
- Font: **LZ-compressed** at 03:$5976 (file 0xD976, 1451 bytes) -> $9000, 0x800 bytes (codes 00-7F), loaded by `$00:2D6D`. Then 03:$5F23 (166 bytes) -> $8800 (0x100). [runtime: decompressed output == VRAM]
- The same font stream is also decompressed to $8000 (OBJ copy, `$00:2D91`, title screen), and **other LZ streams back-reference VRAM before their destination** (03:$5F23 ->$8800, 03:$6378 ->$8900). Do not edit 03:$5976 in place; add a new stream and repoint only the $9000 load (`$00:2D6E` bank, `$00:2D7A` addr), mirror 03:$5F23 into the new bank (the $8800 load runs with the same pushed bank). That is what the render test does. [runtime]
- Title screen loads 03:$5FE7 -> $9500 (tiles 50-7F replaced while on the title), the font is reloaded at the start of the game. [runtime, trace_lz.py]
- LZ format (`$00:2AD5`, see lz.py docstring): 00-7F back-ref len (c>>2)+2, disp ((c&3)-4)<<8|next (-1..-1024, may reach before dest); 80-9F literal (c&1F)+1; A0-BF zero (c&1F)+1; C0-DF RLE (c&1F)+2; E0-FE zero (c&1F)+1; E0|1F extended zero (next+0x20)&FF; `7F FF` end; stops after bc bytes. **Counts are 8-bit** (a 255+ zero run corrupts). Writes go straight to VRAM with a STAT mode-0/1 wait per byte; state in CE50-CE53 allows resuming. `lz.compress()` is compatible and round-trips (font: 1435 bytes vs 1451 original). [static + runtime]
- Glyph style: 2bpp, ink colour 3 with a colour-1 shade; 8x8 cells, glyph ~7x7.
- Print routine: `$00:3BB2` loop: `a=[hl+]` from C8E6; `a<EF` or `a==FF` -> `$3FD2` writes `a` as the tile index to the tilemap address in C8E8 (via `$1F4A`, STAT wait) and increments; EF-FE -> handler. No WRAM shadow buffer: **text goes directly into the BG/window tilemap** ($9800, or $9C00 if CE97/C940 set) **at text time, not in VBlank**. Per-char delay C8D9 frames (A/B skips). [static; tilemap result runtime]
- Box: text origin (4,1) on $9800 in the opening scene, **15 cells x 4 lines**, portrait 3x3 at (1,1). Clear/scroll widths are hard-coded 15 (`ld c,$0F` at $3CAA/$3CD4), 4 rows ($3C88, $3DA3). Wait cursor at (18,5). No auto-wrap: lines are explicit FE; pages = F2 (clear) / F0 (scroll). Max JP line = 15 cells. [static + runtime]

## 5. VWF verdict: feasible, but tile budget is tight; recommended with 512 KB expansion
- Tiles: BG can only address $8800-$97FF. 80-FF ($8800-$8FFF) hold scene graphics, the 3x3 portrait (F5-FD) and frames; only 00-7F (font) are ours. 70-7F hold ?!- .♡ and window-frame tiles, which stay. So **112 tiles (00-6F)** are available.
- A 15x4 box needs **60 canvas tiles** (fixed mapping cell (r,c) -> tile 00+r*15+c, or a 4-row ring so F0 scroll can keep copying tile *indices* as it does now and the scrolled-off row's tiles become the new bottom row).
- That leaves **52 tiles** for fixed 8x8 glyphs used by menus/tilemaps that are on screen at the same time as dialogue (battle window shows mahou/nigeru/hidarite/migite, item names via `$00:1495`, HP). Fits uppercase A-Z + 0-9 + ~16 punctuation/specials, or pre-rendered menu words.
- Upload timing is not a problem: the engine already writes tiles outside VBlank with STAT polling (portrait upload of 0x90 bytes mid-text, `$3EE8`). A VWF char costs ~32 bytes of VRAM writes.
- Hook points: `$3FD2` (put char; also used by F4-F8 name printing, so names get VWF for free), `$3C7F` (F0 scroll), `$3D99`/`$3CD2` (clear: must also clear canvas tile data), `$3CFB` (WAIT cursor unaffected). Code goes in an expanded bank; bank-0 trampolines fit in the 25 bytes freed at `$3C65-$3C7D` by the new `$3C46`. Bank 0 has no other confirmed free space (`$0F7C-$0FD5` zeros are next to SGB packet data - unverified).
- Width: 120 px per line -> ~22-26 English chars with a 4-5 px average font, vs 15 with 8x8.
- **Plan**: (1) expand to 512 KB (done in insert.py); (2) new font stream: fixed glyph set in 3C-6F, canvas 00-3B; (3) VWF routine (~150 lines SM83, rgbds now available) in bank 1F with a widths table; (4) patch F0/F2/clear to handle canvas data; (5) re-letter the tilemap menus with the fixed glyph set; (6) wrapper in insert.py using the same widths table.
- **Fallback (no VWF)**: 8x8 English font in 00-6D (all 112 slots), plus ~40 bigram tiles ("th", "he", "in", "er", "an", ...) or narrow letter-pair tiles ("il", "li", "ll", ...). 15 chars/line is very cramped; expect ~1.6x more pages.
- Free tile slots today: none inside 00-7F (all used by kana/symbols); in English, 00-6F become free (only 6E/6F dakuten goes away).

## 6. Free space
- Original 256 KB: essentially **no free space**. Banks 1-4, 6-F: 0 runs >= 64 bytes; bank 0: 90 zeros at $0F7C (maybe SGB data) + FF runs at $1109-$12B4 (tilemap data, not free); bank 5: 180 zeros at $4178 (unverified). See `freespace.txt`.
- 0x148 -> 04 (512 KB) works: MBC1 5-bit bank register covers banks 1-31, the game only writes the bank to $3FFF (`$02B2`/`$02D4`), no writes to $4000-$7FFF found. **[runtime: expanded ROM boots and shows text from banks 10h-13h]**. Going past 512 KB would need the MBC1 upper-bits register (`$4000`) - not needed.

## 7. Render test [runtime]
- No Latin glyphs exist, so the test builds an 8x8 test font (`font/latin5x7.txt`) into a new LZ stream at 1F:$6000, repoints the $9000 load, and inserts three opening strings (dlg_165/166/167) at their original lengths (in place, max_bytes respected), on the expanded ROM.
- `render_test/before.png` vs `after.png`: the first dialogue page shows "Now, pick a / partner! / Go! Draw!" with the frame and portrait intact. The battle window below shows kana tiles reinterpreted as Latin (expected: those tilemaps need re-lettering).
- Note: a font with a zero run > 255 bytes broke the loader (8-bit count) - fixed in lz.compress.

## Open questions
- Status screen strings 0E:$5022-$506F: who points at them? Same for 03:$4F41 (game-over layout) and the title layout format at 04:$4B22 (`82 98 00 ...` looks like VRAM-address-prefixed write lists).
- Other UI tilemaps might be LZ-compressed (only 9 LZ call sites, all to tile VRAM, so probably not) or stored raw without dakuten; `scan_text.py` only finds runs with dakuten. A runtime sweep of menus/shop/password/report card screens is still needed.
- Which scenes load saki/nama at 8E/8F (kanji tiles) and whether other kanji tiles exist.
- Password charset (FD / CE60 / $00:1FF5) and the password entry grid: not mapped yet. Kana in passwords must stay displayable.
- 02:$467C -> $9000 (another 0x800 load, `$00:2DCD`) and 02:$7C8A -> $9000 (0x150): alternate fonts? Not traced.
- F1/F6/FA unused in dialogue. FA looks broken.
- 1369 IDs vs 1314 unique strings: 193 aliases (shared pointers), 2 orphans.
