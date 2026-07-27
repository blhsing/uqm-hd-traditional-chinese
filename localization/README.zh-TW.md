# UQM-HD Traditional Chinese localization

This workspace contains a complete Traditional Chinese (`zh-TW`) localization
of The Ur-Quan Masters HD Beta 1, prepared on 2026-07-26.

## Translation provenance

- The shipped translation was authored by OpenAI Codex as an LLM translation.
- It covers all 5,177 translatable records exported from 107 resource documents
  (6,806 engine entries in total).
- The source and translated record sets are `records.en.json` and
  `records.llm-zh-TW.json`.
- A previously interrupted Google Translate experiment was quarantined in a
  local `machine-translation.backup` directory and is intentionally not
  published; none of it was merged into the shipped packs.
- Proper names and recurring lore terminology were normalized through
  `glossary.zh_TW.json`.

This is an LLM-authored localization, not a professional human translation.
The structural and automated linguistic checks pass, but a native-speaker
editor may still wish to polish tone or word choice.

## Built add-on packs

| Pack | Bytes | SHA-256 |
| --- | ---: | --- |
| `zh_TW.uqm` | 20,986,438 | `faa76bdd7f386c02e3c2ef989d8ca5ff5f434054d944173ac02fdc42b7319d31` |
| `hires2x-zh_TW.uqm` | 39,634,130 | `ca3a5954aed77ed476a7529dfd7dd28c88d57671f23a615773db4ea061ac93a7` |
| `hires4x-zh_TW.uqm` | 59,255,847 | `bf5103dc3341ee8e7fd5c8a515a95309ebb78463ed0979b064107bd89bdc896c` |

All three archives passed ZIP integrity and exact resource-mapping audits. The
merged workspace passed UTF-8, engine-line-length, wrapping, CJK glyph, record
identity, protected-token, and placeholder checks.

Each mounted shadow archive contains 5,244 functional override files plus one
inert ZIP padding entry. Every override was compared byte-for-byte with its
generated shadow tree after the exact-size nested-archive refresh. The eight
direct cutscene fonts contain both the generated Traditional-Chinese subset and
all 95–100 original glyphs from the corresponding stock font; package QA
explicitly checks space, digits, uppercase/lowercase Latin, and `一` before
installation.

## Legibility and menu artwork

- In-game Chinese bitmap glyphs are rasterized from `NotoSansTC-VF.ttf` at an
  explicit Bold/700 weight. The variable font's implicit Thin/100 default was
  the cause of the earlier faint strokes. Direct cutscene fonts retain every
  original Latin/punctuation glyph because a shadow-mounted `.fon` directory
  replaces, rather than merges with, the stock resource.
- Generic 2x UI cells are now 14x14 (`starcon`), 14x16 (`tiny`), and 12x15
  (`micro`). Their 4x equivalents are 28x28, 28x32, and 24x30.
- The five baked main-menu choices are localized as `新遊戲`, `載入遊戲`,
  `超級對戰`, `設定`, and `離開`. Unselected choices are steady light gray;
  the selected choice now remains yellow through a positive-only additive
  pulse, so it never crosses through the unselected gray or the stock red.
  These labels use Medium/500 without a synthetic outline; the heavier
  Bold/700 setting remains limited to the smaller in-game bitmap fonts.
- The source-level menu pulse is `3..6/16` in `restart.c`. Because this host
  lacks the historical SDL 1.2 build toolchain, the unsigned PE32 release is
  updated by a hash-, offset-, signature-, and PE-checksum-gated patcher. The
  second equally gated patch makes `Escape` end only an active Super Melee
  bout by clearing `IN_BATTLE`, then return to its setup screen; campaign
  combat is unchanged and `CHECK_ABORT` is not propagated. The
  installed executable SHA-256 is
  `3d2174f5dab4ce9b7a2dcd0eec7c59473f543239953b18664c51fff631f36bc9`.
- A permanent main-menu hint documents `↑`/`↓` navigation and `Enter` to
  confirm. The native starmap key-help panels are localized separately at 1x,
  2x, and 4x; the 4x panel documents the old-map/constellation, zoom, and
  star-search bindings in full Traditional Chinese.
- The PC-style combat HUD bitmaps now show the full `船員` and `能量` labels at
  every resolution. Their canvases are enlarged from 5/5/9 pixels high to
  8/10/18 pixels at 1x/2x/4x respectively, without changing the stock frame
  hotspots or crossing the HUD clip boundaries. Status labels use Medium/500
  so the tiny Han counters remain open, and all six frames retain transparent
  glyph masks so the low-energy recoloring effect remains functional.
- OpenAI's built-in image editor was used only to remove the five baked English
  labels while preserving the 4:3 space/panel composition. The edit prompt was:
  "Remove only the New Game, Load Game, Super Melee!, Setup, and Quit labels;
  preserve the scene, panel, composition, and crop, and add no replacement
  text." Exact Chinese text was then rendered deterministically by the build,
  rather than generated inside the image model.
- The clean source artwork is
  `menu-assets/source/newgame4x-clean-imagegen.png`. Visual QA renders are under
  `qa/font-legibility-contact-sheet.png` and
  `qa/installed-runtime-final-yellow-3.png`,
  `qa/installed-runtime-final-yellow-7.png`, and the
  `qa/key-help-*-preview.png` renders.

## Host installation

- Game: `C:\Games\UQM-HD-TW`
- Isolated profile and saves: `%APPDATA%\UQM-HD-zh_TW`
- Default visual mode: 4x OpenGL fullscreen (`hires4x-zh_TW`) at 1920x1080,
  nearest-neighbor scaling, with the engine's 4:3 canvas pillarboxed
- Alternate native-size windowed launchers: 1x at 320x240, 2x at 640x480, and
  4x at 1280x960 in the game directory

The installed marker, all 11,530 managed file hashes, three pack archives, five
shortcuts, and a hidden 12-second runtime smoke test passed the final 13-check
verifier. The smoke log confirmed `hires4x-zh_TW` and a 1920x1080 fullscreen
surface with no fatal diagnostic. Visible 4x runtime passes additionally
confirmed the always-yellow selection, the `新遊戲` transition into the opening
sequence instead of a stalled black screen, localized opening credits, and the
`船員`/`能量` Super Melee combat HUD. The 1x mode remains a compatibility option;
dense Han characters cannot be fully legible inside its original 8x9-pixel
cells.

Shortcut filenames use ASCII because this host's legacy Windows shortcut API
cannot reliably create Unicode paths. This does not affect the Traditional
Chinese game UI or content.

## Upstream and licenses

The base game was obtained from the official
[UQM-HD SourceForge project](https://sourceforge.net/projects/urquanmastershd/).
See upstream's [COPYING file](https://sourceforge.net/p/urquanmastershd/git-new/ci/master/tree/COPYING)
for the game code and content licenses. Bundled Noto CJK font files are covered
by the SIL Open Font License; a copy is stored in
`../LICENSES/OFL-1.1-NotoSansCJK.txt`.
