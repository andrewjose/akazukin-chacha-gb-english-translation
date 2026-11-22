; UI layer constants (keep in sync with tools/build_ui.py)
DEF UI_BANK    EQU $18
DEF PushBank   EQU $02B2
DEF PopBank    EQU $02D4
DEF rSTAT      EQU $FF41
; routine ids (order of Routines in ui.asm)
DEF ID_HUD      EQU 0
DEF ID_REPORT   EQU 1
DEF ID_RANKWORD EQU 2
DEF ID_RESULT   EQU 3
DEF ID_QUEST    EQU 4
DEF ID_GAMEOVER EQU 5
DEF ID_PWINIT   EQU 6
DEF ID_PWERR    EQU 7
DEF ID_PWERRDONE EQU 8
DEF ID_PWPRINT  EQU 9
DEF ID_TITLE    EQU 10
DEF ID_RANK     EQU 11
DEF ID_HUDTILES EQU 12
DEF ID_SLOTS    EQU 13
DEF ID_BURST    EQU 14
; WRAM: $D3B0-$D3BF, inside the 241-byte never-referenced zero run $D302-$D3F2 (engine uses $D3D0-$D3EB)
DEF wFarId     EQU $D3B0
DEF wJmp       EQU $D3B1      ; 3 bytes: jp nn
DEF wBank      EQU $D3B4
DEF wN         EQU $D3B5
DEF wT0        EQU $D3B6
DEF wMapLo     EQU $D3B7
DEF wMapHi     EQU $D3B8
DEF wCols      EQU $D3B9
DEF wNoMap     EQU $D3BA
