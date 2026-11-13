#!/usr/bin/env python3
"""Render state keys to SVG files plus an HTML page to look at them.

    gallery.py OUTDIR [KEY ...]     default: all golden cases
    gallery.py OUTDIR --still ...   still images instead of animated ones

Open OUTDIR/index.html in a browser.
"""
import html
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'custom_components' / 'moin_hamburg'), str(ROOT / 'tools')]

import golden  # noqa: E402
import render  # noqa: E402

PAGE = '''<!doctype html><meta charset="utf-8"><title>Moin Hamburg gallery</title>
<style>body{{margin:0;padding:16px;background:#111;color:#ddd;font:14px system-ui}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px}}
figure{{margin:0}}img{{width:100%;aspect-ratio:1200/844;display:block;border-radius:6px}}
figcaption{{padding:4px 2px;word-break:break-all;color:#9ab}}</style>
<div class="g">{items}</div>'''


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    out = pathlib.Path(argv[0])
    still = '--still' in argv
    keys = [a for a in argv[1:] if a != '--still'] or golden.cases()
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for key in keys:
        name = f'{key}{"-still" if still else ""}.svg'
        (out / name).write_text(render.render(key, not still), encoding='utf-8')
        items.append(f'<figure><img src="{html.escape(name)}" loading="lazy"><figcaption>{html.escape(key)}</figcaption></figure>')
    (out / 'index.html').write_text(PAGE.format(items='\n'.join(items)), encoding='utf-8')
    print(f'{len(keys)} images in {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
