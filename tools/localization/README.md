# UQM HD Traditional-Chinese localization pipeline

This directory contains a content-only localization pipeline for **The Ur-Quan
Masters HD Beta 1**. It does not call a translation API and does not modify the
game installation. It exports protected JSON, merges translated `{id,text}`
records, handles the engine's unusual text formats, generates bitmap glyphs from
Noto Sans TC, and builds three installable `.uqm` add-ons.

## Requirements

- Python 3.10 or newer.
- The extracted Beta 1 `content` directory, including `base`, `uqm.rmp`, and the
  stock `content/addons/hires2x.zip`, `hires4x.zip`, and `3dovoice.zip` packages.
- `NotoSansTC-VF.ttf`. This host provides it at
  `C:\Windows\Fonts\NotoSansTC-VF.ttf`.
- Pillow for TTF rasterization:

```powershell
python -m pip install -r .\tools\localization\requirements.txt
```

Before redistributing generated fonts, preserve and review the SIL Open Font
License for Noto Sans TC. Do not substitute a Microsoft system font for a
redistributable package unless its license explicitly permits that use.

## Complete workflow

The examples assume the extracted game is in this repository's `staging`
directory. Output paths must be new or empty so a typo cannot overwrite an
existing translation.

### 1. Export protected entry JSON

```powershell
python .\tools\localization\uqm_localize.py export `
  --content-root .\staging\UQM-HD\content `
  --output .\translation-workspace
```

This exports all 104 `STRTAB`/`CONVERSATION` resources referenced by `uqm.rmp`
and recursively discovers the three scripts called by the ending wrapper. On
the verified Beta 1 content this is 107 documents and 6,806 engine entries.

Each `resources/**/*.json` entry contains immutable label/audio/template fields
and an editable `translation` field. Only edit `translation`. The manifest's
contract hashes deliberately reject changed labels, audio tokens, entry order,
script commands, timing, paths, or source templates.

### 2. Make a flat translation-service bundle

```powershell
python .\tools\localization\uqm_localize.py bundle `
  --workspace .\translation-workspace `
  --output .\zh-TW-source.jsonl `
  --jsonl
```

The verified source yields 5,177 translatable `{id,text}` records. Immutable
slideshow commands and other control records are omitted. Send only `text` for
translation and preserve each `id` exactly.

Merge a complete returned array (`.json`) or JSONL response:

```powershell
python .\tools\localization\uqm_localize.py merge `
  --workspace .\translation-workspace `
  --response .\zh-TW-response.jsonl `
  --output .\translation-workspace-zh-TW
```

By default every exported ID must be returned exactly once. Use
`--allow-partial` only for an intentional batch, and then merge into the same
working copy with `--in-place` for subsequent batches.

### 3. Add safe Chinese break opportunities

UQM HD's dialogue wrapper recognizes only ASCII spaces and hard newlines. A
normal unspaced Chinese sentence can therefore make the engine's wrapping loop
stop making progress. This command adds conservative ASCII break spaces to CJK
tokens and hard-wraps physical UTF-8 lines below the parser limit:

```powershell
python .\tools\localization\uqm_localize.py wrap `
  --workspace .\translation-workspace-zh-TW `
  --in-place `
  --max-cjk-token 12 `
  --max-line-bytes 900
```

Dialogue is wrapped by default. `--all-text` also modifies non-dialogue payloads
and should only be used after visual review. Human translators can get better
typography by inserting semantic ASCII break spaces themselves; the validator
only requires that no CJK engine word exceed the selected limit.

### 4. Validate and optionally materialize text files

```powershell
python .\tools\localization\uqm_localize.py validate `
  --workspace .\translation-workspace-zh-TW

python .\tools\localization\uqm_localize.py import `
  --workspace .\translation-workspace-zh-TW `
  --output .\translated-text-preview
