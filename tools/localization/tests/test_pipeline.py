from __future__ import annotations

import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uqmloc.core import (  # noqa: E402
    LocError,
    document_contract,
    parse_rmp,
    parse_string_document,
    render_document,
    write_json,
)
from uqmloc.builder import UI_FONT_METRICS, _zip_tree  # noqa: E402
from patch_stored_member import (  # noqa: E402
    PADDING_NAME,
    fit_zip_to_size,
    patch_stored_member,
)
from uqmloc.fontgen import (  # noqa: E402
    FontMetrics,
    NotoRenderer,
    glyph_filename,
    observe_font_metrics,
)
from uqmloc.menuassets import (  # noqa: E402
    KEY_HELP_VARIANTS,
    MENU_NORMAL_COLOR,
    MENU_SELECTED_COLOR,
    STATUS_LABEL_VARIANTS,
    SUPER_MELEE_BUTTON_LABELS,
    SUPER_MELEE_CONTROL_LABELS,
    SUPER_MELEE_TITLE,
    SUPER_MELEE_VARIANTS,
    _effect_map_from_mask,
    _status_text_mask,
)
from uqmloc.translation_io import export_records, merge_records  # noqa: E402
from uqmloc.validation import validate_documents  # noqa: E402
from uqmloc.wrapping import split_cjk_token, wrap_translation  # noqa: E402


def make_document(path: str, text: str, resource_type: str = "STRTAB"):
    return parse_string_document(
        text.encode("utf-8"), path, ["test.resource"], [resource_type]
    )


class RmpTests(unittest.TestCase):
    def test_parse_rmp_preserves_conversation_fields(self):
        entries = parse_rmp(
            "# comment\ncomm.a.dialogue = CONVERSATION:base/a.txt:addons/voice/:addons/voice/a.ts\n"
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].fields, ("base/a.txt", "addons/voice/", "addons/voice/a.ts"))
        self.assertEqual(entries[0].format(), "comm.a.dialogue = CONVERSATION:base/a.txt:addons/voice/:addons/voice/a.ts")


class StringTableTests(unittest.TestCase):
    def test_round_trip_preserves_space_and_tab_audio_headers(self):
        source = "#(ONE) clip-001.ogg\r\nHello\r\n\r\n#(two)\tclip-002.ogg\r\nWorld\r\n"
        document = make_document("base/comm/test/test.txt", source, "CONVERSATION")
        self.assertEqual(document["entries"][0]["audio"], "clip-001.ogg")
        self.assertEqual(document["entries"][1]["audio"], "clip-002.ogg")
        self.assertEqual(render_document(document), source.encode("utf-8"))

    def test_slideshow_exposes_only_tfi_payload(self):
        source = "#(timing)\nSYNC 5000\n\n#(subtitle)\nTFI Visible line\ncontinued\n"
        document = make_document("base/cutscene/intro/intro.txt", source)
        self.assertEqual(document["entries"][0]["unit_kind"], "immutable")
        self.assertIsNone(document["entries"][0]["translation"])
        subtitle = document["entries"][1]
        self.assertEqual(subtitle["unit_kind"], "slideshow-tfi")
        self.assertEqual(subtitle["translation"], "Visible line\ncontinued")
        subtitle["translation"] = "可見字幕"
        rendered = render_document(document).decode("utf-8")
        self.assertIn("SYNC 5000", rendered)
        self.assertIn("TFI 可見字幕", rendered)

    def test_contract_rejects_immutable_label_change(self):
        document = make_document("base/test.txt", "#(A)\nText\n")
        before = document_contract(document)
        document["entries"][0]["label"] = "B"
        self.assertNotEqual(document_contract(document), before)


class WrappingTests(unittest.TestCase):
    def test_cjk_words_receive_ascii_breaks(self):
        wrapped = split_cjk_token("這是一段很長的繁體中文句子。", 4)
        self.assertIn(" ", wrapped)
        self.assertTrue(all(len(part) <= 4 for part in wrapped.split(" ")))

    def test_closing_punctuation_never_pushes_chunk_past_limit(self):
        wrapped = split_cjk_token("一二三四五六七八九十甲乙，丙丁", 12)
        self.assertLessEqual(max(len(part) for part in wrapped.split(" ")), 12)
        self.assertNotIn(" ，", wrapped)

    def test_markers_survive_wrap_and_physical_lines_fit(self):
        source = "$*這是一段非常長的測試文字*$"
        wrapped = wrap_translation(source, max_cjk_token=4, max_line_bytes=18)
        self.assertEqual(wrapped.count("$"), 2)
        self.assertTrue(all(len(line.encode("utf-8")) <= 18 for line in wrapped.split("\n")))


