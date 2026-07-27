Set-StrictMode -Version 2.0

$script:UqmProductId = 'uqm-hd-zh-tw'
$script:UqmMarkerName = '.uqm-hd-zh-tw-install.json'
$script:UqmPackNames = @(
    'zh_TW.uqm',
    'hires2x-zh_TW.uqm',
    'hires4x-zh_TW.uqm'
)

function Get-UqmFullPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$MustExist,
        [switch]$MustBeDirectory
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw 'A required path was empty.'
    }
    # All filesystem operations in this installer use -LiteralPath. Windows
    # permits '[' and ']' in real filenames (the stock UQM keyboard font uses
    # `[.png`), even though PowerShell's wildcard parser treats '[' specially.
    # Reject only wildcard characters that Windows itself cannot store.
    if ($Path.IndexOfAny([char[]]@([char]42, [char]63)) -ge 0) {
        throw "Wildcard characters are not allowed in managed paths: $Path"
    }
    if ($Path.IndexOfAny([char[]]@([char]0, [char]10, [char]13, [char]34)) -ge 0) {
        throw "The path contains an unsupported control or quote character: $Path"
    }

    $candidate = [Environment]::ExpandEnvironmentVariables($Path)
    if (-not [IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path -Path (Get-Location).ProviderPath -ChildPath $candidate
    }
    try {
        $full = [IO.Path]::GetFullPath($candidate)
    }
    catch {
        throw "The path is invalid: $Path. $($_.Exception.Message)"
    }

    $volumeRoot = [IO.Path]::GetPathRoot($full)
    if ($full.Length -gt $volumeRoot.Length) {
        $full = $full.TrimEnd([char[]]'\/')
    }

    if ($MustExist -and -not (Test-Path -LiteralPath $full)) {
        throw "The required path does not exist: $full"
    }
    if ($MustBeDirectory -and (Test-Path -LiteralPath $full) -and
        -not (Test-Path -LiteralPath $full -PathType Container)) {
        throw "The path must be a directory: $full"
    }
    return $full
}

function Test-UqmPathEqual {
    param([string]$Left, [string]$Right)
    return [string]::Equals(
        (Get-UqmFullPath -Path $Left),
        (Get-UqmFullPath -Path $Right),
        [StringComparison]::OrdinalIgnoreCase)
}

function Test-UqmPathInside {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root,
        [switch]$AllowRoot
    )

    $fullPath = Get-UqmFullPath -Path $Path
    $fullRoot = Get-UqmFullPath -Path $Root
    if ([string]::Equals($fullPath, $fullRoot, [StringComparison]::OrdinalIgnoreCase)) {
        return [bool]$AllowRoot
    }
    $prefix = $fullRoot.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
    return $fullPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
}

function Assert-UqmNotVolumeRoot {
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Role = 'Destination')
    $full = Get-UqmFullPath -Path $Path
    $volumeRoot = [IO.Path]::GetPathRoot($full)
    if ([string]::Equals($full, $volumeRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Role cannot be a filesystem volume root: $full"
    }

    $protected = @(
        $env:SystemRoot,
        $env:ProgramData,
        $env:USERPROFILE,
        [Environment]::GetFolderPath([Environment+SpecialFolder]::Windows),
        [Environment]::GetFolderPath([Environment+SpecialFolder]::System)
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    foreach ($item in $protected) {
        if (Test-UqmPathEqual -Left $full -Right $item) {
            throw "$Role cannot replace a protected directory: $full"
        }
    }
}

function Assert-UqmNoReparseComponents {
    param([Parameter(Mandatory = $true)][string]$Path)

    $full = Get-UqmFullPath -Path $Path
    $volumeRoot = [IO.Path]::GetPathRoot($full)
    $current = $volumeRoot
    $remainder = $full.Substring($volumeRoot.Length)
    foreach ($part in $remainder.Split([char[]]'\/', [StringSplitOptions]::RemoveEmptyEntries)) {
        $current = Join-Path -Path $current -ChildPath $part
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Managed paths cannot cross a reparse point: $current"
            }
        }
    }
}

function Get-UqmRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $fullPath = Get-UqmFullPath -Path $Path
    $fullRoot = Get-UqmFullPath -Path $Root
    $prefix = $fullRoot.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is not below the expected root. Path: $fullPath Root: $fullRoot"
    }
    return $fullPath.Substring($prefix.Length)
}

