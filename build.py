#!/usr/bin/env python3
"""Build the Akazukin ChaCha GB English translation from your own copy of the original ROM.

usage: python3 build.py --rom "Akazukin Chacha (Japan) (SGB Enhanced).gb" [--out build/] [--rgbds DIR] [--flips PATH]

Steps (all intermediate files go to <out>/work/):
  1. verify the ROM (MD5 9a5215658c60a1802b11f728c292b536)
  2. tools/re/extract.py        -> work/re/strings.json (string table: pointers, offsets, field sizes)
  3. translation/en.json is checked against the extracted ids -> work/tl/merged.json
  4. tools/engine/build.py      -> work/engine/chacha_en_text.gb (VWF engine, dialogue, name tables, fixed UI text;
                                   fonts generated into work/engine/font, the menu font's frame tiles from the ROM)
  5. tools/ui/build_ui.py       -> <out>/chacha_en.gb (UI layer: HUD, report card, results, password, title,
                                   graphics; ending pictures and signs are decompressed from the ROM and re-lettered)
  6. <out>/chacha_en.bps        (Flips if found, else tools/common/mkbps.py), verified by applying it
rgbds (rgbasm/rgblink) comes from --rgbds, $RGBDS_DIR or PATH; Flips from --flips, $FLIPS, PATH or the rgbds dir."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
ROM_MD5 = '9a5215658c60a1802b11f728c292b536'
TOOLS = os.path.join(REPO, 'tools')


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def rel(x):
    return os.path.relpath(x, REPO) if os.path.isabs(x) and x.startswith(REPO) else x


def run(args, env):
    print('+', ' '.join(rel(x) for x in args), flush=True)
    subprocess.check_call([sys.executable, '-I'] + args, env=env, cwd=REPO)


def find_rgbds(opt):
    d = opt or os.environ.get('RGBDS_DIR', '')
    tools = ('rgbasm', 'rgblink')
    if d:
        missing = [t for t in tools if not shutil.which(t, path=d)]
        if missing: sys.exit('rgbds: %s not found in %s' % (', '.join(missing), d))
        return os.path.abspath(d)
    missing = [t for t in tools if not shutil.which(t)]
    if missing: sys.exit('rgbds: %s not on PATH (install rgbds or pass --rgbds DIR)' % ', '.join(missing))
    return ''


def find_flips(opt, rgbds):
    for c in (opt, os.environ.get('FLIPS', '')):
        if c:
            p = shutil.which(c) or (c if os.path.isfile(c) else None)
            if not p: sys.exit('flips not found: %s' % c)
            return p
    p = shutil.which('flips') or shutil.which('flips-linux')
    if not p and rgbds: p = shutil.which('flips', path=rgbds)
    return p


def merge(en_path, strings_path, out_path):
    S = json.load(open(strings_path, encoding='utf-8'))
    ids = {s['id'] for s in S}
    en = json.load(open(en_path, encoding='utf-8'))
    unknown = [e['id'] for e in en if e['id'] not in ids]
    if unknown: sys.exit('translation/en.json has ids not found in the ROM: %s' % ', '.join(unknown[:20]))
    missing = sorted(ids - {e['id'] for e in en})
    if missing: print('warning: %d extracted strings have no translation: %s' % (len(missing), ', '.join(missing[:20])))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(en, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('merged %d translated strings (%d extracted) -> %s' % (len(en), len(S), rel(out_path)))


def make_bps(rom, final, bps, flips, env):
    if os.path.exists(bps): os.remove(bps)
    if flips:
        print('BPS: Flips (%s)' % flips, flush=True)
        r = subprocess.run([flips, '--create', '--bps-delta', rom, final, bps], capture_output=True, text=True)
        msg = [l for l in (r.stdout + r.stderr).replace('\r', '\n').splitlines() if l.strip() and not l.startswith('Please wait')]
        if msg: print(msg[-1])
        if not os.path.isfile(bps): sys.exit('flips failed to create %s' % bps)
        with tempfile.TemporaryDirectory() as td:
            chk = os.path.join(td, 'check.gb')
            subprocess.run([flips, '--apply', bps, rom, chk], capture_output=True, check=False)
            if not os.path.isfile(chk) or md5(chk) != md5(final): sys.exit('flips --apply does not reproduce %s' % final)
        print('BPS verified with flips --apply')
    else:
        print('BPS: Flips not found, using tools/common/mkbps.py', flush=True)
        run([os.path.join(TOOLS, 'common', 'mkbps.py'), 'make', rom, final, bps], env)
        with tempfile.TemporaryDirectory() as td:
            chk = os.path.join(td, 'check.gb')
            run([os.path.join(TOOLS, 'common', 'mkbps.py'), 'apply', rom, bps, chk], env)
            if md5(chk) != md5(final): sys.exit('mkbps.py apply does not reproduce %s' % final)
        print('BPS verified with mkbps.py apply')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rom', required=True, help='original Akazukin Chacha (Japan) (SGB Enhanced).gb')
    ap.add_argument('--out', default=os.path.join(REPO, 'build'), help='output directory (default: build/)')
    ap.add_argument('--rgbds', help='directory containing rgbasm/rgblink (default: $RGBDS_DIR or PATH)')
    ap.add_argument('--flips', help='Flips executable for the BPS (default: $FLIPS, PATH, rgbds dir; else mkbps.py)')
    a = ap.parse_args()

    rom = os.path.abspath(a.rom)
    if not os.path.isfile(rom): sys.exit('ROM not found: %s' % rom)
    h = md5(rom)
    if h != ROM_MD5:
        sys.exit('ROM MD5 %s does not match the required %s (Akazukin Chacha (Japan) (SGB Enhanced).gb)' % (h, ROM_MD5))
    print('ROM ok:', h)
    rgbds = find_rgbds(a.rgbds)
    flips = find_flips(a.flips, rgbds)

    out = os.path.abspath(a.out); work = os.path.join(out, 'work')
    os.makedirs(work, exist_ok=True)
    strings = os.path.join(work, 're', 'strings.json')
    env = dict(os.environ, CHACHA_ROM=rom, CHACHA_WORK=work, CHACHA_STRINGS=strings, RGBDS_DIR=rgbds)

    run([os.path.join(TOOLS, 're', 'extract.py'), rom, os.path.join(work, 're')], env)
    tl = os.path.join(work, 'tl', 'merged.json')
    merge(os.path.join(REPO, 'translation', 'en.json'), strings, tl)
    text_gb = os.path.join(work, 'engine', 'chacha_en_text.gb')
    run([os.path.join(TOOLS, 'engine', 'build.py'), '--tr', tl, '--out', text_gb,
         '--layout', os.path.join(work, 'engine', 'layout.json')], env)
    final = os.path.join(out, 'chacha_en.gb'); bps = os.path.join(out, 'chacha_en.bps')
    run([os.path.join(TOOLS, 'ui', 'build_ui.py'), text_gb, final, '--tr', tl], env)
    make_bps(rom, final, bps, flips, env)
    print('\n%s  %s\n%s  %s (%d bytes)' % (md5(final), final, md5(bps), bps, os.path.getsize(bps)))


if __name__ == '__main__':
    main()
