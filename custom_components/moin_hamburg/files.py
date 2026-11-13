"""Images and theme file on disk. Blocking: runs in the executor."""
from __future__ import annotations

import hashlib
import pathlib
import shutil
from dataclasses import dataclass, replace

from . import render
from .const import KEEP_IMAGES, THEME, THEME_STILL, URL_PATH

HEADER = '# Moin Hamburg: rewritten by the integration whenever the picture changes. Do not edit.'


@dataclass(frozen=True)
class Written:
    image: str            # URL of the animated image
    still: str            # URL of the still image
    theme_changed: bool   # the theme file is new or different: themes need a reload


class Files:
    def __init__(self, image_dir, theme_file):
        self.image_dir = pathlib.Path(image_dir)
        self.theme_file = pathlib.Path(theme_file)
        self._last = None

    def prepare(self):
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def write(self, key, scene, animated):
        """Draw both images for the key and point the themes at them.

        The image URLs carry a hash of the picture, so browsers never show a
        stale one after the renderer changed. The theme moin-hamburg shows the
        animated image only while animation is on; moin-hamburg-still never moves.
        """
        if self._last and self._last[0] == (key, animated):
            return replace(self._last[1], theme_changed=False)
        self.prepare()
        urls = []
        for moving, suffix in ((True, ''), (False, '-still')):
            svg = render.render(key, moving)
            name = f'{key}{suffix}.svg'
            _write(self.image_dir / name, svg)
            urls.append(f'{URL_PATH}/{name}?v={hashlib.sha256(svg.encode()).hexdigest()[:12]}')
        image, still = urls
        text = render.theme_yaml(scene, image if animated else still, still, (THEME, THEME_STILL), HEADER)
        changed = not self.theme_file.exists() or self.theme_file.read_text(encoding='utf-8') != text
        if changed:
            self.theme_file.parent.mkdir(parents=True, exist_ok=True)
            _write(self.theme_file, text)
        self._prune()
        written = Written(image, still, changed)
        self._last = ((key, animated), written)
        return written

    def _prune(self):
        images = sorted(self.image_dir.glob('*.svg'), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in images[2 * KEEP_IMAGES:]:
            old.unlink(missing_ok=True)

    def remove(self):
        """Everything the integration wrote, for when it is removed."""
        shutil.rmtree(self.image_dir, ignore_errors=True)
        self.theme_file.unlink(missing_ok=True)


def _write(path, text):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)
