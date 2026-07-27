[CmdletBinding()]
param(
    [string]$SourceRoot = (Join-Path -Path $PSScriptRoot -ChildPath '..\..\staging\UQM-HD'),
    [Parameter(Mandatory = $true)][string]$PacksDir,
    [string]$InstallRoot = 'C:\Games\UQM-HD-TW',
    [string]$ProfileDir = (Join-Path -Path $env:APPDATA -ChildPath 'UQM-HD-zh_TW'),
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path -Path $PSScriptRoot -ChildPath 'UqmInstall.Common.ps1')

$script:UqmOriginalExecutableSha256 = 'c43c258aa41c4effe5d092c8541560a517cdd7be91e3c576a10a4ad306f776d3'
$script:UqmMenuPatchedExecutableSha256 = '638a9ae53678df63fcf1cd43ffe48e62446f094c67ab730c5c11a02a6ef86907'
$script:UqmLegacyEscapeExecutableSha256 = @(
    '40e99978b96f3ec3b75d9acd5ba6308be21b0f0986362b144afd97ef9f380ac0',
    '1af8f5fdcefd18b59cc14007a7ca9a98f5317bebf6f4ac46a29fa28086de5214',
    '425b175a4da3d5a93dc238e0d545ebb5f63abf0abe8441b515d5b3b30f94c419'
)
$script:UqmFinalExecutableSha256 = '3d2174f5dab4ce9b7a2dcd0eec7c59473f543239953b18664c51fff631f36bc9'

