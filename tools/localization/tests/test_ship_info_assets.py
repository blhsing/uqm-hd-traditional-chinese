from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "localization"))

from uqmloc.shipinfoassets import (  # noqa: E402
    SHIP_INFO_PAGES,
    SHIP_INFO_VARIANTS,
    SHIP_PICK_LABELS,
    _render_ship_info_frames,
    _wrap_cjk,
    build_localized_ship_info_assets,
)


class ShipInfoAssetTests(unittest.TestCase):
    def test_all_twenty_five_pages_have_stable_native_resource_mappings(self):
        self.assertEqual([page.index for page in SHIP_INFO_PAGES], list(range(25)))
        self.assertEqual(len({page.stem for page in SHIP_INFO_PAGES}), 25)
        self.assertEqual(SHIP_INFO_PAGES[0].stem, "androsynth")
        self.assertEqual(SHIP_INFO_PAGES[-1].stem, "zoqfot")
        self.assertTrue(all(page.name and page.weapon and page.special for page in SHIP_INFO_PAGES))
        self.assertEqual(
            [
                (variant.addon, variant.ui_prefix, variant.spin_prefix, variant.canvas)
                for variant in SHIP_INFO_VARIANTS
            ],
            [
                ("zh_TW", "base/ui", "base/cutscene/spins", (320, 240)),
                (
                    "hires2x-zh_TW",
                    "addons/hires2x/ui",
                    "addons/hires2x/cutscene/spins",
                    (640, 480),
                ),
                (
                    "hires4x-zh_TW",
                    "addons/hires4x/ui",
                    "addons/hires4x/cutscene/spins",
                    (1280, 960),
                ),
            ],
        )

    def test_picker_wording_is_localized(self):
        self.assertEqual(SHIP_PICK_LABELS["pick_ship"], "選擇船艦")
        self.assertEqual(SHIP_PICK_LABELS["ship_info"], "船艦資料")
        self.assertEqual(SHIP_PICK_LABELS["more_ships"], "想要更多船艦？")

    def test_canonical_race_names_and_closing_punctuation(self):
        self.assertEqual(SHIP_INFO_PAGES[1].name, "阿里盧拉萊萊・小艇")
        self.assertEqual(SHIP_INFO_PAGES[3].name, "克姆爾混合種・化身艦")

        class FixedWidthDraw:
            @staticmethod
            def textbbox(_position, text, font=None):
                del font
                return (0, 0, len(text) * 10, 10)

        self.assertEqual(
            _wrap_cjk(FixedWidthDraw(), "甲乙丙。", None, 30),
            ["甲乙", "丙。"],
        )

    @unittest.skipUnless(
        Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf").is_file(),
        "Noto Sans TC variable font is not installed",
    )
    def test_one_page_build_is_deterministic_and_uses_shadow_paths(self):
        from PIL import Image, ImageDraw

        base = Image.new("RGB", (320, 240), (9, 11, 23))
        draw = ImageDraw.Draw(base)
        draw.rectangle((0, 23, 319, 92), fill=(88, 88, 88))
        draw.rectangle((80, 49, 84, 55), fill=(230, 230, 230))
        draw.rectangle((258, 62, 315, 89), fill=(4, 5, 91))
        base_buffer = io.BytesIO()
        base.save(base_buffer, format="PNG")
        base.close()

        picker = Image.new("RGB", (128, 98), (128, 128, 124))
        picker_buffer = io.BytesIO()
        picker.save(picker_buffer, format="PNG")
        picker.close()

        class Resolver:
            @staticmethod
            def read_bytes(path: str) -> bytes:
                if path == "base/ui/meleemenu-027.png":
                    return picker_buffer.getvalue()
                if path == "base/cutscene/spins/ship00.ani":
                    return (
                        b"androsynth.png -2 -1 0 0\n"
                        b"androsynth-ovl.png -2 -1 0 0\n"
                    )
                if path == "base/cutscene/spins/androsynth.png":
                    return base_buffer.getvalue()
                raise AssertionError(f"unexpected resource: {path}")

        variant = SHIP_INFO_VARIANTS[0]
        page = SHIP_INFO_PAGES[0]
        font = Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            with patch(
                "uqmloc.shipinfoassets.SHIP_INFO_VARIANTS", (variant,)
            ), patch("uqmloc.shipinfoassets.SHIP_INFO_PAGES", (page,)):
                first_report = build_localized_ship_info_assets(
                    Resolver(), first, font
                )
                second_report = build_localized_ship_info_assets(
                    Resolver(), second, font
                )

            expected = (
                "base/ui/meleemenu-027.png",
                "base/cutscene/spins/ship00.ani",
                "base/cutscene/spins/androsynth.png",
                "base/cutscene/spins/androsynth-ovl.png",
            )
            for relative in expected:
                first_file = first / "zh_TW" / Path(relative)
                second_file = second / "zh_TW" / Path(relative)
                with self.subTest(resource=relative):
                    self.assertTrue(first_file.is_file())
                    self.assertEqual(first_file.read_bytes(), second_file.read_bytes())

            report = first_report["zh_TW"]
            self.assertEqual(report["ship_info"]["pages"], 1)
            self.assertTrue(report["ship_info"]["native_resolution"])
            self.assertEqual(len(report["files"]), 4)
            with Image.open(
                first / "zh_TW/base/cutscene/spins/androsynth.png"
            ) as rendered_base:
                self.assertEqual(rendered_base.size, (320, 240))
                # A long English tagline may extend left of the nominal header;
                # the complete stock wording must be removed.
                self.assertEqual(
                    rendered_base.convert("RGB").getpixel((82, 52)),
                    (80, 80, 80),
                )
                # An untouched corner of the battle artwork remains intact.
                self.assertEqual(rendered_base.convert("RGB").getpixel((2, 150)), (9, 11, 23))
            with Image.open(
                first / "zh_TW/base/cutscene/spins/androsynth-ovl.png"
            ) as rendered_overlay:
                self.assertEqual(rendered_overlay.size, (320, 240))
                self.assertIsNotNone(rendered_overlay.convert("RGBA").getchannel("A").getbbox())

    @unittest.skipUnless(
        Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf").is_file(),
        "Noto Sans TC variable font is not installed",
    )
    def test_shofixti_portrait_readout_is_localized(self):
        from PIL import Image, ImageDraw, ImageFont

        source = Image.new("RGB", (1280, 960), (9, 11, 23))
        draw = ImageDraw.Draw(source)
        draw.rectangle((1036, 204, 1168, 232), fill=(211, 17, 31))
        base, overlay = _render_ship_info_frames(
            Image,
            ImageDraw,
            ImageFont,
            source,
            SHIP_INFO_PAGES[13],
            Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf"),
        )
        source.close()
        overlay.close()
        panel = base.convert("RGB").crop((1036, 204, 1168, 232))
        raw = panel.tobytes()
        pixels = {raw[index : index + 3] for index in range(0, len(raw), 3)}
        self.assertNotIn(bytes((211, 17, 31)), pixels)
        self.assertGreater(len(pixels), 1)
        panel.close()
        base.close()


if __name__ == "__main__":
    unittest.main()
