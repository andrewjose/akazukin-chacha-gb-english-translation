# Playtest coverage: Akazukin Chacha EN (build md5 af870608b1e11d10ccd2a33f7d1e48ef, snapshot tmp/en.gb)

> **Repository note.** These notes were written in the original work tree, where `re/`, `engine/` and `ui/` each had
> their own `tools/`. In this repository the build tools are in `tools/re/`, `tools/engine/` and `tools/ui/`, and every
> generated file goes to `build/work/` (see the README). Screenshots, save states, test ROMs, extracted strings,
> captured graphics and the headless test harnesses referred to below are not published (they contain game data);
> everything the build needs is regenerated from your own ROM.

All headless PyBoy, scripts in `tools/`, shots in `shots/`, states in `tmp/st_*.state`. Issues: `issues.csv`.

## RAM / flow notes found while playing (useful for later tests)
- C8F9 top mode: 0 title, 1 school, 2 dungeon, 3 battle, 4/5 game over / ending. CE44 = per-frame action (START = map, SELECT = report card).
- C8FB scene: 1 hall (ring of 60 positions, CE4B = position x2), rooms 2-C by door table 01:4137 (UP at a door);
  dungeon = C8FC (quest) + 0Dh.
- Leaving for the dungeon: talk until C92D = 2 (location known), then the school-gate room (door at CE4B=1Dh, room 0Bh) -> world map -> dungeon.
  Shortcut used: poke C92D=2, CE4B=1Dh, press UP (tools/go_dungeon.py, dng_all.py).
- Quest done / time up: Principal Urara's room (CE4B=50h, speaker CE41=8): quest item C8FF in a hand (C91D/C91E) -> dlg_1E1 + graduation ending + results; C8FD (day) >= 7 -> dlg_1E2 + time-up ending.
- HP C917 (max C918). HP 0 at the end of a battle -> collapse -> nurse's office (dlg_3A2, 0F3, 0F6); with C94D != 0 (special password mode) -> GAME OVER + reset.
- Lead C915 (title grid cursor C517), partner C924; NICK = nick[CE41*6 + C8D2], NICK2 = nick[CE41*6 + C8D1].

## Screens
| screen | seen? | how | notes |
|---|---|---|---|
| Title, New Game / Continue | yes | play.py | ok |
| Lead select (6 faces) | yes | run_open.py | no text on screen |
| Opening + lot draw + assignment | yes, 4 pairs | run_open.py: ChaCha+Marin, Riiya+Marin, Riiya+Shiine (dlg_172 "Oh, it's just Dumb Dog... / I'm not a dog! I'm a WOLF!" reads right), Suzu+Marin; JP Riiya+Shiine for reference | ok |
| School hall, doors, NPC rooms 2-C | yes | probe.py / room loop | ok |
| World map (START) | yes | | no text |
| School gate departure + map | yes | go_dungeon.py | ok |
| Trapsalot Dungeon (q0) | yes | dng_all.py + explore/hunt | exit sign deiriguchi untranslated; item pickup -> HUD corruption (blocker) |
| Darkalot Cave (q1) | yes | | pit message 205 ok; exit sign |
| Trapsalot/monster (q2) | yes | | ok |
| Coral Forest (q3) | yes | | battles (Rubberfish), exit sign |
| Magic Forest / Holy Falls (q4) | yes (forest part) | explore rsf (Riiya+Shiine) + cc | Holy Falls spring itself not reached (quest item poked instead) |
| Maze of Trials (q5) | yes (entrance area) | | Cycloghost battle |
| Battles | yes: >6 real fights | battle.py | win (magic, fish summon), run away, enemy lines, partner banter, transformation (Riiya wolf / Rush) ok |
| Item use in battle (Left / Right) | yes | battle.py useL/useR | HUD item names update correctly (Yummy Cake, Light Wall) |
| Item pickup in dungeon | yes | hunt.py | BLOCKER: HUD becomes password tiles ($1458 stub clash) |
| Report card (SELECT) hall + dungeon | yes | play.py | ok |
| Collapse -> nurse's office | yes | collapse.py | ok |
| GAME OVER (special mode) | yes | collapse.py (C94D=1) | ok |
| Diary Spell given by Urara (real flow, dlg_11E) | yes | visit.py urara | shown "dQAA AP** A%yD" |
| Password entry + continue | yes (UI harness t_pwtest.py on this build) | MATCH | typed from a real password not done by hand |
| Quest done -> graduation ending -> Exam Results (pass stamp) -> reset | yes, EN vs JP | ending_cmp.py, results_cmp.py | BLOCKER two-box text corruption; stray "th" after results |
| Time up -> ending -> title | yes | visit.py fail | same two-box corruption (1E4/1EB) |
| Results fail stamp | only via UI force-call earlier | | real fail path skipped the results screen in my run? (went ending -> title) |
| Credits (03:5071) | yes (force-call), EN vs JP | credits.py | line tails fixed; first pages are during the fade-in |
| SGB border | no (PyBoy has no SGB) | | |

## All dialogue (1369 IDs = 1316 strings + aliases)
- `tools/sweep.py`: every ID forced into the opening box (state just before the first $3B5B call; BC replaced), capture at every WAIT,
  before every SCROLL/CLR and at the top-level END; EN and JP. Shots `shots/sweep_en|orig/ID_n.png`; sheets per 100 IDs `shots/sheets/`.
- `tools/analyze_sweep.py`: decodes every box row from VRAM with the VWF font (exact glyph match) and matches it to the layout lines
  (tokens = any table value). Result: 0 garbage tiles, 0 non-canvas tiles in boxes, all 1316 strings render; only real defect dlg_0A3
  (callee clipped). Remaining flags are false positives (layout text drops a heart before PAUSE, dummy password).
