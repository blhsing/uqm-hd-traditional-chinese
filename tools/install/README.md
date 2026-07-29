# UQM-HD Traditional Chinese Windows install layer

These scripts install the extracted UQM-HD Beta 1 tree as a managed portable copy and verify the result. They support Windows PowerShell 5.1 and PowerShell 7.

## Inputs

The installer always requires:

- `SourceRoot`: extracted upstream Windows tree containing `content/addons` (normally `staging/UQM-HD`)
- `PacksDir`: build-output directory containing exactly `zh_TW.uqm`, `hires2x-zh_TW.uqm`, and `hires4x-zh_TW.uqm`
- `InstallRoot`: portable destination (default `C:\Games\UQM-HD-TW`)
- `ProfileDir`: isolated user configuration/save directory (default `%APPDATA%\UQM-HD-zh_TW`)

The preferred release path also supplies `RuntimeDir`, whose
`runtime-manifest.json` locks the custom Windows x86 executable and every DLL by
exact length and SHA-256. The manifest maps its source executable (normally
`uqm-hd.exe`) to the installed name `uqm.exe`; DLLs retain their leaf names. It
must also contain a non-empty `LICENSES` directory. This path does not require
Python and never applies legacy binary patches.

The v0.3 release runtime was built from the clean 1,043-file `game/` tree at
source commit `1aee01896e88f759271779efcc03f58508c52f7f`. Its manifest records
20 PE32 payloads, 27 license files, and zero unresolved non-system imports:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `uqm-hd.exe` | 3,020,273 | `2ef0f8ca00baad2f9c5611f8885a34acb54f16bc5c7fecb29ee7d6632d3be018` |
| `runtime-manifest.json` | 51,276 | `3facebf59aafb4a373cf55bfc59953b9d4d4fcfe4c6feac96674e316123c9220` |

The release archive includes this GPL source-built runtime and its dependency
licenses, but not the upstream game's original content. `SourceRoot` must
therefore still point at an extracted official Beta 1 tree containing
`content/addons`.

The manifest schema is intentionally small and deterministic:

```json
{
  "schemaVersion": 1,
  "platform": "windows-x86",
  "executable": "uqm-hd.exe",
  "files": [
    {
      "path": "uqm-hd.exe",
      "installPath": "uqm.exe",
      "length": 3020273,
      "sha256": "64 lowercase or uppercase hexadecimal digits",
      "kind": "executable",
      "package": "uqm-hd",
      "version": "0.7.0 + HD Mod BETA (revision 1347M)",
      "license": "GPL-2.0-or-later",
      "licenseFiles": ["LICENSES/uqm-hd/COPYING"],
      "provenance": {"source": "repository/build identification"}
    },
    {
      "path": "SDL.dll",
      "installPath": "SDL.dll",
      "length": 451295,
      "sha256": "64 lowercase or uppercase hexadecimal digits",
      "kind": "runtime-library",
      "package": "mingw-w64-i686-SDL",
      "version": "1.2.15+r419+gef3a6c05-1",
      "license": "LGPL-2.1-or-later",
      "licenseFiles": ["LICENSES/mingw-w64-i686-SDL/COPYING"],
      "provenance": {"source": "MSYS2 package identification"}
    }
  ]
}
```

All payload names must be ASCII leaf filenames. There must be exactly one
`executable` entry and at least one `runtime-library`; every top-level EXE/DLL
must be listed, and no unlisted binary is accepted. Every entry must name its
package, version, license expression, one or more existing files below
`LICENSES/`, and a non-empty provenance object.

If `RuntimeDir` is omitted, `SourceRoot` must also contain the exact supported
upstream `uqm.exe`, and Python 3.10 or newer must be available on `PATH`. That
fallback copies the upstream executable and applies the audited, hash-gated PE
patch pipeline only to the destination copy.

Run a validation-only rehearsal first. `-PlanOnly` reads and validates the source and all three pack archives, but does not create the destination, profile, marker, or shortcuts:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install\Install-UqmHdZhTw.ps1 `
  -SourceRoot .\staging\UQM-HD `
  -PacksDir .\localized-build\packages `
  -RuntimeDir .\runtime\windows-x86 `
  -InstallRoot C:\Games\UQM-HD-TW `
  -ProfileDir "$env:APPDATA\UQM-HD-zh_TW" `
  -PlanOnly
```

Remove `-PlanOnly` to install:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install\Install-UqmHdZhTw.ps1 `
  -SourceRoot .\staging\UQM-HD `
  -PacksDir .\localized-build\packages `
  -RuntimeDir .\runtime\windows-x86 `
  -InstallRoot C:\Games\UQM-HD-TW `
  -ProfileDir "$env:APPDATA\UQM-HD-zh_TW"