```

Validation checks, among other things:

- UTF-8 without a BOM, no NUL/CR, and no code point above `U+FFFF`;
- at most 2,048 entries and at most 1,023 encoded bytes per physical line;
- exact entry order, labels, original header whitespace, and audio clip tokens;
- balanced/preserved `$` font-switch marker counts used by Orz dialogue;
- setup-menu list cardinality and credits column limits;
- lossless reparse of every rendered text file;
- immutable slideshow commands, timing, animation paths, and font paths.

The intro and ending/final files are command scripts disguised as string tables.
Only the visible payload following `TFI` is exported for translation. `DIMS`,
`FONT*`, `ANI*`, `CALL`, `SYNC`, `WAIT`, and every other command remain protected.
Called ending scripts are installed through `shadow-content`, so their literal
`CALL base/...` paths do not need to be rewritten.

### 5. Build all three packages

```powershell
python .\tools\localization\uqm_localize.py build `
  --content-root .\staging\UQM-HD\content `
  --workspace .\translation-workspace-zh-TW `
  --output .\localized-build `
  --font C:\Windows\Fonts\NotoSansTC-VF.ttf `
  --menu-background .\localization\menu-assets\source\newgame4x-clean-imagegen.png
```

The result is:

```text
localized-build/packages/zh_TW.uqm
localized-build/packages/hires2x-zh_TW.uqm
localized-build/packages/hires4x-zh_TW.uqm
```

The resource maps are generated from the installed official maps, not copied
from the incomplete Japanese pack:

- `zh_TW`: 27 conversations + 77 string tables + 39 fonts = 143 mappings;
- `hires2x-zh_TW`: 613 stock HD graphics + 104 text + 39 fonts = 756;
- `hires4x-zh_TW`: 614 stock HD graphics + 104 text + 39 fonts = 757.

Original Latin/punctuation glyphs are copied into every mapped and directly
loaded cutscene font directory. A shadow-mounted `.fon` directory replaces the
stock resource instead of merging with it, so omitting the original glyphs can
leave presentations on a blank frame.
Only the Traditional-Chinese subsets needed by each font role are rasterized.
The generator explicitly selects Noto Sans TC Bold/700; the variable font's
default is Thin/100 and is not legible in the game's small bitmap cells. Generic
HD UI fonts receive larger, engine-safe Han canvases, while other fonts continue
to use the source font's observed capital-letter metrics. It emits lowercase,
five-digit Unicode filenames such as `04e00.png`. Directly loaded cutscene fonts
are augmented using `shadow-content`, which keeps their script paths immutable.

The five main-menu choices are baked into animation PNGs rather than string
tables. The build therefore creates localized `newgame`, `newgame2x`, and
`newgame4x` frame sets inside a nested archive placed in each add-on's
`shadow-content` directory (UQM mounts nested `.uqm`/`.zip` archives there, not
loose files). A clean 4:3 menu background supplies the artwork; the exact labels
`新遊戲`, `載入遊戲`, `超級對戰`, `設定`, and `離開` are rendered deterministically
with Noto Sans TC Medium/500 and no synthetic outline. In-game bitmap fonts stay
at Bold/700 for legibility at small cell sizes.

Packages use only ZIP Deflate, disable ZIP64, reject 65,535 or more files, and
are written deterministically. All three packages must be installed because
their fallback mappings intentionally cross-reference the 1x/2x/4x fonts.

## Install and launch

Copy all three `.uqm` files to the game's `content\addons` directory. Activate
exactly one combined add-on:

```powershell
# 320x240 content
uqm.exe -x -r 320x240 -w --resfactor=0 --addon zh_TW

# 640x480 content
uqm.exe -x -r 640x480 -w --resfactor=1 --addon hires2x-zh_TW

# 1280x960 content
uqm.exe -x -r 1280x960 -w --resfactor=2 --addon hires4x-zh_TW

# Recommended legible fullscreen profile for a 1920x1080 display
uqm.exe -o -r 1920x1080 -f -k -c none --resfactor=2 --addon hires4x-zh_TW
```

## Scope and visual QA

This pipeline localizes engine text, bitmap glyph coverage, and the five baked
main-menu choices. The Beta 1 executable still contains a few hardcoded strings
such as `SCRAP` and `QuasiSpace`; translating those would require a rebuilt
executable. A polished release still benefits from a full playthrough. In
particular, visually check the intro/final subtitles, credits, setup menu, every
alien conversation font, the 21 lander reports copied into each high-resolution
tree, save/load screens, and name entry.

## Tests

```powershell
python -m unittest discover `
  -s .\tools\localization\tests `
  -v
```
