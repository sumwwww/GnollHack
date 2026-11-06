#!/usr/bin/env python3
"""Validate and stage the reviewed zh-CN game-data text overlay."""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


FILES = (
    "dat/help",
    "dat/cmdhelp",
    "dat/keyhelp",
    "dat/hh",
    "dat/opthelp",
    "dat/wizhelp",
    "dat/quest.txt",
    "dat/oracles.txt",
    "dat/history",
    "dat/epitaph.txt",
    "dat/engrave.txt",
    "dat/bogusmon.txt",
    "dat/credits",
    "dat/xcredits",
    "doc/Guidebook.txt",
)
PRINTF = re.compile(
    r"%(?:%|(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspn])"
)
GAME = re.compile(r"%(?:[A-Za-z]|\d+|%)")
CJK = re.compile(r"[\u3400-\u9fff]")


def read_utf8(path: Path) -> tuple[str, bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"UTF-8 BOM is not allowed: {path}")
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return text, raw


def tab_keys(text: str) -> list[str]:
    return [line.split("\t", 1)[0] for line in text.splitlines() if "\t" in line]


def option_keys(text: str) -> list[str]:
    return re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_-]*)\s{2,}", text)


def validate(repo: Path) -> tuple[list[str], list[str]]:
    overlay = repo / "tools_zh_CN" / "content_zh_CN"
    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest = json.loads((overlay / "MANIFEST.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Cannot read content manifest: {exc}"], warnings
    if manifest.get("locale") != "zh-CN" or tuple(manifest.get("files", ())) != FILES:
        errors.append("MANIFEST.json must list the complete approved zh-CN content file set in order")

    disk_files = {
        path.relative_to(overlay).as_posix()
        for path in overlay.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    if disk_files != set(FILES):
        errors.append("Content overlay has missing or unexpected files")

    source_text: dict[str, str] = {}
    translated_text: dict[str, str] = {}
    for rel in FILES:
        source_path = repo / rel
        translated_path = overlay / rel
        if not source_path.is_file() or not translated_path.is_file():
            errors.append(f"Missing source or translated file: {rel}")
            continue
        try:
            source_text[rel], _ = read_utf8(source_path)
            translated_text[rel], _ = read_utf8(translated_path)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{rel}: {exc}")
            continue
        translated = translated_text[rel]
        if "\ufffd" in translated:
            errors.append(f"{rel}: contains Unicode replacement characters")
        if not CJK.search(translated):
            errors.append(f"{rel}: no Simplified Chinese text found")
        if PRINTF.findall(source_text[rel]) != PRINTF.findall(translated):
            errors.append(f"{rel}: printf placeholders changed")
        if GAME.findall(source_text[rel]) != GAME.findall(translated):
            errors.append(f"{rel}: game control tokens changed")

    for rel in ("dat/cmdhelp", "dat/keyhelp"):
        if rel in source_text and rel in translated_text and tab_keys(source_text[rel]) != tab_keys(translated_text[rel]):
            errors.append(f"{rel}: command/key identifiers before TAB changed")

    if "dat/opthelp" in source_text and "dat/opthelp" in translated_text:
        if option_keys(source_text["dat/opthelp"]) != option_keys(translated_text["dat/opthelp"]):
            errors.append("dat/opthelp: option identifiers changed")

    if "dat/quest.txt" in source_text and "dat/quest.txt" in translated_text:
        for pattern, label in ((r"(?m)^#.*$", "comments"), (r"(?m)^%Cc.*$", "%Cc records"),
                               (r"(?m)^%Cp.*$", "%Cp records"), (r"(?m)^%E.*$", "%E records")):
            if re.findall(pattern, source_text["dat/quest.txt"]) != re.findall(pattern, translated_text["dat/quest.txt"]):
                errors.append(f"dat/quest.txt: {label} changed")

    if "dat/oracles.txt" in source_text and "dat/oracles.txt" in translated_text:
        if [line for line in source_text["dat/oracles.txt"].splitlines() if line.strip() == "-----"] != [
            line for line in translated_text["dat/oracles.txt"].splitlines() if line.strip() == "-----"
        ]:
            errors.append("dat/oracles.txt: oracle separators changed")

    if "dat/bogusmon.txt" in source_text and "dat/bogusmon.txt" in translated_text:
        def special_prefixes(text: str) -> list[str]:
            return [line[:1] for line in text.splitlines() if line and line[0] in "+_-|="]
        if special_prefixes(source_text["dat/bogusmon.txt"]) != special_prefixes(translated_text["dat/bogusmon.txt"]):
            errors.append("dat/bogusmon.txt: special name prefixes changed")

    if "dat/engrave.txt" in translated_text:
        for literal in ("Elbereth", "ad aerarium", "A.S. ->", "<- A.S.", "notary sojak", "^?MAIL"):
            if literal in source_text.get("dat/engrave.txt", "") and literal not in translated_text["dat/engrave.txt"]:
                errors.append(f"dat/engrave.txt: protected engraving text missing: {literal}")

    if "doc/Guidebook.txt" in source_text and "doc/Guidebook.txt" in translated_text:
        chapter_pattern = r"(?m)^ {10}(1[0-2]|[1-9])\.\s+"
        source_chapters = re.findall(chapter_pattern, source_text["doc/Guidebook.txt"])
        translated_chapters = re.findall(chapter_pattern, translated_text["doc/Guidebook.txt"])
        if source_chapters != translated_chapters:
            errors.append("doc/Guidebook.txt: main chapter heading sequence changed")
        source_blank = sum(not line.strip() for line in source_text["doc/Guidebook.txt"].splitlines())
        translated_blank = sum(not line.strip() for line in translated_text["doc/Guidebook.txt"].splitlines())
        if source_blank != translated_blank:
            warnings.append(
                f"doc/Guidebook.txt: blank-line layout was normalized ({source_blank} source, {translated_blank} translated)"
            )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and stage the Simplified Chinese game-data overlay")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="GnollHack repository root")
    parser.add_argument("--check-only", action="store_true", help="validate without copying any files")
    args = parser.parse_args()
    repo = args.repo.resolve()
    errors, warnings = validate(repo)
    for warning in warnings:
        print("[WARN]", warning)
    if errors:
        for error in errors:
            print("[ERROR]", error)
        print(f"Content validation failed: {len(errors)} error(s)")
        return 1
    print(f"Validated {len(FILES)} zh-CN content files; errors: 0")
    if args.check_only:
        return 0
    overlay = repo / "tools_zh_CN" / "content_zh_CN"
    for rel in FILES:
        destination = repo / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(overlay / rel, destination)
    print(f"Applied {len(FILES)} zh-CN content files to the native build inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