```

The default Desktop and Start Menu shortcut is named `The Ur-Quan Masters HD - Traditional Chinese.lnk` and launches:

```text
uqm.exe -o -r 1920x1080 -f -k -c none --resfactor=2 -C "%APPDATA%\UQM-HD-zh_TW" --addon hires4x-zh_TW
```

This is the legible 4x profile for this host. The engine's logical canvas remains
4:3 (1280x960); OpenGL scales it to 1440x1080 and centers it on the 1920x1080
display with pillarboxes. Nearest-neighbor scaling (`-c none`) keeps the Chinese
bitmap glyphs crisp.

Three local shortcuts in the install root provide native-size windowed variants:
1x at 320x240 (`zh_TW`), 2x at 640x480 (`hires2x-zh_TW`), and 4x at 1280x960
(`hires4x-zh_TW`). The 1x mode is retained for compatibility; its 8-9-pixel
font cells cannot represent dense Traditional Chinese as clearly as the 4x mode.

During an active Super Melee bout, `Escape` ends that bout by clearing only the
`IN_BATTLE` state and returns to the Super Melee setup screen. This behavior is
deliberately scoped to Super Melee; the campaign's existing escape/run-away
rules are unchanged, and the global `CHECK_ABORT` state is not propagated.
In the pre-battle vessel picker, physical `Escape` follows the same confirmation
path as the red X. Player 1's special ability keeps its Right Shift and keypad
`0` bindings and gains RightAlt as a hidden third binding in the isolated
profile.

With `RuntimeDir`, every runtime payload file is re-hashed both during preflight
and immediately before its atomic copy, and the managed-install marker records
the custom runtime manifest hash and the final hash of every installed file.

Without `RuntimeDir`, the managed executable receives exactly four
deterministic, hash-gated compatibility patches: menu highlight, in-bout Escape,
Player 1 RightAlt, and pre-battle picker Escape. This fallback does not provide
the source runtime's complete mouse-selection and vessel-stat-card features.
The upstream `SourceRoot` is never modified. `-PlanOnly` verifies the full chain
against a temporary copy; a real install patches only the destination copy
before its final manifest hash is recorded. Every patcher rejects unknown
executable hashes and supports `--check`.

Shortcut file and folder names intentionally use ASCII for compatibility with
Windows hosts whose legacy shortcut API cannot save Unicode paths. The game UI,
dialogue, menus, and localized add-on data remain Traditional Chinese.

## Verification

The default verification is intentionally thorough: it checks every managed
file's length and SHA-256 against the install manifest, validates all three
ZIP-compatible UQM archives, compares packs with the build output when it is
available, independently checks all shortcut targets/arguments/working
directories, and runs a hidden 12-second 4x fullscreen smoke test. The smoke
log must confirm the `hires4x-zh_TW` add-on and a 1920x1080 rendering surface.
The finalized v0.3 installation contains 11,534 managed files and passes all 17
verifier checks; the repository's automated suite passes all 48 tests.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install\Test-UqmHdZhTwInstall.ps1 `
  -InstallRoot C:\Games\UQM-HD-TW `
  -ProfileDir "$env:APPDATA\UQM-HD-zh_TW" `
  -PacksDir .\localized-build\packages `
  -SmokeTimeoutSeconds 12
```

The smoke test terminates only the process it starts and retains its log at `%APPDATA%\UQM-HD-zh_TW\uqm-install-smoke.log`. `-SkipSmokeTest` runs static verification only. `-SkipHashes` is available for a quicker diagnostic pass but should not be used for final acceptance.

## Safety and idempotence

- The installer refuses volume roots, protected directories, wildcards, nested source/install/profile paths, reparse points, and non-empty destinations without its exact product marker.
- Every replacement is an exact literal path below a validated managed root. Files are staged and SHA-256 checked before atomic replacement.
- Existing unrelated files are never mirrored or deleted. Rerunning the installer only replaces managed files whose hash changed.
- A transactional `.installing` sidecar makes an interrupted first install
  safely resumable without replacing the last complete product marker.
- Stale files from a prior managed runtime are removed only when their current
  length and SHA-256 still match the previous marker; user-modified files are
  refused rather than silently deleted.
- Existing Desktop or Start Menu shortcuts with different settings are not overwritten unless the previous complete marker proves that this installer owns their exact paths.
- Compiler output, debug CRT/audio DLLs, source build archives/scripts, old launch batches, baseline userdata, and logs are excluded from the portable copy.