function Test-ExcludedUqmSourceFile {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $portable = $RelativePath.Replace('\', '/')
    $leaf = [IO.Path]::GetFileName($RelativePath)
    $extension = [IO.Path]::GetExtension($leaf)

    if ($portable.StartsWith('userdata-baseline/', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($portable.StartsWith('.git/', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($portable.StartsWith('.vs/', [StringComparison]::OrdinalIgnoreCase)) { return $true }

    if ($portable.IndexOf('/') -lt 0) {
        $excludedRootFiles = @(
            'build.sh', 'build2.sh', 'build.vars.in', 'build.zip',
            'Makefile.build', 'Makeinfo', 'Makeproject', 'subst', 'uqm-indent',
            'stdout.txt', 'stderr.txt',
            'uqm-exe-1280.bat', 'uqm1280 - RUS.bat', 'uqm1280.bat',
            'uqm320.bat', 'uqm640.bat',
            'msvcr100d.dll', 'msvcr110d.dll', 'ogg_d.dll',
            'vorbis_d.dll', 'vorbisenc_d.dll', 'vorbisfile_d.dll'
        )
        if ($excludedRootFiles -contains $leaf) { return $true }
        if ($leaf.StartsWith('uqmdebug', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    }

    if (@('.pdb', '.ilk', '.exp', '.lib', '.obj', '.idb', '.suo', '.user') -contains $extension.ToLowerInvariant()) {
        return $true
    }
    if ($leaf.EndsWith('_d.dll', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($leaf.EndsWith('.log', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($leaf.EndsWith('.tmp', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($leaf.EndsWith('.bak', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ([string]::Equals($leaf, $script:UqmMarkerName, [StringComparison]::OrdinalIgnoreCase)) { return $true }
    return $false
}

function Test-MarkerListsShortcut {
    param($Marker, [string]$Path)
    if ($null -eq $Marker) { return $false }
    if ($null -eq $Marker.PSObject.Properties['Shortcuts']) { return $false }
    foreach ($item in @($Marker.Shortcuts)) {
        if ($null -ne $item -and $null -ne $item.PSObject.Properties['Path'] -and
            (Test-UqmPathEqual -Left $item.Path -Right $Path)) {
            return $true
        }
    }
    return $false
}

function Copy-UqmFileAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$ExpectedHash,
        [Parameter(Mandatory = $true)][Int64]$ExpectedLength,
        [Parameter(Mandatory = $true)][string]$ManagedRoot
    )

    $destinationFull = Get-UqmFullPath -Path $Destination
    if (-not (Test-UqmPathInside -Path $destinationFull -Root $ManagedRoot)) {
        throw "Copy destination escaped the exact install root: $destinationFull"
    }
    $parent = [IO.Path]::GetDirectoryName($destinationFull)
    Assert-UqmNoReparseComponents -Path $parent
    if (-not (Test-Path -LiteralPath $parent)) {
        [void](New-Item -ItemType Directory -Path $parent)
    }
    Assert-UqmNoReparseComponents -Path $parent

    if (Test-Path -LiteralPath $destinationFull) {
        $existing = Get-Item -LiteralPath $destinationFull -Force
        if ($existing.PSIsContainer) {
            throw "A directory occupies a required file path: $destinationFull"
        }
        if (($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to replace a file reparse point: $destinationFull"
        }
        if ($existing.Length -eq $ExpectedLength) {
            $existingHash = Get-UqmSha256 -Path $destinationFull
            if ([string]::Equals($existingHash, $ExpectedHash, [StringComparison]::OrdinalIgnoreCase)) {
                return 'unchanged'
            }
        }
    }

    $temporary = Join-Path -Path $parent -ChildPath ('.uqm-copy-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::Copy($Source, $temporary, $false)
        $temporaryItem = Get-Item -LiteralPath $temporary
        if ($temporaryItem.Length -ne $ExpectedLength) {
            throw "The staged copy has the wrong length: $Destination"
        }
        $temporaryHash = Get-UqmSha256 -Path $temporary
        if (-not [string]::Equals($temporaryHash, $ExpectedHash, [StringComparison]::OrdinalIgnoreCase)) {
            throw "The staged copy failed SHA-256 verification: $Destination"
        }
        Move-UqmStagedFileIntoPlace -StagedPath $temporary -DestinationPath $destinationFull
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }

    $installed = Get-Item -LiteralPath $destinationFull
    if ($installed.Length -ne $ExpectedLength) {
        throw "The installed file has the wrong length: $destinationFull"
    }
    return 'copied'
}

function Get-UqmPythonExecutable {
    $command = Get-Command -Name 'python' -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $command) {
        throw 'Python 3.10 or newer is required to apply the hash-gated executable patches.'
    }
    $versionOutput = @(& $command.Source --version 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "The Python command could not run: $($versionOutput -join ' ')"
    }
    return $command.Source
}

function Invoke-UqmPythonPatch {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExecutable,
        [Parameter(Mandatory = $true)][string]$ScriptName,
        [Parameter(Mandatory = $true)][string]$Executable,
        [switch]$CheckOnly
    )

    $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath $ScriptName
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "Required executable patcher is missing: $scriptPath"
    }
    $arguments = @($scriptPath, $Executable)
    if ($CheckOnly) { $arguments += '--check' }
    $patchOutput = @(& $PythonExecutable @arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Executable patcher failed ($ScriptName): $($patchOutput -join ' ')"
    }
    Write-Verbose ($patchOutput -join ' ')
}

function Invoke-UqmExecutablePatchPipeline {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string]$PythonExecutable
    )

    $full = Get-UqmFullPath -Path $Executable -MustExist
    $digest = Get-UqmSha256 -Path $full

    if ([string]::Equals($digest, $script:UqmFinalExecutableSha256, [StringComparison]::OrdinalIgnoreCase)) {
        Invoke-UqmPythonPatch -PythonExecutable $PythonExecutable `
            -ScriptName 'patch_uqm_hd_super_melee_escape.py' -Executable $full -CheckOnly
        return
    }

    if ([string]::Equals($digest, $script:UqmOriginalExecutableSha256, [StringComparison]::OrdinalIgnoreCase)) {
        Invoke-UqmPythonPatch -PythonExecutable $PythonExecutable `
            -ScriptName 'patch_uqm_hd_menu_highlight.py' -Executable $full
    }
    elseif (-not [string]::Equals($digest, $script:UqmMenuPatchedExecutableSha256, [StringComparison]::OrdinalIgnoreCase) -and
        -not ($script:UqmLegacyEscapeExecutableSha256 -contains $digest)) {
        throw "Unsupported uqm.exe SHA-256: $digest"
    }

    Invoke-UqmPythonPatch -PythonExecutable $PythonExecutable `
        -ScriptName 'patch_uqm_hd_super_melee_escape.py' -Executable $full
    $finalDigest = Get-UqmSha256 -Path $full
    if (-not [string]::Equals($finalDigest, $script:UqmFinalExecutableSha256, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Executable patch pipeline produced an unexpected SHA-256: $finalDigest"
    }
}

function Assert-UqmExecutablePatchPipeline {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string]$PythonExecutable
    )

    $temporary = Join-Path -Path ([IO.Path]::GetTempPath()) `
        -ChildPath ('uqm-hd-zh-tw-' + [Guid]::NewGuid().ToString('N') + '.exe')
    try {
        [IO.File]::Copy($Executable, $temporary, $false)
        Invoke-UqmExecutablePatchPipeline -Executable $temporary -PythonExecutable $PythonExecutable
    }
    finally {
        if ([IO.File]::Exists($temporary)) {
            [IO.File]::Delete($temporary)
        }
    }
}

$source = Get-UqmFullPath -Path $SourceRoot -MustExist -MustBeDirectory
$packs = Get-UqmFullPath -Path $PacksDir -MustExist -MustBeDirectory
$install = Get-UqmFullPath -Path $InstallRoot -MustBeDirectory
$profile = Get-UqmFullPath -Path $ProfileDir -MustBeDirectory

Assert-UqmNotVolumeRoot -Path $install -Role 'InstallRoot'
Assert-UqmNotVolumeRoot -Path $profile -Role 'ProfileDir'
Assert-UqmNoReparseComponents -Path $source
Assert-UqmNoReparseComponents -Path $packs
Assert-UqmNoReparseComponents -Path $install
Assert-UqmNoReparseComponents -Path $profile

if ((Test-UqmPathInside -Path $install -Root $source -AllowRoot) -or
    (Test-UqmPathInside -Path $source -Root $install -AllowRoot)) {
    throw 'SourceRoot and InstallRoot must be separate, non-nested directories.'
}
if ((Test-UqmPathInside -Path $install -Root $packs -AllowRoot) -or
    (Test-UqmPathInside -Path $packs -Root $install -AllowRoot)) {
    throw 'PacksDir and InstallRoot must be separate, non-nested directories.'
}
if ((Test-UqmPathInside -Path $install -Root $profile -AllowRoot) -or
    (Test-UqmPathInside -Path $profile -Root $install -AllowRoot)) {
    throw 'ProfileDir and InstallRoot must be separate, non-nested directories.'
}

$requiredExe = Join-UqmContainedPath -Root $source -RelativePath 'uqm.exe'
$requiredContent = Join-UqmContainedPath -Root $source -RelativePath 'content'
$requiredAddons = Join-UqmContainedPath -Root $source -RelativePath 'content\addons'
if (-not (Test-Path -LiteralPath $requiredExe -PathType Leaf)) {
    throw "SourceRoot does not contain uqm.exe: $source"
}
if (-not (Test-Path -LiteralPath $requiredContent -PathType Container) -or
    -not (Test-Path -LiteralPath $requiredAddons -PathType Container)) {
    throw "SourceRoot does not contain the expected content/addons tree: $source"
}

$reparseSourceItem = Get-ChildItem -LiteralPath $source -Force -Recurse |
    Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 } |
    Select-Object -First 1
if ($null -ne $reparseSourceItem) {
    throw "SourceRoot contains a reparse point, which is not accepted for a portable install: $($reparseSourceItem.FullName)"
}

$pythonExecutable = Get-UqmPythonExecutable
Assert-UqmExecutablePatchPipeline -Executable $requiredExe -PythonExecutable $pythonExecutable

$packFiles = @{}
foreach ($packName in $script:UqmPackNames) {
    $packPath = Join-UqmContainedPath -Root $packs -RelativePath $packName
    if (-not (Test-Path -LiteralPath $packPath -PathType Leaf)) {
        throw "Required Traditional Chinese pack is missing: $packPath"
    }
    $packItem = Get-Item -LiteralPath $packPath
    if (-not [string]::Equals($packItem.Name, $packName, [StringComparison]::Ordinal)) {
        throw "Pack filename casing must be exact. Expected: $packName Actual: $($packItem.Name)"
    }
    $entryCount = Assert-UqmArchive -Path $packPath
    $packFiles[$packName] = [pscustomobject]@{
        Path = $packPath
        EntryCount = $entryCount
    }
}

$previousMarker = $null
if (Test-Path -LiteralPath $install) {
    if (-not (Test-Path -LiteralPath $install -PathType Container)) {
        throw "InstallRoot is not a directory: $install"
    }
    $previousMarker = Read-UqmInstallMarker -InstallRoot $install
    $firstExistingItem = Get-ChildItem -LiteralPath $install -Force | Select-Object -First 1
    if ($null -ne $firstExistingItem -and $null -eq $previousMarker) {
        throw "InstallRoot is non-empty but has no valid managed-install marker: $install"
    }
}

$copyPlan = @{}
$excludedCount = 0
$sourceFiles = Get-ChildItem -LiteralPath $source -Force -File -Recurse
foreach ($file in $sourceFiles) {
    $relative = Get-UqmRelativePath -Path $file.FullName -Root $source
    if (Test-ExcludedUqmSourceFile -RelativePath $relative) {
        $excludedCount++
        continue
    }
    $portableRelative = $relative.Replace('\', '/')
    $copyPlan[$portableRelative] = [pscustomobject]@{
        RelativePath = $portableRelative
        SourcePath = $file.FullName
        Kind = 'upstream'
    }
}

foreach ($packName in $script:UqmPackNames) {
    $relative = ('content/addons/' + $packName)
    $copyPlan[$relative] = [pscustomobject]@{
        RelativePath = $relative
        SourcePath = $packFiles[$packName].Path
        Kind = 'zh-tw-pack'
    }
}

$plannedBytes = [Int64]0
foreach ($entry in $copyPlan.Values) {
    $plannedBytes += (Get-Item -LiteralPath $entry.SourcePath).Length
}
$planSummary = [pscustomobject][ordered]@{
    SourceRoot = $source
    PacksDir = $packs
    InstallRoot = $install
    ProfileDir = $profile
    FilesToManage = $copyPlan.Count
    BytesToManage = $plannedBytes
    SourceFilesExcluded = $excludedCount
    Packs = @($script:UqmPackNames)
}

$shortcutSpecifications = Get-UqmShortcutSpecifications -InstallRoot $install -ProfileDir $profile
foreach ($specification in $shortcutSpecifications) {
    $shortcutPath = Get-UqmFullPath -Path $specification.Path
    if (-not (Test-UqmPathInside -Path $shortcutPath -Root $specification.AllowedRoot)) {
        throw "Shortcut preflight escaped its exact allowed root: $shortcutPath"
    }
    if (Test-Path -LiteralPath $shortcutPath) {
        $ownedByPreviousMarker = Test-MarkerListsShortcut -Marker $previousMarker -Path $shortcutPath
        try {
            $existingShortcut = Get-UqmShortcutDetails -Path $shortcutPath
            $existingMatches = Test-UqmShortcutMatches -Actual $existingShortcut -Expected $specification
        }
        catch {
            if (-not $ownedByPreviousMarker) {
                throw "An unmanaged shortcut exists but cannot be validated: $shortcutPath. $($_.Exception.Message)"
            }
            $existingMatches = $false
        }
        if (-not $existingMatches -and -not $ownedByPreviousMarker) {
            throw "An unmanaged shortcut already exists with different settings: $shortcutPath"
        }
    }
}

if ($PlanOnly) {
    $planSummary
    return
}

if (-not (Test-Path -LiteralPath $install)) {
    [void](New-Item -ItemType Directory -Path $install)
}
if (-not (Test-Path -LiteralPath $profile)) {
    [void](New-Item -ItemType Directory -Path $profile)
}
Assert-UqmNoReparseComponents -Path $install
Assert-UqmNoReparseComponents -Path $profile

$markerPath = Join-UqmContainedPath -Root $install -RelativePath $script:UqmMarkerName
$installedAtUtc = [DateTime]::UtcNow.ToString('o')
if ($null -ne $previousMarker -and $null -ne $previousMarker.PSObject.Properties['InstalledAtUtc']) {
    $installedAtUtc = [string]$previousMarker.InstalledAtUtc
}
$provisionalMarker = [ordered]@{
    SchemaVersion = 1
    ProductId = $script:UqmProductId
    State = 'installing'
    InstalledAtUtc = $installedAtUtc
    UpdatedAtUtc = [DateTime]::UtcNow.ToString('o')
    SourceRoot = $source
    PacksDir = $packs
    InstallRoot = $install
    ProfileDir = $profile
    Shortcuts = @()
}
Write-UqmUtf8JsonAtomic -Path $markerPath -Value $provisionalMarker

$manifest = New-Object System.Collections.ArrayList
$copiedCount = 0
$unchangedCount = 0
$orderedPlan = @($copyPlan.Values | Sort-Object -Property RelativePath)
for ($index = 0; $index -lt $orderedPlan.Count; $index++) {
    $entry = $orderedPlan[$index]
    $activity = 'Installing UQM-HD Traditional Chinese'
    Write-Progress -Activity $activity -Status $entry.RelativePath -PercentComplete (($index * 100) / $orderedPlan.Count)
    $sourceItem = Get-Item -LiteralPath $entry.SourcePath
    $sourceHash = Get-UqmSha256 -Path $entry.SourcePath
    $destination = Join-UqmContainedPath -Root $install -RelativePath $entry.RelativePath
    $isExecutable = [string]::Equals($entry.RelativePath, 'uqm.exe', [StringComparison]::OrdinalIgnoreCase)
    if ($isExecutable -and (Test-Path -LiteralPath $destination -PathType Leaf) -and
        [string]::Equals((Get-UqmSha256 -Path $destination), $script:UqmFinalExecutableSha256,
            [StringComparison]::OrdinalIgnoreCase)) {
        $result = 'unchanged'
    }
    else {
        $result = Copy-UqmFileAtomic -Source $entry.SourcePath -Destination $destination `
            -ExpectedHash $sourceHash -ExpectedLength $sourceItem.Length -ManagedRoot $install
        if ($isExecutable) {
            Invoke-UqmExecutablePatchPipeline -Executable $destination -PythonExecutable $pythonExecutable
        }
    }
    if ($result -eq 'copied') { $copiedCount++ } else { $unchangedCount++ }
    $managedItem = if ($isExecutable) { Get-Item -LiteralPath $destination } else { $sourceItem }
    $managedHash = if ($isExecutable) { Get-UqmSha256 -Path $destination } else { $sourceHash }
    [void]$manifest.Add([ordered]@{
        Path = $entry.RelativePath
        Length = [Int64]$managedItem.Length
        Sha256 = $managedHash
        Kind = $entry.Kind
    })
}
Write-Progress -Activity 'Installing UQM-HD Traditional Chinese' -Completed

$shortcutRecords = New-Object System.Collections.ArrayList
foreach ($specification in $shortcutSpecifications) {
    $canReplace = Test-MarkerListsShortcut -Marker $previousMarker -Path $specification.Path
    $shortcutResult = Write-UqmShortcut -Specification $specification -AllowManagedReplacement:$canReplace
    [void]$shortcutRecords.Add([ordered]@{
        Kind = $specification.Kind
        Path = Get-UqmFullPath -Path $specification.Path
        Target = Get-UqmFullPath -Path $specification.Target
        Arguments = $specification.Arguments
        WorkingDirectory = Get-UqmFullPath -Path $specification.WorkingDirectory
        ResolutionFactor = $specification.ResolutionFactor
        Addon = $specification.Addon
        Result = $shortcutResult
    })
}

$packRecords = New-Object System.Collections.ArrayList
foreach ($packName in $script:UqmPackNames) {
    $manifestPath = 'content/addons/' + $packName
    $manifestEntry = $manifest | Where-Object { $_.Path -eq $manifestPath } | Select-Object -First 1
    [void]$packRecords.Add([ordered]@{
        Name = $packName
        RelativePath = $manifestPath
        Length = $manifestEntry.Length
        Sha256 = $manifestEntry.Sha256
        EntryCount = $packFiles[$packName].EntryCount
    })
}

$finalMarker = [ordered]@{
    SchemaVersion = 1
    ProductId = $script:UqmProductId
    State = 'complete'
    InstalledAtUtc = $installedAtUtc
    UpdatedAtUtc = [DateTime]::UtcNow.ToString('o')
    SourceRoot = $source
    PacksDir = $packs
    InstallRoot = $install
    ProfileDir = $profile
    Executable = 'uqm.exe'
    DefaultArguments = Get-UqmLaunchArguments -ResolutionFactor 2 -Addon 'hires4x-zh_TW' -ProfileDir $profile -Fullscreen
    Files = @($manifest)
    Packs = @($packRecords)
    Shortcuts = @($shortcutRecords)
    SourceFilesExcluded = $excludedCount
}
Write-UqmUtf8JsonAtomic -Path $markerPath -Value $finalMarker

[pscustomobject][ordered]@{
    Status = 'Installed'
    InstallRoot = $install
    ProfileDir = $profile
    Marker = $markerPath
    ManagedFiles = $manifest.Count
    CopiedFiles = $copiedCount
    UnchangedFiles = $unchangedCount
    Shortcuts = $shortcutRecords.Count
}
