from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class MousePressSnapshotTests(unittest.TestCase):
    def test_sdl_button_down_captures_press_position_atomically(self):
        header = (REPO_ROOT / "game/src/libs/inplib.h").read_text(encoding="utf-8")
        source = (REPO_ROOT / "game/src/libs/input/sdl/input.c").read_text(
            encoding="utf-8"
        )

        for field in ("press_x", "press_y", "press_inside_viewport"):
            self.assertIn(field, header)
        button_down = source.index("case SDL_MOUSEBUTTONDOWN:")
        generation = source.index("++MouseState.press_generation;", button_down)
        capture = source.index("MouseState.press_x = MouseState.x;", button_down)
        self.assertLess(capture, generation)
        self.assertIn(
            "MouseState.press_inside_viewport = MouseState.inside_viewport;",
            source[button_down:generation],
        )

    def test_every_clickable_surface_targets_press_coordinates(self):
        sources = {
            "restart": REPO_ROOT / "game/src/uqm/restart.c",
            "melee": REPO_ROOT / "game/src/uqm/supermelee/melee.c",
            "buildpick": REPO_ROOT / "game/src/uqm/supermelee/buildpick.c",
            "pickmele": REPO_ROOT / "game/src/uqm/supermelee/pickmele.c",
        }
        for name, path in sources.items():
            source = path.read_text(encoding="utf-8")
            with self.subTest(surface=name):
                self.assertIn("press_inside_viewport", source)
                self.assertIn("press_x", source)
                self.assertIn("press_y", source)


class SuperMeleeStatsCardTests(unittest.TestCase):
    def test_shared_card_contains_performance_and_energy_fields(self):
        melee = (REPO_ROOT / "game/src/uqm/supermelee/melee.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("DrawMeleeShipStatsCard", melee)
        for label in ("船員", "能量", "極速", "加速", "轉向", "回能", "武器", "特技"):
            self.assertIn(label, melee)
        self.assertIn("max_thrust >> RESOLUTION_FACTOR", melee)

    def test_both_picker_surfaces_call_shared_card(self):
        buildpick = (
            REPO_ROOT / "game/src/uqm/supermelee/buildpick.c"
        ).read_text(encoding="utf-8")
        pickmele = (
            REPO_ROOT / "game/src/uqm/supermelee/pickmele.c"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(buildpick.count("DrawMeleeShipStatsCard"), 2)
        self.assertIn("GetBuildPickStatsRect", buildpick)
        self.assertIn("popupRect.corner.y + popupRect.extent.height", buildpick)
        self.assertIn("BoxUnion (&popupRect, &statsRect, r);", buildpick)
        self.assertIn("DrawMeleeShipStatsCard", pickmele)
        self.assertIn("隨機選船", pickmele)
        self.assertIn("返回隊伍設定", pickmele)


if __name__ == "__main__":
    unittest.main()
