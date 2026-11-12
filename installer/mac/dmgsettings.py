"""dmgbuild settings: fancy drag-to-Applications layout (paths relative to repo root)."""
from __future__ import annotations

files = ["dist/CineForge AI.app", "installer/mac/LEGGIMI.txt"]
symlinks = {"Applications": "/Applications"}
background = "installer/mac/assets/background.png"

window_rect = ((120, 140), (920, 560))
default_view = "icon-view"
icon_size = 96
text_size = 13

icon_locations = {
    "CineForge AI.app": (250, 250),
    "Applications": (640, 250),
    "LEGGIMI.txt": (445, 420),
    ".background": (0, -1000),
}
