; Akazukin Chacha (GB) English UI layer (labels, HUD, report card, results, password, game over).  rgbds.
; Assembled by tools/build_ui.py; bank-0 sections are copied over original code at their fixed addresses,
; ROMX sections go to banks UI_BANK.. (18h-1Fh).  Generated data: tmp/gen/data.asm (records + tile blobs).
INCLUDE "src/ui_defs.inc"

; ================================================================ bank 0
; $1434-$14E6 was: HUD init ($1434), cmd records ($1476), hand-slot printer ($1494). All HUD-only (callers of
; $1434 unchanged, $1476/$1494 only referenced from inside). Now: HUD entry + far-call dispatcher + stubs.
SECTION "b0_hud", ROM0[$1434]
HudInit::                      ; == $1434 (14 callers)
    ld a, ID_HUD
FarDispatch::                  ; a = routine id; runs UiEntry in UI_BANK, returns with the caller's bank
    ld [wFarId], a
    ld a, UI_BANK
    call PushBank
    call UiEntry
    jp PopBank
Stub_Report::  ld a, ID_REPORT
               jr FarDispatch
Stub_RankWord:: ld a, ID_RANKWORD
               jr FarDispatch
Stub_Result::  ld a, ID_RESULT
               jr FarDispatch
Stub_Quest::   ld a, ID_QUEST
               jr FarDispatch
Stub_GameOver:: ld a, ID_GAMEOVER
               jr FarDispatch
HandSlots::                    ; == $1458: original "redraw hand slots" entry (called by 01:42A5 item pickup, 00:16C2 gift)
               ld a, ID_SLOTS
               jr FarDispatch
Stub_PwInit::  ld a, ID_PWINIT
               jr FarDispatch
Stub_PwErr::   ld a, ID_PWERR
               jr FarDispatch
Stub_PwErrDone:: ld a, ID_PWERRDONE
               jr FarDispatch
Stub_PwPrint:: ld a, ID_PWPRINT
               jr FarDispatch
Stub_Title::   ld a, ID_TITLE
               jr FarDispatch
FontHook::                     ; $2D86 (end of the font load, bank 17h pushed): $8800 block, pop, re-blit HUD tiles
    ld bc, $0100
    ld de, $5F23
    ld hl, $8800
    call $2AD5
    call PopBank
    ld a, ID_HUDTILES
    jp FarDispatch
RepExit::                      ; $1A00 (report card exit): restore the HUD label tiles the report card reused
    ld a, $04
    ld [$C8D9], a
    ld a, ID_HUDTILES
    jp FarDispatch
CopyTiles::                    ; a = bank, de = src, hl = VRAM dst, b = tiles. Runs in bank 0 (data bank mapped).
    call PushBank
.tile
    ld c, 8
.pair
    di
.w
    ldh a, [rSTAT]
    and 2
    jr nz, .w
    ld a, [de]
    inc de
    ld [hl+], a
    ld a, [de]
    inc de
    ld [hl+], a
    ei
    dec c
    jr nz, .pair
    dec b
    jr nz, .tile
    jp PopBank
B0End::
ASSERT HudInit == $1434
ASSERT HandSlots == $1458
ASSERT @ <= $14E7              ; $14E7 = HUD blit list (kept)

; $1A06 was: draw the rank kanji (2x2 tiles B2+4*C916 at $988D) - falls through into the portrait load at $1A3C
SECTION "b0_rank", ROM0[$1A06]
RankDraw::
    ld a, ID_RANK
    call FarDispatch
    jr $1A3C
ASSERT @ <= $1A3C

SECTION "b0_repexit", ROM0[$1A00]
    jp RepExit

SECTION "b0_font", ROM0[$2D86]
    jp FontHook

; FD (password) printer: $3F2D call $1FF5 / print CE60 x14 -> translated print in UI_BANK
SECTION "b0_pwprint", ROM0[$3F30]
    jp Stub_PwPrint
ASSERT @ <= $3F3D

; ================================================================ UI bank
SECTION "ui_code", ROMX[$4000], BANK[UI_BANK]
UiEntry::                      ; jump to Routines[wFarId], hl preserved
    push hl
    ld a, [wFarId]
    add a, a
    add a, LOW(Routines)
    ld l, a
    ld a, 0
    adc a, HIGH(Routines)
    ld h, a
    ld a, [hl+]
    ld [wJmp+1], a
    ld a, [hl]
    ld [wJmp+2], a
    ld a, $C3
    ld [wJmp], a
    pop hl
    jp wJmp

Routines:
    dw DoHud, DoReport, DoRankWord, DoResult, DoQuest, DoGameOver, DoPwInit, DoPwErr, DoPwErrDone, DoPwPrint, DoTitle, DoRank, DoHudTiles, DoSlots, DoBurst

; ---------------------------------------------------------------- blitter
; record (10 bytes): db bank, dw src, dw vram, db ntiles, db tile0, dw map (0 = no map write), db cols
; copies ntiles*16 bytes bank:src -> vram (STAT mode 0/1, 2 bytes per wait), then writes tile0.. into the
; tilemap at map in rows of cols cells (stride 32). Returns hl after the record. Clobbers all.
Blit::
    ld a, [hl+]
    ld [wBank], a
    ld a, [hl+]
    ld e, a
    ld a, [hl+]
    ld d, a
    ld a, [hl+]
    ld c, a
    ld a, [hl+]
    ld b, a
    ld a, [hl+]
    ld [wN], a
    ld a, [hl+]
    ld [wT0], a
    ld a, [hl+]
    ld [wMapLo], a
    ld a, [hl+]
    ld [wMapHi], a
    ld a, [hl+]
    ld [wCols], a
    push hl
    ld a, [wN]
    or a
    jr z, .done
    ld h, b
    ld l, c
    ld a, [wN]
    ld b, a
    ld a, [wBank]
    call CopyTiles             ; bank 0 (switches to the data bank)
    ld a, [wNoMap]
    or a
    jr nz, .done
    ld a, [wMapHi]
    or a
    jr z, .done
    ld h, a
    ld a, [wMapLo]
    ld l, a
    ld a, [wT0]
    ld d, a
    ld a, [wN]
    ld b, a
