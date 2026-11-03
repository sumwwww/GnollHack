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


def patch_global_h_bufsz(repo_root: Path):
    global_h = repo_root / "include" / "global.h"
    if not global_h.exists():
        print("[SKIP] 未找到 include/global.h")
        return
    backup_file(global_h)
    text = global_h.read_text(encoding="utf-8-sig", errors="replace")
    new_text = re.sub(r"(#define\s+BUFSZ\s+)256\b", r"\g<1>1024 /* Expanded for UTF-8 zh-CN */", text)
    new_text = re.sub(r"(#define\s+QBUFSZ\s+)128\b", r"\g<1>512 /* Expanded for UTF-8 zh-CN */", new_text)
    if new_text != text:
        strip_bom_and_write_utf8(global_h, new_text)
        print("[OK] 已扩容 include/global.h 中的 BUFSZ (1024) 与 QBUFSZ (512)")


def patch_vcxproj_utf8(repo_root: Path):
    vs_dir = repo_root / "win" / "win32"
    if not vs_dir.exists():
        return
    for vcx in vs_dir.rglob("*.vcxproj"):
        text = vcx.read_text(encoding="utf-8-sig", errors="replace")
        if "/utf-8" not in text and "<ClCompile>" in text:
            backup_file(vcx)
            new_text = text.replace(
                "<ClCompile>",
                "<ClCompile>\n      <AdditionalOptions>/utf-8 %(AdditionalOptions)</AdditionalOptions>"
            )
            strip_bom_and_write_utf8(vcx, new_text)
            print(f"[OK] 已为 {vcx.relative_to(repo_root)} 注入 MSVC /utf-8 编译标志")


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


def patch_c_string_tables(repo_root: Path, full_dict: dict):
    targets = [
        repo_root / "include" / "artilist.h",
        repo_root / "src" / "objects.c",
        repo_root / "src" / "monst.c",
        repo_root / "src" / "role.c",
        repo_root / "src" / "skill.c",
    ]
    for target in targets:
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8-sig", errors="replace")
        orig = text
        for en_str, zh_str in full_dict.items():
            # 仅替换双引号完全匹配的字符串字面量，保护 C 宏名与枚举标识符
            text = text.replace(f'"{en_str}"', f'"{escape(zh_str, {chr(34): '&quot;'})}"')
        if text != orig:
            backup_file(target)
            strip_bom_and_write_utf8(target, text)
            print(f"[OK] 已汉化核心引擎数据表: {target.relative_to(repo_root)}")


def patch_dat_dungeon(repo_root: Path, dungeon_txt_path: Path):
    if not dungeon_txt_path.exists():
        return
    mapping = {}
    for line in dungeon_txt_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        en, zh = line.split("|", 1)
        mapping[en.strip()] = zh.strip()

    dat_dir = repo_root / "dat"
    if not dat_dir.exists():
        return
    for f in dat_dir.glob("*"):
        if f.suffix in (".def", ".des", ".txt", ".tru", ".fal") and not f.name.endswith("_zh_cn.txt"):
            text = f.read_text(encoding="utf-8-sig", errors="replace")
            orig = text
            for en_str, zh_str in mapping.items():
                text = text.replace(f'"{en_str}"', f'"{escape(zh_str, {chr(34): '&quot;'})}"')
            if text != orig:
                backup_file(f)
                # 严格以无 BOM UTF-8 写入 dat/ 文件
                strip_bom_and_write_utf8(f, text)


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
    # Indexer initializers tolerate duplicate keys with different casing.
    entries = ["            [" + json.dumps(en, ensure_ascii=False) + "] = " + json.dumps(zh, ensure_ascii=False) + "," for en, zh in sorted(mapping.items())]
    target = repo_root / "win/win32/xpl/GnollHackM/GnhZhCnDictionary.g.cs"
    source = "// Generated by apply_zh_cn_patch.py. Display strings only.\nnamespace GnollHackX { internal static partial class GnhDisplayLocalization {\n    private static readonly System.Collections.Generic.Dictionary<string, string> Words = new System.Collections.Generic.Dictionary<string, string>(System.StringComparer.OrdinalIgnoreCase) {\n" + "\n".join(entries) + "\n    };\n} }\n"
    strip_bom_and_write_utf8(target, source)
    print("[OK] Generated", len(mapping), "display translations")


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