class ValidationTests(unittest.TestCase):
    def test_rejects_non_bmp_and_new_entry_injection(self):
        document = make_document("base/test.txt", "#(A)\nText\n")
        document["entries"][0]["translation"] = "😀\n#(BAD)"
        errors = validate_documents([document], max_cjk_token=100)
        self.assertTrue(any("outside" in error for error in errors))
        self.assertTrue(any("starts with #" in error for error in errors))


class FontTests(unittest.TestCase):
    @staticmethod
    def png_header(width: int, height: int) -> bytes:
        return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", width, height)

    def test_observed_metrics_use_capital_canvas(self):
        files = {
            "00041.png": self.png_header(8, 12),
            "0004d.png": self.png_header(10, 12),
            "00061.png": self.png_header(30, 40),
        }
        metrics = observe_font_metrics(files)
        self.assertEqual((metrics.width, metrics.height), (10, 12))
        self.assertEqual(glyph_filename("一"), "04e00.png")

    def test_hd_ui_metric_overrides_respect_fixed_hud_bands(self):
        self.assertEqual(
            UI_FONT_METRICS,
            {
                ("hires2x-zh_TW", "starcon.fon"): (14, 14),
                ("hires2x-zh_TW", "tiny.fon"): (14, 14),
                ("hires2x-zh_TW", "micro.fon"): (12, 15),
                ("hires4x-zh_TW", "starcon.fon"): (20, 19),
                ("hires4x-zh_TW", "tiny.fon"): (20, 20),
                ("hires4x-zh_TW", "micro.fon"): (24, 30),
            },
        )

    @unittest.skipUnless(
        Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf").is_file(),
        "Noto Sans TC variable font is not installed",
    )
    def test_variable_font_uses_legible_bold_weight(self):
        from PIL import Image

        renderer = NotoRenderer(Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf"))
        raw = renderer.render("星", FontMetrics(18, 17, 1))
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
        opaque = sum(
            alpha >= 250
            for alpha in image.getchannel("A").get_flattened_data()
        )
        self.assertGreaterEqual(opaque, 30)

    @unittest.skipUnless(
        Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf").is_file(),
        "Noto Sans TC variable font is not installed",
    )
    def test_generated_hud_ink_fits_sis_fields(self):
        from PIL import Image

        renderer = NotoRenderer(Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf"))
        cases = (
            # label, metrics, text, baseline, inclusive top, exclusive bottom
            ("4x sun", (20, 20), "太陽", 21, 0, 28),
            ("4x date", (20, 20), "一二三四五六七八九十月", 18, 0, 24),
            ("4x captain label", (20, 20), "船長", 27, 9, 30),
            ("4x captain name", (20, 20), "澤爾尼克", 48, 32, 51),
            ("4x fuel", (20, 20), "燃料", 118, 102, 120),
            ("4x crew", (20, 20), "船員", 373, 357, 374),
            ("4x ship name", (20, 19), "維迦凱特", 78, 63, 81),
            ("2x date", (14, 14), "一二三四五六七八九十月", 10, 0, 14),
        )
        for label, size, text, baseline, field_top, field_bottom in cases:
            metrics = FontMetrics(*size, 1)
            # gfxload.c uses height - 3 as the hotspot for canvases over 9px.
            canvas_top = baseline - (metrics.height - 3)
            for character in text:
                with self.subTest(field=label, character=character):
                    raw = renderer.render(character, metrics)
                    image = Image.open(io.BytesIO(raw)).convert("RGBA")
                    bbox = image.getchannel("A").getbbox()
                    self.assertIsNotNone(bbox)
                    assert bbox is not None
                    self.assertGreaterEqual(canvas_top + bbox[1], field_top)
                    self.assertLessEqual(canvas_top + bbox[3], field_bottom)


class PackageTests(unittest.TestCase):
    def test_shadow_archive_entries_are_rooted_at_base_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "hires4x-zh_TW"
            asset = source / "base" / "ui" / "newgame4x.ani"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"menu")
            destination = root / "hires4x-zh_TW-shadow.uqm"

            count = _zip_tree(source, destination, include_root=False)

            self.assertEqual(count, 1)
            with zipfile.ZipFile(destination) as archive:
                self.assertEqual(archive.namelist(), ["base/ui/newgame4x.ani"])
                self.assertEqual(archive.read("base/ui/newgame4x.ani"), b"menu")

    def test_nested_archives_are_stored_to_avoid_double_deflate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "hires4x-zh_TW"
            regular = source / "base" / "ui" / "newgame4x.ani"
            nested = source / "shadow-content" / "hires4x-zh_TW-shadow.uqm"
            regular.parent.mkdir(parents=True)
            nested.parent.mkdir(parents=True)
            regular.write_bytes(b"menu")
            nested.write_bytes(b"nested archive")
            destination = root / "hires4x-zh_TW.uqm"

            _zip_tree(source, destination, include_root=True)

            with zipfile.ZipFile(destination) as archive:
                self.assertEqual(
                    archive.getinfo("hires4x-zh_TW/base/ui/newgame4x.ani").compress_type,
                    zipfile.ZIP_DEFLATED,
                )
                self.assertEqual(
                    archive.getinfo(
                        "hires4x-zh_TW/shadow-content/hires4x-zh_TW-shadow.uqm"
                    ).compress_type,
                    zipfile.ZIP_STORED,
                )

    def test_equal_size_nested_archive_refresh_updates_outer_crc(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "inner-source.uqm"
            with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("base/ui/asset.png", b"new runtime asset")

            target_size = source.stat().st_size + 400
            fitted = root / "inner-fitted.uqm"
            fit_zip_to_size(source, fitted, target_size)
            self.assertEqual(fitted.stat().st_size, target_size)
            with zipfile.ZipFile(fitted) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn(PADDING_NAME, archive.namelist())

            member = "addon/shadow-content/inner.uqm"
            outer = root / "outer.uqm"
            with zipfile.ZipFile(outer, "w", allowZip64=False) as archive:
                info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, bytes(target_size), compress_type=zipfile.ZIP_STORED)
                archive.writestr("addon/metadata.txt", b"unchanged")

            patch_stored_member(outer, member, fitted)

            with zipfile.ZipFile(outer) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read(member), fitted.read_bytes())
                self.assertEqual(archive.read("addon/metadata.txt"), b"unchanged")


