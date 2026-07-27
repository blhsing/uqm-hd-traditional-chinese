from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .core import ContentResolver, LocError


MENU_LABELS = ("新遊戲", "載入遊戲", "超級對戰", "設定", "離開")
MENU_FONT_WEIGHT = 500
# The restart menu does not alpha-composite its selected frame.  It adds and
# subtracts that frame at only 3/16 strength.  A neutral base plus a yellow
# effect map therefore makes the selected label pulse blue <-> yellow, while
# every unselected label remains a steady light gray.  Baking red into the
# base can never produce a cyan selected label because the red channel is
# already saturated before the effect is applied.
MENU_NORMAL_COLOR = (160, 160, 160, 255)
MENU_SELECTED_COLOR = (255, 240, 0, 255)
MENU_KEY_HELP = "↑↓ 選擇　Enter 確認"
MENU_KEY_HELP_COLOR = (175, 225, 235, 255)


@dataclass(frozen=True)
class MenuVariant:
    addon: str
    stem: str


@dataclass(frozen=True)
class MenuFrame:
    filename: str
    width: int
    height: int
    x: int
    y: int


MENU_VARIANTS = (
    MenuVariant("zh_TW", "newgame"),
    MenuVariant("hires2x-zh_TW", "newgame2x"),
    MenuVariant("hires4x-zh_TW", "newgame4x"),
)


@dataclass(frozen=True)
class KeyHelpVariant:
    addon: str
    source_path: str
    output_path: str


KEY_HELP_VARIANTS = (
    KeyHelpVariant(
        "zh_TW",
        "base/ui/submenustarmapkeys-000.png",
        "base/ui/submenustarmapkeys-000.png",
    ),
    KeyHelpVariant(
        "hires2x-zh_TW",
        "addons/hires2x/ui/submenustarmapkeys-000.png",
        "addons/hires2x/ui/submenustarmapkeys-000.png",
    ),
    KeyHelpVariant(
        "hires4x-zh_TW",
        "addons/hires4x/ui/submenustarmapkeys-000.png",
        "addons/hires4x/ui/submenustarmapkeys-000.png",
    ),
)


@dataclass(frozen=True)
class StatusLabelVariant:
    addon: str
    source_prefix: str
    output_prefix: str
    crew_size: tuple[int, int]
    energy_size: tuple[int, int]
    crew_output_size: tuple[int, int]
    energy_output_size: tuple[int, int]


STATUS_LABEL_VARIANTS = (
    StatusLabelVariant(
        "zh_TW",
        "base/ui",
        "base/ui",
        (22, 5),
        (21, 5),
        (22, 8),
        (21, 8),
    ),
    StatusLabelVariant(
        "hires2x-zh_TW",
        "addons/hires2x/ui",
        "addons/hires2x/ui",
        (22, 5),
        (22, 5),
        (22, 10),
        (22, 10),
    ),
    StatusLabelVariant(
        "hires4x-zh_TW",
        "addons/hires4x/ui",
        "addons/hires4x/ui",
        (44, 9),
        (44, 9),
        (44, 18),
        (44, 18),
    ),
)


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError as exc:
        raise LocError(
            "Main-menu generation requires Pillow. Run: python -m pip install -r requirements.txt"
        ) from exc
    return Image, ImageDraw, ImageFont


def _menu_font(
    ImageFont,
    font_path: Path,
    size: int,
    weight: int = MENU_FONT_WEIGHT,
):
    try:
        font = ImageFont.truetype(str(font_path), size=size)
        axes = font.get_variation_axes()
        values = [axis["default"] for axis in axes]
        for index, axis in enumerate(axes):
            name = axis.get("name", b"")
            if isinstance(name, bytes):
                name = name.decode("ascii", errors="ignore")
            if str(name).lower() == "weight":
                values[index] = min(axis["maximum"], max(axis["minimum"], weight))
        if axes:
            font.set_variation_by_axes(values)
        return font
    except (AttributeError, OSError) as exc:
        if isinstance(exc, OSError) and "variation" not in str(exc).lower():
            raise LocError(f"Pillow cannot load {font_path}: {exc}") from exc
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError as inner:
            raise LocError(f"Pillow cannot load {font_path}: {inner}") from inner