function Join-UqmContainedPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )
    if ([IO.Path]::IsPathRooted($RelativePath) -or
        [string]::IsNullOrWhiteSpace($RelativePath) -or
        $RelativePath.IndexOfAny([char[]]@([char]0, [char]10, [char]13)) -ge 0) {
        throw "Unsafe relative path: $RelativePath"
    }
    $fullRoot = Get-UqmFullPath -Path $Root
    $combined = Get-UqmFullPath -Path (Join-Path -Path $fullRoot -ChildPath $RelativePath)
    if (-not (Test-UqmPathInside -Path $combined -Root $fullRoot)) {
        throw "Relative path escapes its managed root: $RelativePath"
    }
    return $combined
}

function Get-UqmSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = Get-UqmFullPath -Path $Path -MustExist
    $stream = [IO.File]::Open($full, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $algorithm = [Security.Cryptography.SHA256]::Create()
        try {
            $bytes = $algorithm.ComputeHash($stream)
            return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
        }
        finally {
            $algorithm.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Move-UqmStagedFileIntoPlace {
    param(
        [Parameter(Mandatory = $true)][string]$StagedPath,
        [Parameter(Mandatory = $true)][string]$DestinationPath
    )
    $staged = Get-UqmFullPath -Path $StagedPath -MustExist
    $destination = Get-UqmFullPath -Path $DestinationPath
    $stagedParent = [IO.Path]::GetDirectoryName($staged)
    $destinationParent = [IO.Path]::GetDirectoryName($destination)
    if (-not (Test-UqmPathEqual -Left $stagedParent -Right $destinationParent)) {
        throw 'A staged replacement must be on the same directory and volume as its exact destination.'
    }
    if (Test-Path -LiteralPath $destination) {
        $destinationItem = Get-Item -LiteralPath $destination -Force
        if ($destinationItem.PSIsContainer -or
            (($destinationItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw "Refusing to replace a destination that is not a normal file: $destination"
        }
        $backup = Join-Path -Path $destinationParent -ChildPath ('.uqm-backup-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        try {
            [IO.File]::Replace($staged, $destination, $backup, $true)
        }
        finally {
            if (Test-Path -LiteralPath $backup) {
                Remove-Item -LiteralPath $backup -Force
            }
        }
    }
    else {
        [IO.File]::Move($staged, $destination)
    }
}

function Quote-UqmArgument {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ($Value.IndexOfAny([char[]]@([char]0, [char]10, [char]13, [char]34)) -ge 0) {
        throw 'A command-line path contains an unsupported control or quote character.'
    }
    return '"' + $Value + '"'
}

function Get-UqmLaunchArguments {
    param(
        [Parameter(Mandatory = $true)][ValidateSet(0, 1, 2)][int]$ResolutionFactor,
        [Parameter(Mandatory = $true)][ValidateSet('zh_TW', 'hires2x-zh_TW', 'hires4x-zh_TW')][string]$Addon,
        [Parameter(Mandatory = $true)][string]$ProfileDir,
        [switch]$Fullscreen
    )
    $profile = Get-UqmFullPath -Path $ProfileDir
    if ($Fullscreen) {
        if ($ResolutionFactor -ne 2 -or $Addon -ne 'hires4x-zh_TW') {
            throw 'The legible fullscreen profile requires the 4x Traditional Chinese add-on.'
        }
        return ('-o -r 1920x1080 -f -k -c none --resfactor=2 -C {0} --addon hires4x-zh_TW' -f
            (Quote-UqmArgument -Value $profile))
    }
    $resolution = @('320x240', '640x480', '1280x960')[$ResolutionFactor]
    return ('-x -r {0} -w -c none --resfactor={1} -C {2} --addon {3}' -f
        $resolution, $ResolutionFactor, (Quote-UqmArgument -Value $profile), $Addon)
}

function Get-UqmShortcutSpecifications {
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$ProfileDir
    )

    $install = Get-UqmFullPath -Path $InstallRoot
    $profile = Get-UqmFullPath -Path $ProfileDir
    $exe = Join-UqmContainedPath -Root $install -RelativePath 'uqm.exe'
    $desktop = Get-UqmFullPath -Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory))
    $programs = Get-UqmFullPath -Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::Programs))
    if ([string]::IsNullOrWhiteSpace($desktop) -or [string]::IsNullOrWhiteSpace($programs)) {
        throw 'Windows did not provide the current user Desktop or Start Menu Programs path.'
    }

    # WScript.Shell can expose an ANSI-only CreateShortcut implementation on
    # otherwise Unicode-capable Windows installations.  Keep shortcut paths in
    # ASCII so creation remains reliable regardless of the system code page;
    # the localized game data and UI remain Traditional Chinese.
    $mainLeaf = 'The Ur-Quan Masters HD - Traditional Chinese.lnk'
    $startFolder = Join-Path -Path $programs -ChildPath 'The Ur-Quan Masters HD - Traditional Chinese'

    return @(
        [pscustomobject][ordered]@{
            Kind = 'desktop-default'
            Path = Join-Path -Path $desktop -ChildPath $mainLeaf
            Target = $exe
            Arguments = Get-UqmLaunchArguments -ResolutionFactor 2 -Addon 'hires4x-zh_TW' -ProfileDir $profile -Fullscreen
            WorkingDirectory = $install
            ResolutionFactor = 2
            Addon = 'hires4x-zh_TW'
            AllowedRoot = $desktop
        },
        [pscustomobject][ordered]@{
            Kind = 'start-menu-default'
            Path = Join-Path -Path $startFolder -ChildPath $mainLeaf
            Target = $exe
            Arguments = Get-UqmLaunchArguments -ResolutionFactor 2 -Addon 'hires4x-zh_TW' -ProfileDir $profile -Fullscreen
            WorkingDirectory = $install
            ResolutionFactor = 2
            Addon = 'hires4x-zh_TW'
            AllowedRoot = $programs
        },
        [pscustomobject][ordered]@{
            Kind = 'install-root-1x'
            Path = Join-Path -Path $install -ChildPath 'Launch UQM-HD zh-TW (1x).lnk'
            Target = $exe
            Arguments = Get-UqmLaunchArguments -ResolutionFactor 0 -Addon 'zh_TW' -ProfileDir $profile
            WorkingDirectory = $install
            ResolutionFactor = 0
            Addon = 'zh_TW'
            AllowedRoot = $install
        },
        [pscustomobject][ordered]@{
            Kind = 'install-root-2x'
            Path = Join-Path -Path $install -ChildPath 'Launch UQM-HD zh-TW (2x).lnk'
            Target = $exe
            Arguments = Get-UqmLaunchArguments -ResolutionFactor 1 -Addon 'hires2x-zh_TW' -ProfileDir $profile
            WorkingDirectory = $install
            ResolutionFactor = 1
            Addon = 'hires2x-zh_TW'
            AllowedRoot = $install
        },
        [pscustomobject][ordered]@{
            Kind = 'install-root-4x'
            Path = Join-Path -Path $install -ChildPath 'Launch UQM-HD zh-TW (4x).lnk'
            Target = $exe
            Arguments = Get-UqmLaunchArguments -ResolutionFactor 2 -Addon 'hires4x-zh_TW' -ProfileDir $profile
            WorkingDirectory = $install
            ResolutionFactor = 2
            Addon = 'hires4x-zh_TW'
            AllowedRoot = $install
        }
    )
}

