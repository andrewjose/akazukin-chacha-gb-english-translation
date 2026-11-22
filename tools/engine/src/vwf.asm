; Akazukin Chacha (GB) English VWF engine.  rgbds.  Assembled by tools/asm.py; the bank-0 sections are
; copied over the original code at their fixed addresses, the ROMX section becomes bank VWF_BANK.
INCLUDE "src/defs.inc"

; ---------------------------------------------------------------- bank 0 patches
SECTION "lookup", ROM0[$3C46]
; replaces the original bank-by-ID reader: pointer + bank from per-ID tables in bank DLG_BANK
TextLookup:
    ld a, DLG_BANK
    call PushBank
TextLookupMid:                 ; == $3C4B, entered by the B-replay path ($3D6D)
    ld hl, DLG_PTRS
    add hl, bc
    add hl, bc
    ld e, [hl]
    inc hl
    ld d, [hl]
    ld hl, DLG_BANKS
    add hl, bc
    ld a, [hl]
    call PopBank
    call PushBank
    ld hl, $C8E6
    ld [hl], e
    inc hl
    ld [hl], d
ASSERT @ == $3C64
MsgStartFlag:                  ; message start: fresh line + "new message" marker
    ld hl, wMsgStart
    ld [hl], 1
LineFlag:                      ; force the VWF onto a fresh line
    ld hl, wLineHi
    ld [hl], 0
    ret
ScrollHook:                    ; control code F0 now lands here ($3C6F)
    call LineFlag
    jp $3C7F
DualOff:                       ; $1ED0 (ending script end: CE97 = 0) now jumps here: also leave dual mode
    xor a
    ld [CE97], a
    ld [wDual], a
    ret
ASSERT TextLookupMid == $3C4B
ASSERT @ <= $3C7E

SECTION "ending_end", ROM0[$1ED0]
    jp DualOff

SECTION "jt_scroll", ROM0[$3C26]
    dw ScrollHook

SECTION "clr_call", ROM0[$3D99]
    call ClrHook               ; was: push af / ld hl,$C8CE
    nop

SECTION "putchar", ROM0[$3FD2]
; $3FD2 put-char (main loop, F4-F8 name printer, password) -> VWF in bank VWF_BANK. Preserves all regs.
PutChar:
    push af
    ld a, VWF_BANK
    call PushBank
    pop af
    call VwfPutChar
    jp PopBank
ClrHook:                       ; box clear ($3D99, also F2 and message start): reset the tile ring
    pop hl
    push af
    push hl
    ld hl, wSlot
    ld [hl], $FF
    ld hl, $C8CE
    ret
ASSERT @ <= $3FEB

; ---------------------------------------------------------------- VWF bank
SECTION "vwf", ROMX[$4000], BANK[VWF_BANK]
VwfPutChar::
    push af
    push bc
    push de
    push hl
    cp $FF
    jr nz, .notff
    ld a, $20
.notff:
    ld [wChar], a
    ; ---- new line?  (ring reset, forced flag, or the engine moved the cursor: NL / CLR / SCROLL)
    ld a, [wSlot]
    inc a
    jr z, .newline
    ld a, [wLineHi]
    or a
    jr z, .newline
    ld a, [CUR_LO]
    ld hl, wLineLo
    cp [hl]
    jr nz, .newline
    ld a, [CUR_HI]
    inc hl
    cp [hl]
    jr z, .sameline
.newline:
    ; Canvas allocation: each line takes consecutive logical cells of its box's range (see SetRange/LogToTile).
    ;  - single box (normal): range = logical 0-59 (tiles 00-3B); a box clear restarts at 0, lines advance (wrap in range).
    ;  - dual (ending script: a box printed with CE97=1 = window box at (1,1) besides the $9800 box at (4,1)):
    ;    the $98xx box owns logical 0-43, the window box 44-87 (tiles 2C-3B + 54-6F). A clear/new page only
    ;    recycles that box's own range, so the other box keeps its text. Off at the end of the ending script
    ;    ($1ED0 -> DualOff) and at a message start without a clear (report card, instant text).
    ld a, [wSlot]
    inc a
    jr nz, .notclr
    ld [wSlot], a               ; 0
    ld [wMsgStart], a
    ld a, [CE97]
    or a
    jr z, .clrrange
    ld a, 1
    ld [wDual], a
