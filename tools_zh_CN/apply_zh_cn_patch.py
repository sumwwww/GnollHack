#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Display-only zh-CN localization generator. Preserves native compiler keys and encodings. See REPAIR_STATUS.md for scope and remaining work."""

import argparse
import json
import os
import re
import shutil
import sys
from xml.sax.saxutils import escape
from pathlib import Path

PRINTF_TOKEN_RE = re.compile(
    r"%(?:%|(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspn])"
)


def strip_bom_and_write_utf8(path: Path, text: str):
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def backup_file(path: Path):
    bak = path.with_suffix(path.suffix + ".bak_en")
    if not bak.exists() and path.exists():
        shutil.copy2(path, bak)


def parse_c_kv_tables(c_file_path: Path) -> dict:
    """从 *_zh_cn.c / *.h 词库文件中解析所有 {"en", "zh"} 键值对"""
    mapping = {}
    if not c_file_path.exists():
        return mapping
    content = c_file_path.read_text(encoding="utf-8-sig")
    pattern = re.compile(r'\{\s*"((?:[^"\\]|\\.)*)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\}')
    for m in pattern.finditer(content):
        en_key, zh_val = m.group(1), m.group(2)
        if en_key and zh_val:
            mapping[en_key] = zh_val
    return mapping




def patch_xaml_files(repo_root: Path, xaml_dict_path: Path):
    if not xaml_dict_path.exists():
        return
    data = json.loads(xaml_dict_path.read_text(encoding="utf-8-sig"))
    translations = data.get("translations", {})
    attrs = data.get("attributes_to_translate", ["Text", "Title", "Placeholder"])

    xpl_dir = repo_root / "win" / "win32" / "xpl" / "GnollHackX"
    if not xpl_dir.exists():
        print("[SKIP] 未找到 win/win32/xpl/GnollHackX 目录")
        return

    count = 0
    for xaml_file in xpl_dir.rglob("*.xaml"):
        text = xaml_file.read_text(encoding="utf-8-sig", errors="replace")
        orig = text
        for attr in attrs:
            for en_str, zh_str in translations.items():
                pattern = attr + '="' + escape(en_str, {chr(34): "&quot;"}) + '"'
                replacement = attr + '="' + escape(zh_str, {chr(34): "&quot;"}) + '"'
                text = text.replace(pattern, replacement)
        if text != orig:
            backup_file(xaml_file)
            strip_bom_and_write_utf8(xaml_file, text)
            count += 1
    print(f"[OK] 已完成 GnollHackX 下 {count} 个共享 XAML 视图的简体中文注入")




def extract_untranslated_strings(repo_root: Path, full_dict: dict, out_json: Path):
    src_dir = repo_root / "src"
    if not src_dir.exists():
        print("[WARN] 未找到 src/ 目录，无法扫描未翻译字符串")
        return
    msg_Regex = re.compile(r'\b(?:pline|You|Your|verbalize|You_feel|You_hear|pline_The|There)\s*\(\s*"((?:[^"\\]|\\.)*)"')
    untranslated = {}
    for c_file in sorted(src_dir.glob("*.c")):
        text = c_file.read_text(encoding="utf-8-sig", errors="replace")
        for m in msg_Regex.finditer(text):
            s = m.group(1)
            if s and s not in full_dict and not any(ord(ch) > 127 for ch in s):
                untranslated.setdefault(c_file.name, []).append(s)

    strip_bom_and_write_utf8(out_json, json.dumps(untranslated, ensure_ascii=False, indent=2) + "\n")
    total = sum(len(v) for v in untranslated.values())
    print(f"[OK] 已导出 {total} 条待增量翻译的动态消息字符串至 {out_json}")


def restore_backups(repo_root: Path):
    count = 0
    for bak in repo_root.rglob("*.bak_en"):
        orig = bak.with_suffix("")
        shutil.move(str(bak), str(orig))
        count += 1
    print(f"[OK] 已还原 {count} 个原始英文源码文件")