function Get-UqmShortcutDetails {
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = Get-UqmFullPath -Path $Path -MustExist
    if (-not $full.EndsWith('.lnk', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Shortcut path must end in .lnk: $full"
    }

    $shell = New-Object -ComObject WScript.Shell
    try {
        $shortcut = $shell.CreateShortcut($full)
        try {
            return [pscustomobject][ordered]@{
                Path = $full
                Target = $shortcut.TargetPath
                Arguments = $shortcut.Arguments
                WorkingDirectory = $shortcut.WorkingDirectory
                IconLocation = $shortcut.IconLocation
            }
        }
        finally {
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
        }
    }
    finally {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }
}

function Test-UqmShortcutMatches {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)]$Expected
    )
    if (-not (Test-UqmPathEqual -Left $Actual.Target -Right $Expected.Target)) { return $false }
    if (-not (Test-UqmPathEqual -Left $Actual.WorkingDirectory -Right $Expected.WorkingDirectory)) { return $false }
    if (-not [string]::Equals($Actual.Arguments, $Expected.Arguments, [StringComparison]::Ordinal)) { return $false }
    return $true
}

function Write-UqmShortcut {
    param(
        [Parameter(Mandatory = $true)]$Specification,
        [switch]$AllowManagedReplacement
    )

    $path = Get-UqmFullPath -Path $Specification.Path
    $allowedRoot = Get-UqmFullPath -Path $Specification.AllowedRoot
    if (-not (Test-UqmPathInside -Path $path -Root $allowedRoot)) {
        throw "Shortcut is outside its exact allowed root: $path"
    }
    if (-not $path.EndsWith('.lnk', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Shortcut path must end in .lnk: $path"
    }
    Assert-UqmNoReparseComponents -Path ([IO.Path]::GetDirectoryName($path))

    if (Test-Path -LiteralPath $path) {
        $existingItem = Get-Item -LiteralPath $path -Force
        if (($existingItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to replace a shortcut reparse point: $path"
        }
        $existingMatches = $false
        try {
            $existing = Get-UqmShortcutDetails -Path $path
            $existingMatches = Test-UqmShortcutMatches -Actual $existing -Expected $Specification
        }
        catch {
            if (-not $AllowManagedReplacement) {
                throw "An unmanaged shortcut exists but cannot be validated: $path. $($_.Exception.Message)"
            }
        }
        if ($existingMatches) {
            return 'unchanged'
        }
        if (-not $AllowManagedReplacement) {
            throw "An unmanaged shortcut already exists with different settings: $path"
        }
    }

    $directory = [IO.Path]::GetDirectoryName($path)
    if (-not (Test-Path -LiteralPath $directory)) {
        [void](New-Item -ItemType Directory -Path $directory)
    }
    $temporary = Join-Path -Path $directory -ChildPath ('.uqm-shortcut-' + [Guid]::NewGuid().ToString('N') + '.lnk')
    $shell = New-Object -ComObject WScript.Shell
    try {
        $shortcut = $shell.CreateShortcut($temporary)
        try {
            $shortcut.TargetPath = $Specification.Target
            $shortcut.Arguments = $Specification.Arguments
            $shortcut.WorkingDirectory = $Specification.WorkingDirectory
            $shortcut.IconLocation = $Specification.Target + ',0'
            $shortcut.Description = 'The Ur-Quan Masters HD - Traditional Chinese'
            $shortcut.Save()
        }
        finally {
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
        }
    }
    finally {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }

    try {
        $written = Get-UqmShortcutDetails -Path $temporary
        if (-not (Test-UqmShortcutMatches -Actual $written -Expected $Specification)) {
            throw "The staged shortcut did not retain its exact target and arguments: $path"
        }
        Move-UqmStagedFileIntoPlace -StagedPath $temporary -DestinationPath $path
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
    return 'written'
}

function Assert-UqmArchive {
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = Get-UqmFullPath -Path $Path -MustExist
    if ((Get-Item -LiteralPath $full).Length -le 0) {
        throw "The UQM add-on archive is empty: $full"
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    try {
        $archive = [IO.Compression.ZipFile]::OpenRead($full)
    }
    catch {
        throw "The UQM add-on is not a readable ZIP-compatible archive: $full. $($_.Exception.Message)"
    }
    try {
        if ($archive.Entries.Count -eq 0) {
            throw "The UQM add-on archive has no entries: $full"
        }
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName.Replace('\', '/')
            if ($name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name.IndexOf([char]0) -ge 0) {
                throw "The UQM add-on contains an unsafe member path: $name"
            }
        }
        return $archive.Entries.Count
    }
    finally {
        $archive.Dispose()
    }
}

function Write-UqmUtf8JsonAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Value,
        [int]$Depth = 8
    )
    $full = Get-UqmFullPath -Path $Path
    $parent = [IO.Path]::GetDirectoryName($full)
    if (-not (Test-Path -LiteralPath $parent)) {
        [void](New-Item -ItemType Directory -Path $parent)
    }
    $temporary = Join-Path -Path $parent -ChildPath ('.uqm-json-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $encoding = New-Object Text.UTF8Encoding($false)
    try {
        $json = $Value | ConvertTo-Json -Depth $Depth
        [IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, $encoding)
        Move-UqmStagedFileIntoPlace -StagedPath $temporary -DestinationPath $full
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Read-UqmInstallMarker {
    param([Parameter(Mandatory = $true)][string]$InstallRoot)
    $install = Get-UqmFullPath -Path $InstallRoot
    $markerPath = Join-UqmContainedPath -Root $install -RelativePath $script:UqmMarkerName
    if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
        return $null
    }
    try {
        $marker = Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "The existing installation marker is not valid JSON: $markerPath. $($_.Exception.Message)"
    }
    if ($marker.SchemaVersion -ne 1 -or $marker.ProductId -ne $script:UqmProductId) {
        throw "The existing marker is not for this installer: $markerPath"
    }
    if (-not (Test-UqmPathEqual -Left $marker.InstallRoot -Right $install)) {
        throw "The installation marker names a different install root: $($marker.InstallRoot)"
    }
    return $marker
}