def _parse_frames(
    resolver: ContentResolver, stem: str, Image
) -> tuple[bytes, list[MenuFrame]]:
    ani_path = f"base/ui/{stem}.ani"
    raw = resolver.read_bytes(ani_path)
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise LocError(f"{ani_path}: expected an ASCII animation manifest") from exc
    rows = [line for line in text.splitlines() if line.strip()]
    if len(rows) != 6:
        raise LocError(f"{ani_path}: expected six menu frames, found {len(rows)}")
    frames: list[MenuFrame] = []
    for row in rows:
        fields = row.split()
        if len(fields) != 5:
            raise LocError(f"{ani_path}: malformed animation row: {row!r}")
        filename = fields[0]
        try:
            hotspot_x, hotspot_y = int(fields[-2]), int(fields[-1])
        except ValueError as exc:
            raise LocError(f"{ani_path}: invalid animation hotspot: {row!r}") from exc
        image = Image.open(io.BytesIO(resolver.read_bytes(f"base/ui/{filename}")))
        try:
            width, height = image.size
        finally:
            image.close()
        frames.append(
            MenuFrame(filename, width, height, -hotspot_x, -hotspot_y)
        )
    return raw, frames


def _measure_tracked(draw, text: str, font, tracking: int, stroke_width: int):
    boxes = [
        draw.textbbox((0, 0), character, font=font, stroke_width=stroke_width)
        for character in text
    ]
    width = sum(box[2] - box[0] for box in boxes) + tracking * max(0, len(text) - 1)
    top = min(box[1] for box in boxes)
    bottom = max(box[3] for box in boxes)
    return boxes, width, top, bottom