def patch_xaml_files_at_maui_root(repo_root, patch_root):
    data = json.loads((patch_root / "win/win32/xpl/GnollHackX/XamlTranslationDict_zh_CN.json").read_text(encoding="utf-8-sig"))
    for path in (repo_root / "win/win32/xpl/GnollHackM").rglob("*.xaml"):
        if any(part in ("bin", "obj") for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig")
        original = text
        for attr in data["attributes_to_translate"]:
            for en, zh in data["translations"].items():
                text = text.replace(attr + "=" + chr(34) + escape(en, {chr(34): "&quot;"}) + chr(34), attr + "=" + chr(34) + escape(zh, {chr(34): "&quot;"}) + chr(34))
        if text != original:
            backup_file(path)
            strip_bom_and_write_utf8(path, text)

def generate_runtime_dictionary(repo_root, mapping, patch_root):
    data = json.loads((patch_root / "win/win32/xpl/GnollHackX/XamlTranslationDict_zh_CN.json").read_text(encoding="utf-8-sig"))
    mapping = dict(mapping)
    mapping.update(data["translations"])
    entries = ["            [" + json.dumps(en, ensure_ascii=False) + "] = " + json.dumps(zh, ensure_ascii=False) + "," for en, zh in sorted(mapping.items())]

    native_path = repo_root / "tools_zh_CN" / "native_messages_zh_CN.json"
    native_items = []
    if native_path.exists():
        native_items = json.loads(native_path.read_text(encoding="utf-8-sig"))["items"]
    rules = build_message_rules(native_items)
    message_entries = [
        "            new MessageRule(" + csharp_string(rule[0]) + ", " + csharp_string(rule[1]) + ", "
        + csharp_string(rule[2]) + ", " + str(rule[3]) + ", " + str(rule[4]) + ", " + str(rule[5]) + "),"
        for rule in rules
    ]
    target = repo_root / "win/win32/xpl/GnollHackM/GnhZhCnDictionary.g.cs"
    source = (
        "// Generated by apply_zh_cn_patch.py. Display strings only.\n"
        "namespace GnollHackX { internal static partial class GnhDisplayLocalization {\n"
        "    private static readonly System.Collections.Generic.Dictionary<string, string> Words = "
        "new System.Collections.Generic.Dictionary<string, string>(System.StringComparer.OrdinalIgnoreCase) {\n"
        + "\n".join(entries)
        + "\n    };\n"
        "    private static readonly MessageRule[] Messages = new MessageRule[] {\n"
        + "\n".join(message_entries)
        + "\n    };\n} }\n"
    )
    strip_bom_and_write_utf8(target, source)
    print("[OK] Generated", len(mapping), "exact display translations and", len(rules), "formatted message patterns")


def csharp_string(value: str) -> str:
    """Return a regular C# string literal for generated source."""
    return json.dumps(value, ensure_ascii=False).replace("\\/", "/")


def decode_c_string(value: str) -> str:
    """Decode the common C escapes retained by the source-string extractor."""
    simple = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v", "\\": "\\", '"': '"', "'": "'", "?": "?"}
    out = []
    i = 0
    while i < len(value):
        if value[i] != "\\" or i + 1 >= len(value):
            out.append(value[i])
            i += 1
            continue
        nxt = value[i + 1]
        if nxt in simple:
            out.append(simple[nxt])
            i += 2
        elif nxt in "01234567":
            j = i + 1
            while j < min(i + 4, len(value)) and value[j] in "01234567":
                j += 1
            out.append(chr(int(value[i + 1:j], 8)))
            i = j
        elif nxt == "x":
            j = i + 2
            while j < len(value) and value[j] in "0123456789abcdefABCDEF":
                j += 1
            if j == i + 2:
                out.extend(("\\", "x"))
                i += 2
            else:
                out.append(chr(int(value[i + 2:j], 16)))
                i = j
        else:
            # Preserve unknown escapes so the matcher cannot silently alter text.
            out.extend(("\\", nxt))
            i += 2
    return "".join(out)


def printf_pattern(format_string: str):
    """Build an anchored regex and return its literal runs for trigram indexing."""
    pieces = [r"\A"]
    literals = []
    group_count = 0
    type_specificity = 0
    cursor = 0
    for match in PRINTF_TOKEN_RE.finditer(format_string):
        literal = format_string[cursor:match.start()]
        pieces.append(re.escape(literal))
        if literal:
            literals.append(literal)
        token = match.group(0)
        conversion = token[-1]
        if token == "%%":
            pieces.append(re.escape("%"))
            literals.append("%")
        elif conversion == "n":
            # %n writes through a pointer and contributes no visible text.
            pass
        else:
            group = "(?<p" + str(group_count) + ">"
            if conversion == "s":
                capture_pattern = r"[\s\S]*?"
            elif conversion in "di":
                capture_pattern = r"(?:\s*)(?:[-+]?[0-9]+)(?:\s*)"
                type_specificity += 1
            elif conversion == "u":
                capture_pattern = r"(?:\s*)(?:[0-9]+)(?:\s*)"
                type_specificity += 1
            elif conversion in "xX":
                capture_pattern = r"(?:\s*)(?:(?:0[xX])?[0-9A-Fa-f]+)(?:\s*)"
                type_specificity += 1
            elif conversion == "o":
                capture_pattern = r"(?:\s*)(?:0?[0-7]+)(?:\s*)"
                type_specificity += 1
            elif conversion in "fFeEgG":
                capture_pattern = r"(?:\s*)(?:[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)(?:\s*)"
                type_specificity += 1
            elif conversion in "aA":
                capture_pattern = r"(?:\s*)(?:[-+]?(?:0[xX])?(?:[0-9A-Fa-f]+(?:\.[0-9A-Fa-f]*)?|\.[0-9A-Fa-f]+)(?:[pP][-+]?[0-9]+)?)(?:\s*)"
                type_specificity += 1
            elif conversion == "c":
                capture_pattern = r"[\s\S]"
                type_specificity += 1
            elif conversion == "p":
                capture_pattern = r"(?:\s*)(?:(?:0[xX])?[0-9A-Fa-f]+)(?:\s*)"
                type_specificity += 1
            else:
                capture_pattern = r"[\s\S]*?"
            pieces.append(group + capture_pattern + ")")
            group_count += 1
        cursor = match.end()
    literal = format_string[cursor:]
    pieces.append(re.escape(literal))
    if literal:
        literals.append(literal)
    pieces.append(r"\z")
    return "".join(pieces), literals, group_count, type_specificity


def build_message_rules(items):
    """Create runtime C printf-template matchers without changing native identifiers."""
    candidates = []
    seen = set()
    for item in items:
        source = item.get("source", "")
        translated = item.get("translation", "")
        if not source or not translated or source.strip() == translated.strip():
            continue
        prefixes = item.get("prefixes") or [""]
        for prefix in prefixes:
            runtime_source = decode_c_string(prefix + source)
            runtime_translation = decode_c_string(translated)
            pattern, literals, group_count, type_specificity = printf_pattern(runtime_source)
            useful_literals = [part for part in literals if len(part) >= 3]
            # A capture-only or nearly empty template (for example "%s") would
            # match unrelated game text, so keep it out of the runtime rules.
            if not useful_literals:
                continue
            translated_pattern, _, translated_group_count, _ = printf_pattern(runtime_translation)
            if translated_group_count != group_count:
                raise ValueError("printf placeholder count changed for " + item.get("id", source))
            key = (pattern, runtime_translation)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "pattern": pattern,
                "translation": runtime_translation,
                "literals": useful_literals,
                "literal_length": sum(map(len, literals)),
                "placeholder_count": group_count,
                "type_specificity": type_specificity,
            })

    # Index each rule by a rare three-character literal. The client can look at
    # only rules whose anchor occurs in the current line instead of scanning all
    # 1,900+ translated templates on every message.
    trigram_frequency = {}
    candidates.sort(key=lambda candidate: (-candidate["literal_length"], -candidate["type_specificity"], candidate["placeholder_count"], candidate["pattern"]))
    for candidate in candidates:
        for literal in candidate["literals"]:
            for i in range(len(literal) - 2):
                gram = literal[i:i + 3].casefold()
                trigram_frequency[gram] = trigram_frequency.get(gram, 0) + 1
    rules = []
    for candidate in candidates:
        grams = [
            literal[i:i + 3]
            for literal in candidate["literals"]
            for i in range(len(literal) - 2)
        ]
        sentinel = min(grams, key=lambda gram: trigram_frequency[gram.casefold()])
        rules.append((candidate["pattern"], candidate["translation"], sentinel,
                      candidate["literal_length"], candidate["placeholder_count"], candidate["type_specificity"]))
    return rules