.clrrange:
    call SetRange
    ld a, [wRStart]
    ld [wBase], a
    jr .based
.notclr:
    ld a, [wMsgStart]
    or a
    jr z, .advance
    xor a
    ld [wMsgStart], a
    ld [wDual], a
.advance:
    call SetRange
    ld a, [wRStart]
    ld e, a                     ; e = range start
    ld a, [wRSize]
    add e
    ld c, a                     ; c = range end
    ld a, [wUsed]
    ld b, a
    ld a, [wBase]
    add b
    cp c
    jr c, .lo_chk
    ld hl, wRSize
    sub [hl]
.lo_chk:
    cp e
    jr c, .torange
    cp c
    jr c, .nowrap
.torange:
    ld a, e
.nowrap:
    ld [wBase], a
.based:
    xor a
    ld [wUsed], a
    ld a, [CUR_LO]
    ld [wLineLo], a
    ld a, [CUR_HI]
    ld [wLineHi], a
    call BlankRow
    xor a
    ld [wPenX], a
    ld [wBufCell], a
    ld hl, wBuf
    ld b, 8
.clr1:
    ld [hl+], a
    dec b
    jr nz, .clr1
.sameline:
    ld a, [wChar]
    sub FIRST_CHAR
    jp c, .done
    cp NUM_GLYPHS
    jp nc, .done
    ld c, a
    ld b, 0
    ld hl, VwfWidths
    add hl, bc
    ld a, [hl]
    or a
    jp z, .done
    ld [wWidth], a
    ld d, a
    ld a, [wPenX]
    add d
    cp LINE_PX + 1
    jp nc, .done                ; would overflow the 120 px line: clip
    ld a, [wPenX]
    and 7
    ld [wShift], a
    ld a, [wPenX]
    srl a
    srl a
    srl a
    ld [wCell], a
    ld hl, wBufCell
    cp [hl]
    jr z, .bufok
    ld [hl], a                  ; pen is in a fresh cell: start from an empty tile
    ld hl, wBuf
    xor a
    ld b, 8
.clr2:
    ld [hl+], a
    dec b
    jr nz, .clr2
.bufok:
    ld h, 0
    ld l, c
    add hl, hl
    add hl, hl
    add hl, hl
    ld de, VwfGlyphs
    add hl, de
    ld d, h
    ld e, l
    ld hl, wBuf
    ld b, 8
.row:
    ld a, [de]
    inc de
    push de
    ld d, a
    ld e, 0
    ld a, [wShift]
    or a
    jr z, .noshift
.sh:
    srl d
    rr e
    dec a
    jr nz, .sh
.noshift:
    ld a, d
    or [hl]
    ld [hl], a                  ; left part ORed into the current tile
    ld a, l
    add 8
    ld l, a
    ld [hl], e                  ; spill into wRight
    ld a, l
    sub 7
    ld l, a
    pop de
    dec b
    jr nz, .row
    ; logical cell = base + cell, wrapped inside the box's range, then -> tile
    ld a, [wCell]
    call MarkUsed
    ld b, a
    ld a, [wBase]
    add b
    call WrapRange
    ld [wLog], a
    call LogToTile
    ld [wTile], a
    ld hl, wBuf
    call WriteTile
    ld a, [wCell]
    call WriteMap
    ld a, [wShift]
    ld b, a
    ld a, [wWidth]
    add b
    cp 9
    jr c, .noright
    ld a, [wCell]
    cp CELLS - 1
    jr nc, .noright
    inc a
    ld [wCell], a
    call MarkUsed
    ld a, [wLog]
    inc a
    call WrapRange
    ld [wLog], a
    call LogToTile
    ld [wTile], a
    ld hl, wRight
    call WriteTile
    ld a, [wCell]
    call WriteMap
