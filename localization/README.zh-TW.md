# UQM-HD Traditional Chinese localization

This workspace contains the v0.3.2 Traditional Chinese (`zh-TW`) localization of
The Ur-Quan Masters HD Beta 1, finalized on 2026-07-29.

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
| `zh_TW.uqm` | 22,455,949 | `1a1b2bd13d6c8e1a8475c16a15c706602d62b7cab1a20fe395c9b931aa707942` |
| `hires2x-zh_TW.uqm` | 42,596,373 | `edef271c9034827bfab29e37c1d37b568ecc779285adc6b5d7730abd5cb1f098` |
| `hires4x-zh_TW.uqm` | 64,579,231 | `03f8491bdf5e84251a305dd73d52e353ac66efee717a9b336f3d152dc38c5749` |

All three archives passed ZIP integrity and exact resource-mapping audits. The
merged workspace passed UTF-8, engine-line-length, wrapping, CJK glyph, record
identity, protected-token, and placeholder checks.

Each mounted shadow archive contains 5,357 normal entries and no padding entry.
Every override was compared byte-for-byte with its generated shadow tree after
the nested-archive refresh. The eight
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
- Generic 2x UI cells are now 14x14 (`starcon`), 14x14 (`tiny`), and 12x15
  (`micro`). Their 4x equivalents are 20x19, 20x20, and 24x30. The Tiny and
  StarCon bounds deliberately match the SIS HUD's fixed text bands and font
  gradient effects, preventing Chinese rows from being clipped while retaining
  Bold/700 strokes.
- The five baked main-menu choices are localized as `新遊戲`, `載入遊戲`,
  `超級對戰`, `設定`, and `離開`. Unselected choices are steady light gray;
  the selected choice now remains yellow through a positive-only additive
  pulse, so it never crosses through the unselected gray or the stock red.
  These labels use Medium/500 without a synthetic outline; the heavier
  Bold/700 setting remains limited to the smaller in-game bitmap fonts.
- The preferred v0.3 Windows runtime is built from the checked-in source. Its
  `restart.c` menu pulse is `3..6/16`; physical `Escape` ends only an active
  local Super Melee bout, while campaign combat and `CHECK_ABORT` semantics are
  unchanged. `Escape` also follows the red-X confirmation path in the
  pre-battle vessel picker. Player 1 keeps Right Shift and keypad `0` for the
  special ability and gains Right Alt as a third binding.
- The main menu, Super Melee team setup, fleet slots, vessel grid, right-side
  controls, and pre-battle vessel picker accept mouse input. Moving the mouse
  reveals the cursor; a keyboard or mouse-button press hides it. Hovering a
  vessel shows its crew, battery, point cost, top speed, acceleration, turning,
  energy regeneration, and weapon/special costs.
- The Super Melee build picker's rendered `選擇船艦` and `船艦資料` action labels
  are directly clickable: the first confirms the current vessel and the second
  opens its full-screen information page. Pressing Enter or Escape, or left-clicking
  anywhere inside the visible page viewport, returns to the picker.
- If a custom runtime is unavailable, the compatibility installer can instead
  apply exactly four hash-, offset-, signature-, and PE-checksum-gated patches
  to the supported upstream PE32 executable: menu highlight, in-bout Escape,
  Player 1 RightAlt, and pre-battle picker Escape. Unknown binaries are refused.
- A permanent main-menu hint documents `↑`/`↓` navigation and `Enter` to
  confirm. The native starmap key-help panels are localized separately at 1x,
  2x, and 4x; the 4x panel documents the old-map/constellation, zoom, and
  star-search bindings in full Traditional Chinese.
- The PC-style combat HUD bitmaps now show the full `船員` and `能量` labels at
  every resolution. Their canvases are enlarged from 5/5/9 pixels high to
  8/10/18 pixels at 1x/2x/4x respectively, without changing the stock frame
  hotspots or crossing the HUD clip boundaries. Status-label weights are
  450/400/350 at 1x/2x/4x respectively, so the tiny Han counters remain open;
  the RGB/alpha encoding restores the stock gray panel during normal rendering
  while retaining a glyph-only mask for the low-energy recoloring effect.
- The Super Melee build picker localizes `PICK SHIP` and `SHIP INFO` as
  `選擇船艦` and `船艦資料`. All 25 ship-information presentations are rebuilt
  at native 320x240, 640x480, and 1280x960 with Traditional-Chinese names,
  movement statistics, weapons, special abilities, and tactics. English-style
  abbreviated ship-table fields reuse the full Han name so they cannot end in
  a misleading full stop.
- On those ship-information pages, the replacement `船員` and `能量` captions
  blend into the stock gray panel. Their redraw boxes preserve the gauges,
  vertical dividers, and lower separators at every resolution.
- The top-level README presents the 25 Super Melee vessels and campaign-only
  Precursor Flagship in one uncollapsed 26-vessel table, with an image, full
  labeled statistics, weapons, special abilities, and strategy for every entry.
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

The installed marker, all 11,534 managed file hashes, three pack archives, five
shortcuts, and a hidden 12-second runtime smoke test passed the final 17-check
verifier. The 59-test automated suite also passed. The smoke log confirmed
`hires4x-zh_TW` and a 1920x1080 fullscreen surface with no fatal diagnostic.
Visible 4x runtime passes additionally confirmed the always-yellow selection,
the `新遊戲` transition into the opening sequence instead of a stalled black
screen, localized opening credits, and the `船員`/`能量` Super Melee combat HUD.
Live input QA also confirmed that Right Alt activates Player 1's special ability
and that the picker Escape confirmation returns to team setup. The 1x mode
remains a compatibility option; dense Han characters cannot be fully legible
inside its original 8x9-pixel cells.

## Source-built Windows runtime

The v0.3.2 release bundles the updated GPL source-built Windows x86 runtime and
includes its exact dependency licenses. It does **not** include the upstream game's original
content; users must provide an extracted official Beta 1 tree. Runtime
provenance is reproducible from the clean 1,043-file `game/` tree at source
commit `7981479c611b60af041d05ec01a40791eb993f51`.

| Runtime artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `uqm-hd.exe` | 3,022,388 | `6f33a1b73a38ce5e4a7045a67a5f520eaaa15a8c16eaa8f169d0cff5ecc2364f` |
| `runtime-manifest.json` | 27,388 | `478bfc840a080977ca65fa366502b04d57d4e473405a93504e7c4c0a5bd58f5c` |

The manifest closes over 20 PE32 payloads, stages 27 license files, and records
zero unresolved non-system imports. See `../docs/BUILD-WINDOWS.md` for the
pinned MSYS2 recipe and provenance checks.

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