def main():
    parser = argparse.ArgumentParser(description="GnollHack 简体中文分模块汉化注入与提取工具")
    parser.add_argument("--repo", type=str, default=".", help="GnollHack 仓库根目录路径")
    parser.add_argument("--restore", action="store_true", help="还原所有 .bak_en 备份文件")
    parser.add_argument("--extract-untranslated", action="store_true", help="导出 src/*.c 中尚未翻译的动态消息模板")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    patch_root = Path(__file__).resolve().parent.parent

    if args.restore:
        restore_backups(repo_root)
        return

    # 汇总所有 C 词库表
    full_dict = {}
    for c_table in [
        patch_root / "include" / "artilist_zh_cn.h",
        patch_root / "src" / "monst_role_skill_zh_cn.c",
        patch_root / "src" / "objects_zh_cn.c",
        patch_root / "src" / "spells_zh_cn.c",
    ]:
        full_dict.update(parse_c_kv_tables(c_table))

    print(f"[*] 已加载 {len(full_dict)} 条核心词条（职业/种族/技能/全物品/全神器/全法术/怪物/词缀）")

    if args.extract_untranslated:
        extract_untranslated_strings(
            repo_root,
            full_dict,
            repo_root / "tools_zh_CN" / "untranslated_messages_dump.json"
        )
        return

    # Translate display text only; objects/monsters are also compiler lookup keys.
    patch_xaml_files(repo_root, patch_root / "win" / "win32" / "xpl" / "GnollHackX" / "XamlTranslationDict_zh_CN.json")
    patch_xaml_files_at_maui_root(repo_root, patch_root)
    generate_runtime_dictionary(repo_root, full_dict, patch_root)
    print("[DONE] Display localization generated; native identifiers preserved.")



if __name__ == "__main__":
    main()