class MenuAssetTests(unittest.TestCase):
    def test_additive_effect_map_encodes_coverage_in_rgb(self):
        from PIL import Image

        mask = Image.new("L", (3, 1))
        mask.putdata((0, 128, 255))
        effect = _effect_map_from_mask(Image, mask, MENU_SELECTED_COLOR)
        self.assertEqual(effect.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertEqual(effect.getpixel((1, 0)), (128, 120, 0, 255))
        self.assertEqual(effect.getpixel((2, 0)), MENU_SELECTED_COLOR)

    def test_selected_label_pulses_blue_to_yellow_not_red_to_red(self):
        normal = MENU_NORMAL_COLOR[:3]
        effect = MENU_SELECTED_COLOR[:3]
        low = tuple(round(base - value * 3 / 16) for base, value in zip(normal, effect))
        high = tuple(round(base + value * 3 / 16) for base, value in zip(normal, effect))
        self.assertGreater(low[2] - low[0], 40)
        self.assertGreater(high[0] - high[2], 40)
        self.assertGreater(high[1] - high[2], 25)

    def test_native_help_status_and_melee_paths_match_resolution_rmps(self):
        self.assertEqual(
            [variant.output_path for variant in KEY_HELP_VARIANTS],
            [
                "base/ui/submenustarmapkeys-000.png",
                "addons/hires2x/ui/submenustarmapkeys-000.png",
                "addons/hires4x/ui/submenustarmapkeys-000.png",
            ],
        )
        self.assertEqual(
            [
                (
                    variant.output_prefix,
                    variant.crew_size,
                    variant.energy_size,
                    variant.crew_output_size,
                    variant.energy_output_size,
                    variant.font_weight,
                    variant.font_size,
                )
                for variant in STATUS_LABEL_VARIANTS
            ],
            [
                ("base/ui", (22, 5), (21, 5), (22, 8), (21, 8), 500, 6),
                (
                    "addons/hires2x/ui",
                    (22, 5),
                    (22, 5),
                    (22, 10),
                    (22, 10),
                    450,
                    8,
                ),
                (
                    "addons/hires4x/ui",
                    (44, 9),
                    (44, 9),
                    (44, 18),
                    (44, 18),
                    400,
                    16,
                ),
            ],
        )
        self.assertEqual(
            [
                (variant.addon, variant.output_prefix, variant.scale)
                for variant in SUPER_MELEE_VARIANTS
            ],
            [
                ("zh_TW", "base/ui", 1),
                ("hires2x-zh_TW", "addons/hires2x/ui", 2),
                ("hires4x-zh_TW", "addons/hires4x/ui", 4),
            ],
        )

    def test_status_output_canvases_materially_enlarge_every_label(self):
        for variant in STATUS_LABEL_VARIANTS:
            self.assertGreaterEqual(
                variant.crew_output_size[1], round(variant.crew_size[1] * 1.6)
            )
            self.assertGreaterEqual(
                variant.energy_output_size[1], round(variant.energy_size[1] * 1.6)
            )

    def test_compact_chinese_status_masks_are_crisp_and_bounded(self):
        from PIL import Image, ImageDraw, ImageFont

        for label in ("人", "力"):
            mask = _status_text_mask(
                Image, ImageDraw, ImageFont, Path("unused.ttf"), label, (22, 5)
            )
            self.assertEqual(mask.size, (22, 5))
            self.assertIsNotNone(mask.getbbox())
            self.assertTrue(
                all(value in (0, 255) for value in mask.get_flattened_data())
            )

    @unittest.skipUnless(
        Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf").is_file(),
        "Noto Sans TC variable font is not installed",
    )
    def test_status_label_optical_sizes_keep_4x_strokes_open(self):
        from PIL import Image, ImageDraw, ImageFont

        font_path = Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf")
        expected = {
            ("zh_TW", "船員"): ((5, 0, 18, 8), (22, 8)),
            ("zh_TW", "能量"): ((4, 1, 17, 8), (21, 8)),
            ("hires2x-zh_TW", "船員"): ((3, 1, 19, 10), (22, 10)),
            ("hires2x-zh_TW", "能量"): ((2, 1, 19, 10), (22, 10)),
            ("hires4x-zh_TW", "船員"): ((6, 1, 38, 17), (44, 18)),
            ("hires4x-zh_TW", "能量"): ((6, 2, 38, 17), (44, 18)),
        }
        for variant in STATUS_LABEL_VARIANTS:
            for label, size in (
                ("船員", variant.crew_output_size),
                ("能量", variant.energy_output_size),
            ):
                with self.subTest(addon=variant.addon, label=label):
                    mask = _status_text_mask(
                        Image,
                        ImageDraw,
                        ImageFont,
                        font_path,
                        label,
                        size,
                        font_weight=variant.font_weight,
                        font_size=variant.font_size,
                    )
                    self.assertEqual(
                        (mask.getbbox(), mask.size), expected[(variant.addon, label)]
                    )
                    if variant.addon == "hires4x-zh_TW":
                        coverage = sum(mask.get_flattened_data()) / 255
                        self.assertGreater(coverage, 150)
                        self.assertLess(coverage, 200)

    def test_clean_super_melee_templates_and_labels_are_complete(self):
        from PIL import Image

        root = ROOT.parents[1] / "localization" / "menu-assets" / "source" / "super-melee"
        expected = {
            "background-4x.png": (1280, 960),
            "battle-4x.png": (193, 258),
            **{
                f"{control}-{state}-4x.png": (232, 116)
                for control in ("human", "weak", "good", "awesome", "network")
                for state in ("normal", "selected")
            },
        }
        for filename, size in expected.items():
            with self.subTest(filename=filename):
                with Image.open(root / filename) as image:
                    self.assertEqual(image.size, size)
                    self.assertNotIn("icc_profile", image.info)
        self.assertEqual(SUPER_MELEE_TITLE, "超級對戰")
        self.assertEqual(
            ["".join(lines) for lines in SUPER_MELEE_CONTROL_LABELS],
            ["玩家操控", "簡易電腦", "普通電腦", "最強電腦"],
        )
        self.assertEqual(
            SUPER_MELEE_BUTTON_LABELS,
            {
                "LOAD": "載入",
                "SAVE": "儲存",
                "NET": "連線",
                "BATTLE": "開戰！",
                "QUIT": "離開",
            },
        )


class RecordIoTests(unittest.TestCase):
    def test_flat_record_export_and_partial_merge(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            document = make_document("base/test.txt", "#(A)\nSource\n")
            document["contract_sha256"] = document_contract(document)
            relative = "resources/base/test.txt.json"
            write_json(workspace / relative, document)
            write_json(
                workspace / "manifest.json",
                {
                    "format": document["format"],
                    "document_count": 1,
                    "resources": [
                        {
                            "source_path": "base/test.txt",
                            "json": relative,
                            "contract_sha256": document["contract_sha256"],
                        }
                    ],
                },
            )
            records = root / "records.json"
            self.assertEqual(export_records(workspace, records, json_lines=False), 1)
            payload = json.loads(records.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["id"], "base/test.txt::0")
            payload[0]["text"] = "繁體中文"
            response = root / "response.json"
            response.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            merged, count = merge_records(
                workspace,
                response,
                output=root / "merged",
                in_place=False,
                allow_partial=False,
            )
            self.assertEqual(count, 1)
            merged_document = json.loads((merged / relative).read_text(encoding="utf-8"))
            self.assertEqual(merged_document["entries"][0]["translation"], "繁體中文")


if __name__ == "__main__":
    unittest.main()
