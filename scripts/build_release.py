from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import zipfile


PACKS = {
    "zh_TW.uqm": (
        20_992_002,
        "86235cf2631490761e9b8dd7e7c55ac4bd9177c1952a585e2863d898d403e98d",
    ),
    "hires2x-zh_TW.uqm": (
        39_587_398,
        "81a0467b6b65ed2e17e673dbf7b4e0cc55bfdb7c241aca638c0add4daa8f25f9",
    ),
    "hires4x-zh_TW.uqm": (
        57_691_453,
        "efe77272bc45451330973051d33df06d758b57e577b972fbcc03e05e15a6ddac",
    ),
}

SOURCE_FILES = (
    "LICENSE",
    "NOTICE.md",
    "LICENSES/UPSTREAM-COPYING.txt",
    "LICENSES/OFL-1.1-NotoSansCJK.txt",
    "tools/install/Install-UqmHdZhTw.ps1",
    "tools/install/UqmInstall.Common.ps1",
    "tools/install/Test-UqmHdZhTwInstall.ps1",
    "tools/install/patch_uqm_hd_menu_highlight.py",
    "tools/install/patch_uqm_hd_super_melee_escape.py",
    "tools/install/README.md",
)

INSTALL_TEXT = """UQM-HD 繁體中文版 v{version} — Windows 安裝說明

本壓縮檔不包含原版遊戲或已修改的 uqm.exe。請先從 UQM-HD 的官方
SourceForge 專案取得 Windows Beta 1，並解壓縮至獨立目錄。

需求：
- Windows PowerShell 5.1 或 PowerShell 7
- Python 3.10 以上，且 python 指令可由 PATH 執行
- 原版目錄須包含 uqm.exe、content 及 content\\addons

建議安裝方式：

1. 將本壓縮檔完整解壓縮；三個 .uqm 檔及 tools 目錄須保留原位置。
2. 先在解壓縮目錄開啟 PowerShell，執行唯讀演練：

   powershell.exe -NoProfile -ExecutionPolicy Bypass `
     -File .\\tools\\install\\Install-UqmHdZhTw.ps1 `
     -SourceRoot C:\\path\\to\\UQM-HD `
     -PacksDir . `
     -InstallRoot C:\\Games\\UQM-HD-TW `
     -ProfileDir "$env:APPDATA\\UQM-HD-zh_TW" `
     -PlanOnly

3. 確認演練結果後，以相同命令移除最後的 -PlanOnly 正式安裝。
4. 從桌面或開始選單開啟
   "The Ur-Quan Masters HD - Traditional Chinese"；預設是 4x、全螢幕、
   1920x1080。其他螢幕可修改捷徑中的 -r 解析度。F11 可切換全螢幕。

安裝器只讀取 SourceRoot，另建受管理的目的地副本。它會驗證三個套件，並在
目的地副本上套用主選單反白及 Super Melee Esc 功能的雜湊鎖定補丁；未知
uqm.exe 版本會被拒絕。它不會散布或覆寫原版目錄中的執行檔。

完整玩法、船艦圖鑑、原始碼、限制及疑難排解：
https://github.com/blhsing/uqm-hd-traditional-chinese

套件 SHA-256 請見 SHA256SUMS。授權及歸屬請見 LICENSE、NOTICE.md 與
LICENSES 目錄。本地化遊戲內容採 CC BY-NC-SA 2.5，不得作商業用途。
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream(source) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def verify_packs(packs_dir: Path) -> None:
    for name, (expected_size, expected_hash) in PACKS.items():
        path = packs_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"required release pack is missing: {path}")
        if path.stat().st_size != expected_size:
            raise ValueError(
                f"wrong size for {name}: expected {expected_size}, got {path.stat().st_size}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"wrong SHA-256 for {name}: expected {expected_hash}, got {actual_hash}"
            )


def write_file(archive: zipfile.ZipFile, arcname: str, source: Path) -> None:
    with source.open("rb") as input_file, archive.open(zip_info(arcname), "w") as output:
        shutil.copyfileobj(input_file, output, length=1024 * 1024)


def verify_release_archive(
    archive_path: Path,
    *,
    repo_root: Path,
    version: str,
    install_text: bytes,
    checksum_text: bytes,
) -> None:
    prefix = f"uqm-hd-zh-tw-v{version}"
    expected_names = {
        *(f"{prefix}/{name}" for name in PACKS),
        f"{prefix}/INSTALL.zh-TW.txt",
        f"{prefix}/SHA256SUMS",
        *(f"{prefix}/{relative}" for relative in SOURCE_FILES),
    }
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected_names:
            raise ValueError("release archive entries do not match the exact manifest")
        if archive.testzip() is not None:
            raise ValueError("release archive failed its CRC integrity check")
        for info in archive.infolist():
            if info.compress_type != zipfile.ZIP_STORED:
                raise ValueError(f"release entry was unexpectedly compressed: {info.filename}")
            if info.date_time != (1980, 1, 1, 0, 0, 0):
                raise ValueError(f"release entry has a nondeterministic timestamp: {info.filename}")
            if info.filename.lower().endswith(".exe"):
                raise ValueError("release archive must not contain an executable")
        for name, (expected_size, expected_hash) in PACKS.items():
            info = archive.getinfo(f"{prefix}/{name}")
            if info.file_size != expected_size:
                raise ValueError(f"release archive has the wrong size for {name}")
            with archive.open(info) as source:
                if sha256_stream(source) != expected_hash:
                    raise ValueError(f"release archive has the wrong SHA-256 for {name}")
        if archive.read(f"{prefix}/INSTALL.zh-TW.txt") != install_text:
            raise ValueError("release installation instructions changed after writing")
        if archive.read(f"{prefix}/SHA256SUMS") != checksum_text:
            raise ValueError("release checksum manifest changed after writing")
        for relative in SOURCE_FILES:
            if archive.read(f"{prefix}/{relative}") != (repo_root / relative).read_bytes():
                raise ValueError(f"release source file changed after writing: {relative}")


def build_release(
    *, repo_root: Path, packs_dir: Path, output: Path, version: str, force: bool
) -> None:
    verify_packs(packs_dir)
    for relative in SOURCE_FILES:
        if not (repo_root / relative).is_file():
            raise FileNotFoundError(f"required repository file is missing: {relative}")
    if output.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {output}; pass --force to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"uqm-hd-zh-tw-v{version}"
    checksum_text = "".join(
        f"{expected_hash}  {name}\n"
        for name, (_, expected_hash) in PACKS.items()
    ).encode("ascii")
    install_text = INSTALL_TEXT.format(version=version).encode("utf-8")

    with tempfile.NamedTemporaryFile(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(
            temporary_path, "w", allowZip64=False, strict_timestamps=True
        ) as archive:
            for name in PACKS:
                write_file(archive, f"{prefix}/{name}", packs_dir / name)
            archive.writestr(zip_info(f"{prefix}/INSTALL.zh-TW.txt"), install_text)
            archive.writestr(zip_info(f"{prefix}/SHA256SUMS"), checksum_text)
            for relative in SOURCE_FILES:
                write_file(archive, f"{prefix}/{relative}", repo_root / relative)
        verify_release_archive(
            temporary_path,
            repo_root=repo_root,
            version=version,
            install_text=install_text,
            checksum_text=checksum_text,
        )
        os.replace(temporary_path, output)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the verified standalone Traditional-Chinese release ZIP."
    )
    parser.add_argument("--packs-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="0.1.1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    build_release(
        repo_root=repo_root,
        packs_dir=args.packs_dir.resolve(),
        output=args.output.resolve(),
        version=args.version,
        force=args.force,
    )
    print(f"built {args.output.resolve()}")
    print(f"sha256 {sha256_file(args.output.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