.row
    ld a, [wCols]
    ld c, a
.cell
    di
.w2
    ldh a, [rSTAT]
    and 2
    jr nz, .w2
    ld [hl], d
    ei
    inc hl
    inc d
    dec b
    jr z, .done
    dec c
    jr nz, .cell
    ld a, [wCols]
    cpl
    inc a
    add a, 32
    add a, l
    ld l, a
    jr nc, .row
    inc h
    jr .row
.done
    pop hl
    ret

BlitList::                     ; hl -> records, terminated by bank byte $FF
    ld a, [hl]
    cp $FF
    ret z
    call Blit
    jr BlitList

BlitIdx::                      ; hl -> table of record pointers, a = index
    add a, a
    add a, l
    ld l, a
    jr nc, .n
    inc h
.n
    ld a, [hl+]
    ld h, [hl]
    ld l, a
    jp Blit

; ---------------------------------------------------------------- HUD ($1434)
DoHudTiles:                    ; after every font load / report card exit: tile data only (no tilemap writes)
    ld a, 1
    ld [wNoMap], a
    call HudLabels
    xor a
    ld [wNoMap], a
    ret
DoHud:
    xor a
    ld [wNoMap], a
    ld hl, $14E7               ; original HUD window blit list (bank 0)
    call $04A2
    call $13A2                 ; hearts
    call HudLabels
    ld a, $60
    ldh [$FF4A], a
    ret
DoSlots:                       ; $1458: hand slots only (tiles + tilemap)
    xor a
    ld [wNoMap], a
    ld a, [$C91E]
    ld hl, LeftRecs
    call SlotBlit
    ld a, [$C91D]
    ld hl, RightRecs
    jp SlotBlit
HudLabels:
    ld hl, HudStatic
    call BlitList
    ld a, [$C915]              ; partner -> special command label
    cp NUM_CMD
    jr c, .c
    xor a
.c
    ld hl, CmdRecs
    call BlitIdx
    ld a, [$C91E]              ; left hand
    ld hl, LeftRecs
    call SlotBlit
    ld a, [$C91D]              ; right hand
    ld hl, RightRecs
    jp SlotBlit
SlotBlit:                      ; a = item or $FF (empty -> label "Left"/"Right" = index 64)
    cp 64
    jr c, .i
    ld a, 64
.i
    jp BlitIdx

; ---------------------------------------------------------------- report card
DoReport:                      ; replaces ld hl,$1A83 / call $04A2 at $1913
    ld hl, $1A83
    call $04A2
    ld hl, ReportLabels
    jp BlitList
DoRankWord:                    ; replaces call $32BC at $196E (de = $1A8C + 6*k)
    ld a, e
    sub LOW($1A8C)
    ld b, 0
.d
    cp 6
    jr c, .k
    sub 6
    inc b
    jr .d
.k
    ld a, b
    cp 4
    jr c, .ok
    ld a, 3
.ok
    ld hl, RankWordRecs
    jp BlitIdx
DoRank:                        ; replaces $1A06 (rank "kanji" shokyuu..tokkyuu), report card + results
    ld a, [$C916]
    cp NUM_RANK
    jr c, .ok
    ld a, NUM_RANK-1
.ok
    ld hl, RankRecs
    jp BlitIdx

; ---------------------------------------------------------------- results (03:4E0E)
DoResult:                      ; replaces call $2DA5 at 03:4E24
    call $2DA5
    ld hl, ResultLabels
    jp BlitList
DoQuest:                       ; replaces call $32BC at 03:4E61 (quest goal line at $9943)
    ld a, [$C8FC]
    cp NUM_QUEST
    jr c, .ok
    xor a
.ok
    ld hl, QuestRecs
    jp BlitIdx

; ---------------------------------------------------------------- game over (03:4F16)
DoGameOver:                    ; replaces call $32BC at 03:4F25
    ld hl, GameOverLabels
    jp BlitList

; ---------------------------------------------------------------- password screen (bank 4)
DoPwInit:                      ; replaces call $0316 at 04:4439
    ld hl, PwLabels
    call BlitList
    jp $0316
DoPwErr:                       ; replaces call $32BC at 04:451D (second copy at 04:4526 nopped)
    ld hl, PwErrLabels
    jp BlitList
DoPwErrDone:                   ; replaces call $0354 at 04:453C
    call $0354
    ld hl, PwRedraw
    jp BlitList
DoPwPrint:                     ; FD: print the 14 password bytes at CE60 through the VWF, translated
    ld b, 14
    ld hl, $CE60
.l
    ld a, [hl+]
    push hl
    push bc
    cp $FF
    jr z, .p
    and $7F
    ld e, a
    ld d, 0
    ld hl, PwXlat
    add hl, de
    ld a, [hl]
.p
    call $3FD2
    pop bc
    pop hl
    dec b
    jr nz, .l
    ret

; ---------------------------------------------------------------- title (unused hook slot)
DoBurst:                       ; reserved (burst is replaced in place)
    ret
DoTitle:                       ; replaces call $2D91 (OBJ font copy) at 04:423A
    call $2D91
    ld hl, TitleLabels
    jp BlitList

INCLUDE "tmp/gen/data.asm"
