; shared constants (keep in sync with tools/build.py)
DEF VWF_BANK   EQU $17
DEF DLG_BANK   EQU $10
DEF DLG_PTRS   EQU $4000
DEF DLG_BANKS  EQU $4000 + $559 * 2
DEF PushBank   EQU $02B2
DEF PopBank    EQU $02D4
DEF rSTAT      EQU $FF41
DEF CUR_LO     EQU $C8E8
DEF CUR_HI     EQU $C8E9
DEF LINE_PX    EQU 120
DEF CELLS      EQU 15
DEF FIRST_CHAR EQU $20
DEF NUM_GLYPHS EQU $63            ; codes $20-$82
; WRAM (unused by the game: never referenced, always 0 in runtime sweeps; see NOTES.md)
DEF wSlot      EQU $D3D0          ; $FF = box cleared (next line restarts at tile 0), else 0
DEF wLineLo    EQU $D3D1          ; tilemap address of the current line start
DEF wLineHi    EQU $D3D2          ; 0 = force new line
DEF wPenX      EQU $D3D3
DEF wBufCell   EQU $D3D4
DEF wChar      EQU $D3D5
DEF wWidth     EQU $D3D6
DEF wTile      EQU $D3D7
DEF wBuf       EQU $D3D8          ; 8 bytes: current tile (1bpp)
DEF wRight     EQU $D3E0          ; 8 bytes: spill tile (must follow wBuf)
DEF wShift     EQU $D3E8
DEF wCell      EQU $D3E9
DEF wBase      EQU $D3EA          ; first canvas tile of the current line
DEF wUsed      EQU $D3EB          ; cells used by the current line
DEF CANVAS     EQU 60             ; canvas tiles 00-3B
DEF wDual      EQU $D3EC          ; 1 = two boxes on screen (dual ring)
DEF wRStart    EQU $D3ED          ; current box range start (logical)
DEF wMsgStart  EQU $D3EE          ; 1 = message started (set by MsgStartFlag)
DEF wLog       EQU $D3EF          ; logical cell being drawn
DEF DUAL_LO    EQU $54            ; dual ring extension: tiles 54-6F (fixed lowercase; not shown in field/ending scenes)
DEF DUAL_HI    EQU $70
DEF wRSize     EQU $D3F0          ; current box range size
DEF DUAL_SIZE  EQU 44             ; logical cells per box in dual mode (88 = 60 + 28)
DEF CE97       EQU $CE97          ; 1 = text goes to the window map (ending script, 0B:7E30)
