# How it works (for software engineers new to Game Boy hacking)

**Banks.** The Game Boy sees 32 KB of cartridge at a time: a fixed 16 KB bank 0 plus one switchable
16 KB bank (MBC1 mapper). The original 256 KB ROM had no free space, so we doubled it to 512 KB and
moved all dialogue into the new banks. The text reader picked the bank from the message ID range; we
replaced that with a per-ID bank table (a lookup table instead of hard-coded ranges).

**Encoding.** Each text byte is the index of an 8x8 font tile; control bytes EF-FE handle new line,
wait for key, clear, scroll, portrait, name substitution and "call a shared sub-string" (like a
function call for repeated phrases). English uses ASCII codes, so the build script encodes text
directly; the control codes are kept.

**Variable-width font (VWF).** Originally each character went straight into the screen's tile grid
(one cell per letter), which makes English look spaced out. We hooked the "put character" routine so
letters are drawn pixel by pixel into a set of canvas tiles (an off-screen bitmap), and the box cells
point at those tiles. Two text boxes can be on screen at once in the endings, so each box owns its own
range of canvas tiles; clearing one box never recycles the other's tiles.

**Line breaking.** The build measures every word with the real glyph widths and picks breaks that keep
lines even (minimal squared slack, TeX-style); name slots are measured at the widest possible name;
text that continues across a shared sub-string is measured as one paragraph. Any overflow fails the build.

**Menus and screens.** Static labels (battle menu, report card, results, title) are pre-rendered at
build time as proportional word tiles and blitted by a small routine; dynamic fields (item names in the
hand slots, partner names, scores) are drawn into reserved tiles when the game redraws them.

**Graphics.** Pictures are compressed with the game's own LZ format. We wrote a decoder/encoder pair,
redrew Japanese art (title logo, rank stamps, signs, sound effects, SGB border) and recompressed it in
place (each new version smaller than the original, because some loaders hard-code the bank).

**Password.** The game's internal codes are unchanged; only the glyphs shown on the entry grid and in
dialogue changed, so passwords stay valid. Verified by generating a password in play, typing it back
in, and comparing game state.

**Testing.** Headless emulator (PyBoy) scripts: every dialogue ID forced on screen and decoded back from
video memory, all six leads' endings checked box by box at every pause, real battles, dungeons, the
password round trip. Real hardware not yet tested.

**Building from your own ROM.** The repository holds only the English text, the tools and the new art
code; nothing copied from the game. `build.py` treats your ROM like an external dependency pinned by
hash: it checks the MD5, then regenerates everything derived from the game at build time - the string
table (offsets, pointer slots, field sizes), the frame/heart tiles of the menu font, the ending pictures
and signs (decompressed from the ROM, re-lettered, recompressed) and the SGB border. The build is
deterministic, so the same inputs always give the same output MD5, which is how the published build is
checked.
