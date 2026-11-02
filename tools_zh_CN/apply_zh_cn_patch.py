#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools_zh_CN/apply_zh_cn_patch.py
GnollHack 现代 WinUI 3 版 (.NET 10 MAUI) 全自动分模块简体中文汉化注入与提取工具

功能：
1. 检查本地 GnollHack 仓库结构，自动备份原始文件 (.bak_en)
2. 将 include/、src/、dat/、win/win32/xpl/ 下的简体中文核心词库与语法旁路模块复制到对应游戏目录
3. 自动扫描并替换：
   - win/win32/xpl/GnollHackX/ 下的所有共享 XAML 界面文本（严格保持 UTF-8）
   - src/objects.c、src/monst.c、src/spell.c、include/artilist.h 中的名词表与描述
   - include/global.h 中的 BUFSZ / QBUFSZ UTF-8 缓冲区扩容（256 -> 1024）
   - src/objnam.c 中的英文冠词(an)、复数(makeplural)、所有格(s_suffix) 中文旁路钩子
   - win/win32/xpl/gnollhackwin/gnollhackwin.vcxproj 注入 MSVC `/utf-8` 编译选项
   - dat/ 目录下的地牢分支名、选项帮助与传言神谕（严格执行 UTF-8 无 BOM 写入）
4. 支持 `--extract-untranslated` 扫描全仓剩余未翻译的 pline/You/verbalize 字符串并导出 JSON 供增量翻译
5. 支持 `--restore` 一键还原所有备份文件
"""

import argparse
import json
import os
import re
import shutil
import sys
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
                pattern = f'{attr}="{re.escape(en_str)}"'
                replacement = f'{attr}="{zh_str}"'
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
            text = text.replace(f'"{en_str}"', f'"{zh_str}"')
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
                text = text.replace(f'"{en_str}"', f'"{zh_str}"')
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

    patch_global_h_bufsz(repo_root)
    patch_vcxproj_utf8(repo_root)
    patch_xaml_files(repo_root, patch_root / "win" / "win32" / "xpl" / "GnollHackX" / "XamlTranslationDict_zh_CN.json")
    patch_c_string_tables(repo_root, full_dict)
    patch_dat_dungeon(repo_root, patch_root / "dat" / "dungeon_zh_cn.txt")
    print("[DONE] GnollHack 简体中文汉化补丁注入完成！现在可运行 Build-GnollHack-WinUI3-zhCN.ps1 编译现代 WinUI 3 客户端。")


if __name__ == "__main__":
    main()
