"""Shared locations for the build tools. Everything comes from the environment (set by the repo's build.py)
or falls back to repo-relative defaults, so the tools can also be run by hand:
  CHACHA_ROM      original ROM (Akazukin Chacha (Japan) (SGB Enhanced).gb, MD5 below)
  CHACHA_WORK     scratch/output directory for generated files (default: <repo>/build/work)
  CHACHA_STRINGS  extracted string table (default: $CHACHA_WORK/re/strings.json)
  RGBDS_DIR       directory with rgbasm/rgblink/rgbfix (default: PATH)
  CHACHA_TTF      DejaVu Sans Condensed Bold (used for a few large labels; default: searched in system font dirs)"""
import os,shutil,glob
TOOLS=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO=os.path.dirname(TOOLS)
ORIG_MD5='9a5215658c60a1802b11f728c292b536'
def rom_path():
    p=os.environ.get('CHACHA_ROM','')
    if not p: raise SystemExit('set CHACHA_ROM to the original ROM (or use the repo build.py --rom)')
    return p
WORK=os.path.abspath(os.environ.get('CHACHA_WORK') or os.path.join(REPO,'build','work'))
STRINGS=os.environ.get('CHACHA_STRINGS') or os.path.join(WORK,'re','strings.json')
ENGINE_WORK=os.path.join(WORK,'engine')
UI_WORK=os.path.join(WORK,'ui')
def tool(name):
    d=os.environ.get('RGBDS_DIR','')
    p=shutil.which(name,path=d) if d else shutil.which(name)
    if not p: raise SystemExit('%s not found (install rgbds or set RGBDS_DIR)'%name)
    return p
def ttf():
    p=os.environ.get('CHACHA_TTF','')
    if p: return p
    for d in ('/usr/share/fonts','/usr/local/share/fonts','/Library/Fonts','/System/Library/Fonts',
              os.path.expanduser('~/.fonts'),os.path.expanduser('~/.local/share/fonts'),'C:/Windows/Fonts'):
        hits=glob.glob(os.path.join(d,'**','DejaVuSansCondensed-Bold.ttf'),recursive=True)
        if hits: return sorted(hits)[0]
    raise SystemExit('DejaVuSansCondensed-Bold.ttf not found (install fonts-dejavu or set CHACHA_TTF)')