- Token stress run (`sweep_tok`): NICK/NICK2 = "Dumb Dog", ITEM/ITEM2 = "Angry Anchor", NAME = "Wrath Grapes": no overflow.
- `tools/frame_cmp.py`: portrait/frame region EN vs JP identical for the first page of every ID (diffs only JP text in column 19, blink timing).
- `tools/text_lint.py`: FACE order equals JP everywhere except dlg_172 (intentional fix); WAIT/CLR only added; typography list in issues.csv.
- Special boxes (report card comments/skills, credits, ending two-box layout) checked in their real screens, not in the sweep.

## Gaps
- Inside of dungeons beyond the first rooms (bosses/guardians, Holy Falls spring, Dragon Palace, Mericle's tomb), chest contents/messages
  454/47C/4A6/4CD/4F3/519 in their real context (rendering verified by the sweep only).
- Full week of play without RAM pokes; real typed Continue from a password obtained in play.
- Other lead characters' graduation endings (only Riiya+Shiine, quest 4 seen; the two-box bug applies to every ending that uses dlg_198-1C7 / 1E3-1EC).
- SGB border on real hardware/SGB emulator.

## Round 2 (build md5 1b56918738556b302ee33d42548c5fab, snapshot tmp/en.gb; round-1 build kept as tmp/en_r1.gb)
- States regenerated on the new build (title, msg0, hall states for 6 leads: chacha, riiya_shiine, suzu, shiine, yk (Marin lead, C915=4), mr (Yakko lead, C915=3)).
- Full forced sweep re-run (all 1369 IDs): 0 garbage, 0 unexpected lines; only the known false positives (layout text drops a heart, dummy password).
  Note: the round-2 engine moved the F0 handler (jump table now -> $3C6F); `sweep.py` reads it from the table. Hooking the old $3C6A
  corrupted execution and looked like a scroll regression - it is not one. Canvas now also uses tiles 54-6F ("noncanvas" flags = expected).
- Round-1 issues: 17 fixed, 1 partly fixed (two-box endings), 1 partly fixed (ending SFX art) - see `round2_status` in issues.csv.
- New coverage:
  - Graduation endings for 5 leads: Riiya (Holy Water), Suzu, ChaCha, Yakko (Maze guardian), Shiine (Shock Frog), Marin (Pink Coral) - `tools/ending2.py`, shots/r2_ending_*.png.
  - Time-up path to the end: 1E2 -> SOB ending -> title. No results screen on this path in JP either (checked on the original).
  - Password earned in play (collapse -> nurse -> Urara dlg_11E "YYJ> LM** A%(note)A"), read off the screen, typed on Continue with real D-pad moves: MATCH (`tools/pw_real.py`, shots/r2_pw_*.png).
  - EXIT signs: Darkalot Cave, Coral Forest (round 2); Trapsalot/Maze seen as JP in round 1 (same tiles).
  - Chest pickup in context (Darkalot: Pillow) with HUD update; item messages 454 (Pouch -> "Oh, it's Medallion!" + Magical Princess), 449 (Holy Sticker -> Straw Cup turned into Holy Water) in battle.
  - Long random walks with HP refill (40k frames x4 dungeons): many more enemy/partner lines, no new defects.
- Still not reached: dungeon bosses/guardians and the Holy Falls spring in real play (random walk does not get there; needs map routes), Dragon Palace, Mericle's tomb.

## Round 3 (release candidate rc_v01.gb, md5 1bf66a69368b4183999e0c9c3b9529ca, snapshot tmp/en.gb; r2 build kept as tmp/en_r2.gb)
- All states regenerated on the RC (engine WRAM $D3D0-$D3F0 zeroed when loading older states).
- Forced sweep, all 1369 IDs: clean (only the known false positives). dlg_109 unindented.
- Endings: all 6 leads' graduation endings + time-up, `tools/ending3.py` decodes BOTH boxes at every WAIT and checks them against the
  messages printed there: 0 problems on the RC (the same check flags 19F on the round-2 build). Sheet: shots/r3_endings_all.png
  (Riiya+Shiine Holy Water, ChaCha / Suzu / Marin-lead Maze, Shiine Shock Frog, Yakko Pink Coral, time-up). All ending art English.
- Bosses/guardians (`tools/boss.py`: random walk, at the encounter set-up 01:508C the enemy slot is forced to 7 = dungeon boss, enemy id = quest*8+slot in CE2C):
  Trapsalot Wee Piggy (07), Darkalot Shroom Lord (0F), Shock Frog (17), Umibozu (1F, "This humble samurai shall give the Pink Coral to Lady Marin!"),
  Snowdrop (27), Mr. Rascal, keeper of the Trick Maze (2F): intro lines, partner lines, defeat lines all render (shots/r3_boss_q*.png).
  Forced boss encounters don't hand out the quest trophy (flow not exercised).
- Holy Falls spring: Magic Forest room (CE48,CE49) = (C99C,C99D) = (13,3), spot CE4B 9-0B / CE4C 9; reached by poking the room coords at a room
  transition and walking there; B -> Left -> A with a Straw Cup: side-view falls scene, dlg_528 "I got the Holy Water!", hand becomes Holy Water
  (shots/r3_holy_falls.png). New: Japanese sign next to the spring.
- Still unreached: the Dragon Palace / Mericle's tomb areas by real routing, a boss fight reached by walking the map (encounters were forced),
  the trophy hand-in after a real boss win.
