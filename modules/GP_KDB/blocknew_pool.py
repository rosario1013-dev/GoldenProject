"""Zhaoshang / Tongdaxin custom blocks in T0002/blocknew.

``blocknew.cfg`` records are 120 bytes: 50-byte GBK name + 70-byte filename
(without ``.blk``). ``*.blk`` files list 7-character codes, one per line.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

DEFAULT_BLOCKNEW_DIR = Path(r"C:\zd_zsone\T0002\blocknew")
CFG_NAME = "blocknew.cfg"
RECORD_SIZE = 120
NAME_SIZE = 50
FILE_SIZE = 70
PROTECTED_FILES = {"zxg", "zxgmore", "blocknew", "tjg"}

_lock = threading.Lock()


def blocknew_dir() -> Path:
    raw = os.environ.get("GP_POOL_BLOCKNEW", "").strip()
    return Path(raw) if raw else DEFAULT_BLOCKNEW_DIR


def ide_to_code(ide: str) -> str:
    text = (ide or "").strip().lower()
    if len(text) < 8 or text[:2] not in {"sh", "sz", "bj"}:
        raise ValueError(f"无法写入板块的股票代码: {ide}")
    market = {"sz": "0", "sh": "1", "bj": "2"}[text[:2]]
    return market + text[2:8]


def code_to_ide(token: str) -> str:
    text = (token or "").strip()
    if len(text) < 7 or not text[:7].isdigit():
        return ""
    prefix = {"0": "sz", "1": "sh", "2": "bj"}.get(text[0])
    if not prefix:
        return ""
    return prefix + text[1:7]


def _decode_field(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("gbk", errors="replace").strip()


def _pack_record(name: str, filename: str) -> bytes:
    try:
        name_raw = name.encode("gbk")
    except UnicodeEncodeError as exc:
        raise ValueError("分类名包含板块文件无法保存的字符") from exc
    if not name_raw or len(name_raw) > NAME_SIZE:
        raise ValueError("分类名过长，请控制在约 10 个汉字以内")
    file_raw = filename.encode("ascii")
    if not file_raw or len(file_raw) > FILE_SIZE:
        raise ValueError("板块文件名无效")
    return name_raw.ljust(NAME_SIZE, b"\x00") + file_raw.ljust(FILE_SIZE, b"\x00")


def _read_cfg(folder: Path) -> list[dict]:
    path = folder / CFG_NAME
    if not path.exists():
        return []
    data = path.read_bytes()
    usable = len(data) - (len(data) % RECORD_SIZE)
    records = []
    for offset in range(0, usable, RECORD_SIZE):
        raw = data[offset : offset + RECORD_SIZE]
        name = _decode_field(raw[:NAME_SIZE])
        filename = _decode_field(raw[NAME_SIZE:])
        if not name or not filename:
            continue
        records.append({"name": name, "filename": filename, "raw": raw})
    return records


def _write_cfg(folder: Path, records: list[dict]) -> None:
    payload = b"".join(record["raw"] for record in records)
    _atomic_write(folder / CFG_NAME, payload)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_bytes(payload)
        os.replace(tmp, path)
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError("无法写入招商证券板块文件，请确认客户端没有占用该文件") from exc


def _blk_path(folder: Path, filename: str) -> Path:
    direct = folder / f"{filename}.blk"
    if direct.exists():
        return direct
    wanted = filename.lower()
    for path in folder.glob("*.blk"):
        if path.stem.lower() == wanted:
            return path
    return direct


def _read_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    codes: list[str] = []
    seen: set[str] = set()
    for line in path.read_bytes().decode("ascii", errors="ignore").splitlines():
        token = line.strip()
        if len(token) < 7 or not token[:7].isdigit():
            continue
        code = token[:7]
        if code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes


def _write_codes(path: Path, codes: list[str]) -> None:
    body = "".join(f"{code}\r\n" for code in codes)
    _atomic_write(path, body.encode("ascii"))


def _filename_taken(records: list[dict], folder: Path, filename: str) -> bool:
    wanted = filename.lower()
    if any(record["filename"].lower() == wanted for record in records):
        return True
    return any(path.stem.lower() == wanted for path in folder.glob("*.blk"))


def _new_filename(name: str, records: list[dict], folder: Path) -> str:
    ascii_name = "".join(ch for ch in name if ch.isascii() and ch.isalnum())
    if (
        ascii_name
        and ascii_name.lower() not in PROTECTED_FILES
        and not _filename_taken(records, folder, ascii_name)
    ):
        return ascii_name[:16]
    number = 1
    while True:
        candidate = f"P{number:03d}"
        if candidate.lower() not in PROTECTED_FILES and not _filename_taken(records, folder, candidate):
            return candidate
        number += 1


def _find(records: list[dict], category: str) -> dict | None:
    name = (category or "").strip()
    for record in records:
        if record["name"] == name:
            return record
    return None


def list_categories() -> list[str]:
    folder = blocknew_dir()
    with _lock:
        return [record["name"] for record in _read_cfg(folder)]


def create_category(category: str) -> dict:
    name = (category or "").strip()
    if not name or name in {".", ".."} or any(ch in name for ch in "\\/:*?\"<>|"):
        raise ValueError("分类名无效")
    folder = blocknew_dir()
    with _lock:
        records = _read_cfg(folder)
        existing = _find(records, name)
        if existing:
            _blk_path(folder, existing["filename"]).touch(exist_ok=True)
            return {"category": name, "filename": existing["filename"]}
        filename = _new_filename(name, records, folder)
        records.append({"name": name, "filename": filename, "raw": _pack_record(name, filename)})
        _write_cfg(folder, records)
        blk = folder / f"{filename}.blk"
        if not blk.exists():
            _write_codes(blk, [])
        return {"category": name, "filename": filename}


def delete_category(category: str) -> bool:
    name = (category or "").strip()
    if not name:
        raise ValueError("category is required")
    folder = blocknew_dir()
    with _lock:
        records = _read_cfg(folder)
        found = _find(records, name)
        if not found:
            return False
        if found["filename"].lower() in PROTECTED_FILES:
            raise ValueError("不能删除招商证券自选股板块")
        _write_cfg(folder, [record for record in records if record["name"] != name])
        blk = _blk_path(folder, found["filename"])
        try:
            blk.unlink(missing_ok=True)
        except OSError as exc:
            raise ValueError("板块索引已更新，但板块文件正在被占用，未能删除") from exc
        return True


def codes_for_category(category: str) -> list[str]:
    folder = blocknew_dir()
    with _lock:
        found = _find(_read_cfg(folder), category)
        if not found:
            return []
        return _read_codes(_blk_path(folder, found["filename"]))


def categories_for_code(code: str) -> list[str]:
    folder = blocknew_dir()
    names = []
    with _lock:
        for record in _read_cfg(folder):
            if code in _read_codes(_blk_path(folder, record["filename"])):
                names.append(record["name"])
    return names


def all_memberships() -> dict[str, list[str]]:
    """Map blk code -> category names, in cfg order."""
    folder = blocknew_dir()
    grouped: dict[str, list[str]] = {}
    with _lock:
        for record in _read_cfg(folder):
            for code in _read_codes(_blk_path(folder, record["filename"])):
                grouped.setdefault(code, []).append(record["name"])
    return grouped


def add_code(category: str, code: str) -> None:
    folder = blocknew_dir()
    with _lock:
        records = _read_cfg(folder)
        found = _find(records, category)
        if not found:
            raise ValueError("分类不存在")
        path = _blk_path(folder, found["filename"])
        codes = _read_codes(path)
        if code not in codes:
            codes.append(code)
            _write_codes(path, codes)


def remove_code(category: str, code: str) -> None:
    folder = blocknew_dir()
    with _lock:
        found = _find(_read_cfg(folder), category)
        if not found:
            return
        path = _blk_path(folder, found["filename"])
        codes = [item for item in _read_codes(path) if item != code]
        _write_codes(path, codes)
