# Akazukin ChaCha (Game Boy) - English fan translation

English translation of *Akazukin ChaCha* (Tomy, 1995, Game Boy, Super Game Boy enhanced), the school-of-magic
adventure based on Min Ayahana's manga and anime. Names follow the official English TV dub of the anime
(ChaCha, Seravi, Suzu, Urara School of Magic, Magical Princess, Selene Arrow); names the dub never gave are marked
in [docs/glossary.md](docs/glossary.md).

This repository holds **tools, English text and documentation only**. It contains no ROM and no game data.

## Features (v0.1)
- All 1,316 dialogue messages and 163 names/UI strings translated, with one editor pass for names, speakers and voices.
- Variable-width font in every dialogue box, balanced line breaking measured at build time; the two-box ending scenes
  keep both texts on screen.
- English word tiles for the battle HUD, report card, exam results, title menu and game over; item names in the
  battle hand slots.
- Diary Spell (password) screen and password display in English letters; passwords round-trip.
- Graphics re-lettered: title logo, rank stamps, EXIT signs, BOOM! burst, ending sound effects, Holy Falls sign,
  Super Game Boy border.
- Original-game bug fixed: Riiya's reply to Shiine (dlg_172) plays instead of a teacher's line.
- ROM expanded to 512 KB (MBC1).

## Patch
Patches are published as release assets (BPS). Required source ROM:
`Akazukin Chacha (Japan) (SGB Enhanced).gb` - 262,144 bytes, CRC32 `898609B4`,
MD5 `9a5215658c60a1802b11f728c292b536`, SHA-1 `d07970a7eae51aef8c4e8b4bcdd57aeed6360bdd`.

Patched v0.1 result: 524,288 bytes, CRC32 `211D801A`, MD5 `ecf356b1e722b5ee32e5b3860153eb3a`.

## Building from source
Requirements: Python 3, Pillow, pyphen, rgbds (rgbasm/rgblink), the DejaVu fonts (`fonts-dejavu-core`;
DejaVu Sans Condensed Bold is used for a few large labels) and your own copy of the original ROM.
Optional: [Flips](https://github.com/Alcaro/Flips) for the BPS patch; without it the build falls back to the
bundled `tools/common/mkbps.py` (larger, but equivalent, patch).
```
python3 build.py --rom "Akazukin Chacha (Japan) (SGB Enhanced).gb"            # rgbds (and flips) on PATH
python3 build.py --rom orig.gb --out build/ --rgbds /path/to/rgbds --flips /path/to/flips
```
rgbds is taken from `--rgbds`, `$RGBDS_DIR` or PATH; Flips from `--flips`, `$FLIPS`, PATH or the rgbds directory
(the build prints which BPS writer it used and checks the patch by applying it). Set `CHACHA_TTF` if the DejaVu
font is somewhere unusual.

Outputs: `build/chacha_en.gb` and `build/chacha_en.bps`; the script prints their MD5s. v0.1 builds to
MD5 `ecf356b1e722b5ee32e5b3860153eb3a` (verified with Python 3.13, Pillow 12.3, DejaVu 2.37, rgbds a6a70bb; a
different FreeType/DejaVu version could change the few pixels of the large labels). Intermediate files (extracted
string table, generated fonts, merged translation, engine build, generated asm, maps/symbols) go to `build/work/`.
Nothing from the ROM is stored in this repository: the string table, the menu font's frame tiles, the ending pictures,
signs, stamps and the SGB border are read from your ROM on every build.

Build steps: `tools/re/extract.py` (string table) -> `translation/en.json` checked against it ->
`tools/engine/build.py` (VWF engine, dialogue, name tables, fixed text) -> `tools/ui/build_ui.py` (UI layer and
graphics) -> BPS. Optional after a build: `python3 tools/engine/typeset_check.py` for a line-fit report and contact
sheets. Details: [engine notes](docs/technical/engine-notes.md), [UI notes](docs/technical/ui-notes.md).

## Repository layout
| path | what |
|---|---|
| `build.py` | one-step build from your ROM |
| `translation/en.json` | the English script: `[{id, en}]` (+ `short8` for 8-cell menu fields, `alt_long` for the results screen) |
| `tools/re/` | text table (`chacha.tbl`), string extractor, LZ codec, SM83 disassembler, free-space map |
| `tools/engine/` | VWF engine (`src/vwf.asm`), hand-drawn font (`fontdef.py`), encoder/line breaker/inserter (`build.py`) |
| `tools/ui/` | UI layer (`src/ui.asm`, `build_ui.py`), label renderer, picture/sign/stamp/SGB border editors |
| `tools/common/` | path settings, BPS writer |

## Documentation
- [Plain-language overview](docs/overview.md)
- [Engineer-level explanation](docs/engineer.md)
- Deep technical: [reverse engineering](docs/technical/re-notes.md), [engine/VWF](docs/technical/engine-notes.md),
  [UI layer and graphics](docs/technical/ui-notes.md)
- Translation: [glossary](docs/glossary.md), [style guide](docs/STYLE.md), [editor report](docs/edit-report.md),
  [bug fixes](docs/bugfixes.md)
- Testing: [playtest coverage](docs/playtest-coverage.md)
- [Changelog](CHANGELOG.md)

## Status
Emulator-tested only (headless PyBoy, three playtest rounds). Not yet tested on real hardware or a flash cart, and
the SGB border has not been seen on an SGB-capable emulator. Passwords from the Japanese version do not map to the
English letters.

## Credits
Original game (c) Min Ayahana / Shueisha / TV Tokyo / NAS / Tomy. This is an unofficial fan project; no game
data is distributed here.