.noright:
    ld a, [wWidth]
    ld b, a
    ld a, [wPenX]
    ld c, a
    add b
    ld [wPenX], a
    srl a
    srl a
    srl a
    ld b, a
    ld a, c
    srl a
    srl a
    srl a
    cp b
    jr z, .done
    ld a, b
    ld [wBufCell], a
    ld hl, wRight
    ld de, wBuf
    ld b, 8
.cp:
    ld a, [hl+]
    ld [de], a
    inc de
    dec b
    jr nz, .cp
.done:
    pop hl
    pop de
    pop bc
    pop af
    ret

; New line: every tilemap cell of the row (15 cells from the line start, row-wrapped) that still shows a
; canvas tile (stale VWF text from an earlier, longer line) is set to the blank tile $FF. Frame and other
; graphics (tiles >= CANVAS) are left alone. Clobbers af, bc, de, hl.
BlankRow:
    ld a, [wLineLo]
    ld c, a
    and $E0
    ld d, a
    ld a, [wLineHi]
    ld h, a
    ld e, 0
    ld b, CELLS
.cell:
    ld a, c
    add e
    and $1F
    or d
    ld l, a
    di
.wait:
    ldh a, [rSTAT]
    and 3
    cp 2
    jr nc, .wait
    ld a, [hl]
    cp CANVAS
    jr c, .blank
    cp DUAL_LO
    jr c, .keep
    cp DUAL_HI
    jr nc, .keep
    ld a, [wDual]
    or a
    jr z, .keep
.blank:
    ld [hl], $FF
.keep:
    ei
    inc e
    dec b
    jr nz, .cell
    ret

; sets wRStart / wRSize for the box the current line is in
SetRange:
    ld a, [wDual]
    or a
    jr nz, .dual
    ld [wRStart], a
    ld a, CANVAS
    ld [wRSize], a
    ret
.dual:
    ld a, DUAL_SIZE
    ld [wRSize], a
    ld a, [CUR_HI]
    and $FC
    cp $9C
    ld a, 0
    jr nz, .set
    ld a, DUAL_SIZE
.set:
    ld [wRStart], a
    ret

; a = logical cell; if >= range end, subtract the range size
WrapRange:
    push bc
    ld b, a
    ld a, [wRStart]
    ld c, a
    ld a, [wRSize]
    add c
    ld c, a
    ld a, b
    cp c
    jr c, .ok
    ld a, [wRSize]
    ld c, a
    ld a, b
    sub c
.ok:
    pop bc
    ret

; a = logical cell -> tile index (0-3B, then DUAL_LO..DUAL_HI-1)
LogToTile:
    cp CANVAS
    ret c
    add DUAL_LO - CANVAS
    ret

; a = cell: wUsed = max(wUsed, a+1). preserves a
MarkUsed:
    push bc
    ld c, a
    inc c
    ld a, [wUsed]
    cp c
    jr nc, .keep
    ld a, c
    ld [wUsed], a
.keep:
    ld a, c
    dec a
    pop bc
    ret

; a = tile index (00-3B, $8800 addressing -> $9000+a*16), hl = 8 bytes 1bpp. Ink = colour 3.
WriteTile:
    push hl
    ld l, a
    ld h, 0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld de, $9000
    add hl, de
    ld d, h
    ld e, l
    pop hl
    ld b, 8
.lp:
    di
.wait:
    ldh a, [rSTAT]
    and 3
    cp 2
    jr nc, .wait
    ld a, [hl+]
    ld [de], a
    inc de
    ld [de], a
    inc de
    ei
    dec b
    jr nz, .lp
    ret

; a = cell (0-14) of the current line; writes [wTile] into the tilemap (row-wrapped like $1F4A)
WriteMap:
    ld b, a
    ld a, [wLineLo]
    ld c, a
    and $E0
    ld e, a
    ld a, c
    add b
    and $1F
    or e
    ld l, a
    ld a, [wLineHi]
    ld h, a
    ld a, [wTile]
    ld b, a
    di
.wait:
    ldh a, [rSTAT]
    and 3
    cp 2
    jr nc, .wait
    ld [hl], b
    ei
    ret

VwfWidths:
    INCBIN "font/vwf_widths.bin"
VwfGlyphs:
    INCBIN "font/vwf_glyphs.bin"
VwfEnd::