def _draw_tracked_centered(
    image,
    ImageDraw,
    ImageFont,
    font_path: Path,
    text: str,
    *,
    fill: tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    # Menu labels are large artwork, not the tiny in-game bitmap font. Medium
    # weight without a synthetic outline matches the original menu's lighter
    # visual rhythm while remaining clear at all three resolutions.
    stroke_width = 0
    size = max(8, round(image.height * 0.74))
    while True:
        font = _menu_font(ImageFont, font_path, size)
        tracking = max(1, round(size * 0.12))
        boxes, width, top, bottom = _measure_tracked(
            draw, text, font, tracking, stroke_width
        )
        if width <= image.width * 0.90 or size <= 8:
            break
        size -= 1
    x = (image.width - width) / 2
    y = (image.height - (bottom - top)) / 2 - top
    for character, box in zip(text, boxes):
        draw.text(
            (round(x - box[0]), round(y)),
            character,
            font=font,
            fill=fill,
        )
        x += box[2] - box[0] + tracking


def _effect_map_from_mask(Image, mask, color: tuple[int, int, int, int]):
    """Encode antialias coverage in RGB for UQM's additive draw mode.

    The legacy additive renderer treats every non-transparent PNG pixel as a
    full-strength sample, so a conventional variable-alpha edge turns into a
    hard fringe.  Premultiplying the effect color into RGB and using binary
    alpha preserves the intended coverage in this particular compositor.
    """

    channels = [
        mask.point(lambda coverage, component=component: round(coverage * component / 255))
        for component in color[:3]
    ]
    alpha = mask.point(lambda coverage: 255 if coverage else 0)
    return Image.merge("RGBA", (*channels, alpha))


def _draw_menu_key_help(background, Image, ImageDraw, ImageFont, font_path: Path) -> None:
    draw = ImageDraw.Draw(background)
    size = max(9, round(background.height * 0.029))
    while True:
        font = _menu_font(ImageFont, font_path, size, weight=550)
        box = draw.textbbox((0, 0), MENU_KEY_HELP, font=font)
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width <= background.width * 0.78 or size <= 9:
            break
        size -= 1

    x = round((background.width - width) / 2)
    y = round(background.height - height - max(3, size * 0.45) - box[1])
    padding_x = max(4, round(size * 0.65))
    padding_y = max(2, round(size * 0.28))
    layer = Image.new("RGBA", background.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.rounded_rectangle(
        (
            x - padding_x,
            y + box[1] - padding_y,
            x + width + padding_x,
            y + box[3] + padding_y,
        ),
        radius=max(2, round(size * 0.35)),
        fill=(0, 5, 8, 185),
        outline=(55, 125, 140, 210),
        width=max(1, round(size / 16)),
    )
    layer_draw.text((x, y), MENU_KEY_HELP, font=font, fill=MENU_KEY_HELP_COLOR)
    background.alpha_composite(layer)


def _clear_text_region(image, box: tuple[int, int, int, int]) -> None:
    """Remove old glyph pixels without flattening the panel's blue gradient."""

    x0, y0, x1, y1 = box
    pixels = image.load()
    for y in range(y0, y1):
        candidates = []
        for x in range(x0, x1):
            red, green, blue = pixels[x, y][:3]
            if blue >= 90 and blue > red * 1.6 and blue > green * 1.6:
                candidates.append((red, green, blue))
        fill = Counter(candidates).most_common(1)[0][0] if candidates else (0, 0, 165)
        for x in range(x0, x1):
            red, green, _ = pixels[x, y][:3]
            # Every stock panel background pixel is blue-only.  White or
            # magenta text introduces red/green, including its antialiasing.
            if red > 2 or green > 2:
                pixels[x, y] = fill


def _draw_text_at(draw, ImageFont, font_path: Path, text: str, xy, size: int, color) -> None:
    font = _menu_font(ImageFont, font_path, size, weight=700)
    draw.multiline_text(xy, text, font=font, fill=color, spacing=max(0, size // 7))


def build_localized_key_help(
    resolver: ContentResolver,
    shadow_trees_root: Path,
    font_path: Path,
) -> dict[str, dict[str, object]]:
    """Localize the native starmap key-help panel in all three HD modes."""

    Image, ImageDraw, ImageFont = _load_pillow()
    report: dict[str, dict[str, object]] = {}
    for variant in KEY_HELP_VARIANTS:
        try:
            image = Image.open(io.BytesIO(resolver.read_bytes(variant.source_path))).convert("RGB")
        except OSError as exc:
            raise LocError(f"Cannot load key-help image {variant.source_path}: {exc}") from exc

        if variant.addon == "zh_TW":
            if image.size != (62, 42):
                raise LocError(f"Unexpected 1x key-help size: {image.size}")
            _clear_text_region(image, (14, 1, 61, 41))
            draw = ImageDraw.Draw(image)
            for text, y in zip(("舊圖", "放大", "縮小", "搜尋"), (1, 11, 21, 31)):
                _draw_text_at(draw, ImageFont, font_path, text, (17, y), 8, (222, 0, 222))
        elif variant.addon == "hires2x-zh_TW":
            if image.size != (124, 80):
                raise LocError(f"Unexpected 2x key-help size: {image.size}")
            for box in ((31, 1, 123, 27), (54, 27, 123, 54), (31, 54, 123, 79)):
                _clear_text_region(image, box)
            draw = ImageDraw.Draw(image)
            _draw_text_at(draw, ImageFont, font_path, "舊星圖", (35, 4), 14, (255, 255, 255))
            _draw_text_at(draw, ImageFont, font_path, "縮放", (58, 30), 14, (255, 255, 255))
            _draw_text_at(draw, ImageFont, font_path, "搜尋", (35, 56), 14, (255, 255, 255))
        else:
            if image.size != (186, 307):
                raise LocError(f"Unexpected 4x key-help size: {image.size}")
            for box in (
                (45, 4, 150, 36),
                (47, 40, 185, 92),
                (47, 112, 185, 151),
                (47, 178, 185, 218),
                (47, 240, 185, 279),
            ):
                _clear_text_region(image, box)
            draw = ImageDraw.Draw(image)
            title = "按鍵說明"
            title_font = _menu_font(ImageFont, font_path, 22, weight=700)
            title_box = draw.textbbox((0, 0), title, font=title_font)
            title_x = round((image.width - (title_box[2] - title_box[0])) / 2)
            draw.text((title_x, 5), title, font=title_font, fill=(181, 90, 255))
            _draw_text_at(draw, ImageFont, font_path, "舊式星圖／\n顯示星座", (54, 45), 14, (181, 90, 255))
            _draw_text_at(draw, ImageFont, font_path, "放大", (60, 119), 17, (181, 90, 255))
            _draw_text_at(draw, ImageFont, font_path, "縮小", (60, 186), 17, (181, 90, 255))
            _draw_text_at(draw, ImageFont, font_path, "搜尋星體", (54, 248), 16, (181, 90, 255))

        destination = shadow_trees_root / variant.addon
        destination = destination.joinpath(*PurePosixPath(variant.output_path).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # These panels are opaque pixel artwork.  An indexed palette preserves
        # the gradients and antialiased Han glyphs while avoiding several KB
        # of redundant RGB data in every mounted shadow archive.
        encoded = image.quantize(
            colors=128,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.NONE,
        )
        encoded.save(destination, format="PNG", optimize=True)
        encoded.close()
        report[variant.addon] = {
            "resource": variant.output_path,
            "canvas": list(image.size),
            "labels": ["舊式星圖／顯示星座", "放大", "縮小", "搜尋星體"],
        }
        image.close()
    return report


def _status_text_mask(Image, ImageDraw, ImageFont, font_path: Path, text: str, size):
    width, height = size
    mask = Image.new("L", size, 0)
    compact_glyphs = {
        "人": ("00100", "00100", "01010", "01010", "10001"),
        "力": ("01110", "00010", "01110", "01010", "10010"),
    }
    if height == 5 and text in compact_glyphs:
        x0 = (width - 5) // 2
        for y, row in enumerate(compact_glyphs[text]):
            for x, value in enumerate(row):
                if value == "1":
                    mask.putpixel((x0 + x, y), 255)
        return mask
    draw = ImageDraw.Draw(mask)
    font_size = max(7, round(height * 1.6))
    while True:
        # Medium keeps the counters in tiny Han glyphs open; Bold/700 turns
        # the 8- and 10-pixel tiers into nearly solid blocks.
        font = _menu_font(ImageFont, font_path, font_size, weight=500)
        box = draw.textbbox((0, 0), text, font=font)
        text_width = box[2] - box[0]
        text_height = box[3] - box[1]
        if (text_width <= width and text_height <= height) or font_size <= 5:
            break
        font_size -= 1
    x = round((width - text_width) / 2 - box[0])
    y = round((height - text_height) / 2 - box[1])
    draw.text((x, y), text, font=font, fill=255)
    return mask


def _row_colors(source, *, energy: bool) -> list[tuple[int, int, int]]:
    rgba = source.convert("RGBA")
    colors: list[tuple[int, int, int] | None] = []
    channel = 0 if energy else 1
    for y in range(rgba.height):
        opaque = [
            pixel[:3]
            for pixel in (rgba.getpixel((x, y)) for x in range(rgba.width))
            if pixel[3] and pixel[channel] > max(pixel[1 - channel], pixel[2])
        ]
        colors.append(max(opaque, key=lambda pixel: pixel[channel]) if opaque else None)
    fallback = (124, 0, 0) if energy else (6, 69, 6)
    populated = [color for color in colors if color is not None]
    if populated:
        fallback = populated[0]
    resolved = [color if color is not None else fallback for color in colors]
    brightened = [
        tuple(
            min(255, round(component * (2.0 if index == channel else 1.5)))
            for index, component in enumerate(color)
        )
        for color in resolved
    ]
    peak = max(color[channel] for color in brightened)
    floor = round(peak * 0.45)
    normalized = []
    for color in brightened:
        if color[channel] >= floor or color[channel] == 0:
            normalized.append(color)
            continue
        scale = floor / color[channel]
        normalized.append(tuple(min(255, round(component * scale)) for component in color))
    return normalized


def _render_status_label(
    Image,
    ImageDraw,
    ImageFont,
    source,
    font_path: Path,
    text: str,
    *,
    energy: bool,
    output_size: tuple[int, int] | None = None,
):
    if output_size is None:
        output_size = source.size
    mask = _status_text_mask(Image, ImageDraw, ImageFont, font_path, text, output_size)
    colors = _row_colors(source, energy=energy)
    # The stock labels use a five- or nine-pixel vertical gradient.  Stretching
    # that gradient made the larger Han glyphs look soft, so use its brightest
    # row as a solid high-contrast foreground at every output resolution.
    channel = 0 if energy else 1
    brightest = max(colors, key=lambda color: color[channel])
    colors = [brightest] * output_size[1]

    if source.mode == "P":
        output = Image.new("P", output_size, 0)
        palette = [0] * 768
        source_palette = source.getpalette()
        palette[:3] = source_palette[:3]
        row_indices = []
        for y, color in enumerate(colors):
            index = y + 1
            palette[index * 3 : index * 3 + 3] = list(color)
            row_indices.append(index)
        output.putpalette(palette)
        for y in range(output_size[1]):
            for x in range(output_size[0]):
                if mask.getpixel((x, y)) >= 96:
                    output.putpixel((x, y), row_indices[y])
        output.info["transparency"] = 0
        return output

    output = Image.new("RGBA", output_size, (0, 0, 0, 0))
    for y, color in enumerate(colors):
        for x in range(source.width):
            alpha = mask.getpixel((x, y))
            if alpha:
                output.putpixel((x, y), (*color, alpha))
    return output


def build_localized_status_labels(
    resolver: ContentResolver,
    shadow_trees_root: Path,
    font_path: Path,
) -> dict[str, dict[str, object]]:
    """Replace the PC-mode combat labels CREW/BATT with 船員/能量."""

    Image, ImageDraw, ImageFont = _load_pillow()
    report: dict[str, dict[str, object]] = {}
    for variant in STATUS_LABEL_VARIANTS:
        files: list[str] = []
        for frame, label, energy in ((4, "船員", False), (5, "能量", True)):
            source_path = f"{variant.source_prefix}/status-{frame:03d}.png"
            source = Image.open(io.BytesIO(resolver.read_bytes(source_path)))
            expected_size = variant.energy_size if energy else variant.crew_size
            output_size = (
                variant.energy_output_size if energy else variant.crew_output_size
            )
            if source.size != expected_size:
                source.close()
                raise LocError(
                    f"Unexpected {variant.addon} status label size for {source_path}: {source.size}"
                )
            rendered = _render_status_label(
                Image,
                ImageDraw,
                ImageFont,
                source,
                font_path,
                label,
                energy=energy,
                output_size=output_size,
            )
            output_path = f"{variant.output_prefix}/status-{frame:03d}.png"
            destination = shadow_trees_root / variant.addon
            destination = destination.joinpath(*PurePosixPath(output_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            save_args = {"format": "PNG", "optimize": True}
            if rendered.mode == "P":
                save_args["transparency"] = 0
            rendered.save(destination, **save_args)
            rendered.close()
            source.close()
            files.append(output_path)
        report[variant.addon] = {
            "labels": {"CREW": "船員", "BATT": "能量"},
            "compact_labels": None,
            "source_canvases": {
                "CREW": list(variant.crew_size),
                "BATT": list(variant.energy_size),
            },
            "canvases": {
                "CREW": list(variant.crew_output_size),
                "BATT": list(variant.energy_output_size),
            },
            "files": files,
        }
    return report


def build_localized_main_menus(
    resolver: ContentResolver,
    shadow_trees_root: Path,
    clean_background: Path,
    font_path: Path,
) -> dict[str, dict[str, object]]:
    Image, ImageDraw, ImageFont = _load_pillow()
    clean_background = clean_background.resolve()
    if not clean_background.is_file():
        raise LocError(f"Clean main-menu background not found: {clean_background}")
    try:
        source = Image.open(clean_background).convert("RGB")
    except OSError as exc:
        raise LocError(f"Cannot load clean main-menu background {clean_background}: {exc}") from exc
    if source.width * 3 != source.height * 4:
        source.close()
        raise LocError(
            f"Clean main-menu background must be exactly 4:3, found {source.width}x{source.height}"
        )

    report: dict[str, dict[str, object]] = {}
    try:
        for variant in MENU_VARIANTS:
            ani_raw, frames = _parse_frames(resolver, variant.stem, Image)
            background_frame = frames[0]
            output_dir = shadow_trees_root / variant.addon / "base" / "ui"
            output_dir.mkdir(parents=True, exist_ok=True)
            background = source.resize(
                (background_frame.width, background_frame.height),
                resample=Image.Resampling.LANCZOS,
            ).convert("RGBA")
            _draw_menu_key_help(background, Image, ImageDraw, ImageFont, font_path)
            for label, frame in zip(MENU_LABELS, frames[1:]):
                overlay = Image.new("RGBA", (frame.width, frame.height), (255, 255, 255, 0))
                _draw_tracked_centered(
                    overlay,
                    ImageDraw,
                    ImageFont,
                    font_path,
                    label,
                    fill=(255, 255, 255, 255),
                )
                coverage = overlay.getchannel("A")
                overlay = _effect_map_from_mask(
                    Image, coverage, MENU_SELECTED_COLOR
                )
                colored = Image.new("RGBA", overlay.size, MENU_NORMAL_COLOR)
                colored.putalpha(coverage)
                background.alpha_composite(colored, (frame.x, frame.y))
                overlay.save(output_dir / frame.filename, format="PNG", optimize=True)
            background.convert("RGB").save(
                output_dir / background_frame.filename, format="PNG", optimize=True
            )
            (output_dir / f"{variant.stem}.ani").write_bytes(ani_raw)
            report[variant.addon] = {
                "resource": f"base/ui/{variant.stem}.ani",
                "labels": list(MENU_LABELS),
                "font_weight": MENU_FONT_WEIGHT,
                "normal_color": list(MENU_NORMAL_COLOR),
                "selected_color": list(MENU_SELECTED_COLOR),
                "canvas": [background_frame.width, background_frame.height],
                "files": 7,
            }
    finally:
        source.close()
    return report
