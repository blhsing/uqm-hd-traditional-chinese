from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class NativeResolutionSourceTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_engine_accepts_and_defaults_to_native_factor_three(self) -> None:
        source = self.read("game/src/uqm.c")
        self.assertIn("INIT_CONFIG_OPTION(  resolutionFactor,  3 )", source)
        self.assertIn("options->resolutionFactor.value > 3", source)
        self.assertIn('"Resolution factor has to be 0, 1, 2 or 3."', source)

    def test_native_canvas_and_opengl_texture_are_large_enough(self) -> None:
        units = self.read("game/src/uqm/units.h")
        opengl = self.read("game/src/libs/graphics/sdl/opengl.c")
        self.assertIn("RES_NATIVE_SCALE", units)
        self.assertIn("texture_width = 512 << resolutionFactor", opengl)
        self.assertIn("texture_height = 256 << resolutionFactor", opengl)
        self.assertIn("GL_MAX_TEXTURE_SIZE", opengl)

    def test_stock_truecolor_frames_are_converted_then_resampled(self) -> None:
        loader = self.read("game/src/libs/graphics/gfxload.c")
        canvas = self.read("game/src/libs/graphics/sdl/canvas.c")
        self.assertIn("resolutionFactor > 2 && !ani[cel_ct].native_resolution", loader)
        self.assertIn("TFB_DrawCanvas_Rescale_Bilinear", loader)
        self.assertIn("SDL_ConvertSurface", canvas)
        self.assertIn("Could not convert %d-bit source", canvas)

    def test_installer_exposes_only_the_native_fullscreen_profile(self) -> None:
        common = self.read("tools/install/UqmInstall.Common.ps1")
        self.assertIn("$script:UqmPackNames = @('native1080-zh_TW.uqm')", common)
        self.assertIn("[ValidateSet(3)]", common)
        self.assertIn("-c bilinear --resfactor=3", common)
        self.assertIn("--addon native1080-zh_TW", common)
        self.assertEqual(common.count("ResolutionFactor = 3"), 2)


if __name__ == "__main__":
    unittest.main()

