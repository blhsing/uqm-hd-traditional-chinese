# UQM-HD Traditional Chinese Windows install layer

These scripts install the extracted UQM-HD Beta 1 tree as a managed portable copy and verify the result. They support Windows PowerShell 5.1 and PowerShell 7.

## Inputs

The installer requires:

- `SourceRoot`: extracted upstream Windows tree containing `uqm.exe` and `content/addons` (normally `staging/UQM-HD`)
- `PacksDir`: build-output directory containing exactly `zh_TW.uqm`, `hires2x-zh_TW.uqm`, and `hires4x-zh_TW.uqm`
- `InstallRoot`: portable destination (default `C:\Games\UQM-HD-TW`)
- `ProfileDir`: isolated user configuration/save directory (default `%APPDATA%\UQM-HD-zh_TW`)
- Python 3.10 or newer on `PATH`, used only by the two audited PE patchers

Run a validation-only rehearsal first. `-PlanOnly` reads and validates the source and all three pack archives, but does not create the destination, profile, marker, or shortcuts:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install\Install-UqmHdZhTw.ps1 `
  -SourceRoot .\staging\UQM-HD `
  -PacksDir .\localized-build\packages `
  -InstallRoot C:\Games\UQM-HD-TW `
  -ProfileDir "$env:APPDATA\UQM-HD-zh_TW" `
  -PlanOnly
```

Remove `-PlanOnly` to install:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install\Install-UqmHdZhTw.ps1 `
  -SourceRoot .\staging\UQM-HD `
  -PacksDir .\localized-build\packages `
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

The managed executable receives two deterministic, hash-gated patches during
installation: `patch_uqm_hd_menu_highlight.py`, followed by
`patch_uqm_hd_super_melee_escape.py`. The upstream `SourceRoot` is never
modified. `-PlanOnly` verifies the full chain against a temporary copy; a real
install patches only the destination copy before its final manifest hash is
recorded. Both patchers reject unknown executable hashes and support `--check`.

Shortcut file and folder names intentionally use ASCII for compatibility with
Windows hosts whose legacy shortcut API cannot save Unicode paths. The game UI,
dialogue, menus, and localized add-on data remain Traditional Chinese.

## Verification

The default verification is intentionally thorough: it checks every managed file's length and SHA-256 against the install manifest, validates all three ZIP-compatible UQM archives, compares packs with the build output when it is available, independently checks all shortcut targets/arguments/working directories, and runs a hidden 12-second 4x fullscreen smoke test. The smoke log must confirm the `hires4x-zh_TW` add-on and a 1920x1080 rendering surface.

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
- A provisional product marker makes an interrupted first install safely resumable.
- Existing Desktop or Start Menu shortcuts with different settings are not overwritten unless the previous complete marker proves that this installer owns their exact paths.
- Compiler output, debug CRT/audio DLLs, source build archives/scripts, old launch batches, baseline userdata, and logs are excluded from the portable copy.
