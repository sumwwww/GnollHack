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
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def strip_bom_and_write_utf8(path: Path, text: str):
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def backup_file(path: Path):
    bak = path.with_suffix(path.suffix + ".bak_en")
    if not bak.exists() and path.exists():
        shutil.copy2(path, bak)


def patch_native_c_messages(repo_root: Path, patch_root: Path):
    """Replace only validated user-facing C messages; preserve compiler lookup tables."""
    location_path = patch_root / "tools_zh_CN" / "zh_cn_c_locations.json"
    runtime_header = patch_root / "include" / "gnh_zh_cn_runtime.h"
    if not location_path.is_file() or not runtime_header.is_file():
        raise FileNotFoundError("Missing verified zh-CN C message map or runtime header")

    entries = json.loads(location_path.read_text(encoding="utf-8-sig")).get("c_locations", [])
    if len(entries) != 2253:
        raise ValueError(f"Expected 2,253 reviewed C message sites, found {len(entries)}")

    by_file = {}
    for entry in entries:
        rel = Path(entry["path"])
        if rel.suffix != ".c" or rel.parts[0] != "src":
            raise ValueError(f"Refusing non-src C translation path: {rel}")
        if rel.as_posix() in {"src/objects.c", "src/monst.c", "src/role.c", "src/skill.c"}:
            raise ValueError(f"Refusing to modify a compiler lookup table: {rel}")
        source = entry["source"]
        translation = entry["translation"]
        # Some valid templates contain only printf substitutions and punctuation
        # (for example "%s%s。"), while diagnostic strings are intentionally
        # unchanged. The content and placeholder checks below still validate them.
        if "\ufffd" in translation or "\n" in translation or "\r" in translation:
            raise ValueError(f"Translation contains an unsafe control character: {rel}:{entry['line']}")
        if PRINTF_TOKEN_RE.findall(source) != PRINTF_TOKEN_RE.findall(translation):
            raise ValueError(f"printf placeholders differ: {rel}:{entry['line']}")
        by_file.setdefault(rel.as_posix(), []).append(entry)

    patched_sites = 0
    for rel, file_entries in by_file.items():
        c_path = repo_root / rel
        if not c_path.is_file():
            raise FileNotFoundError(f"C source file not found: {rel}")
        lines = c_path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
        original = list(lines)
        for entry in file_entries:
            old = '"' + entry["source"] + '"'
            new = '"' + entry["translation"] + '"'
            target = max(0, int(entry["line"]) - 1)
            start = max(0, target - 25)
            end = min(len(lines), target + 26)
            candidates = [i for i in range(start, end) if old in lines[i]]
            if not candidates:
                candidates = [i for i, line in enumerate(lines) if old in line]
            if not candidates:
                raise ValueError(f"Could not match source string at {rel}:{entry['line']}: {entry['source']}")
            # Multiple identical strings can occur in one file; use the nearest source line.
            idx = min(candidates, key=lambda i: abs(i - target))
            lines[idx] = lines[idx].replace(old, new, 1)
            patched_sites += 1
        if lines != original:
            backup_file(c_path)
            strip_bom_and_write_utf8(c_path, "".join(lines))

    if patched_sites != len(entries):
        raise ValueError(f"Applied {patched_sites} of {len(entries)} C message sites")

    header_path = repo_root / "include" / "gnh_zh_cn_runtime.h"
    strip_bom_and_write_utf8(header_path, runtime_header.read_text(encoding="utf-8-sig"))
    patch_pline_format_hook(repo_root)
    patch_utf8_native_build(repo_root)
    print(f"[OK] Applied {patched_sites} validated C message sites across {len(by_file)} source files")


def patch_pline_format_hook(repo_root: Path):
    pline_path = repo_root / "src" / "pline.c"
    text = pline_path.read_text(encoding="utf-8-sig")
    original = text
    include = '#include "../include/gnh_zh_cn_runtime.h"'
    if include not in text:
        needle = '#include "hack.h"'
        if needle not in text:
            raise ValueError('Could not locate #include "hack.h" in src/pline.c')
        text = text.replace(needle, needle + "\n" + include, 1)

    if "gnh_zh_fix_pline_fmt(line," not in text:
        marker = "vpline(const char *line, va_list the_args)\n{"
        start = text.find(marker)
        if start < 0:
            raise ValueError("Could not locate vpline format function in src/pline.c")
        guard = text.find("if (!line || !*line)", start + len(marker))
        if guard < 0:
            raise ValueError("Could not locate vpline empty-message guard in src/pline.c")
        guard_end = text.find(";", guard)
        if guard_end < 0:
            raise ValueError("Could not locate end of vpline empty-message guard")
        hook = (
            "\n\n    char gnh_zh_fmt_buf[1024];\n"
            "    line = gnh_zh_fix_pline_fmt(line, gnh_zh_fmt_buf, sizeof(gnh_zh_fmt_buf));"
        )
        text = text[:guard_end + 1] + hook + text[guard_end + 1:]

    if text != original:
        backup_file(pline_path)
        strip_bom_and_write_utf8(pline_path, text)
    print("[OK] Connected the translated format table to the actual Vsprintf path in pline.c")


def patch_utf8_native_build(repo_root: Path):
    vs_dir = repo_root / "win" / "win32"
    for project in vs_dir.rglob("*.vcxproj"):
        text = project.read_text(encoding="utf-8-sig")
        if "/utf-8" in text.lower():
            continue
        updated = text

        def patch_compile_definitions(group):
            block = group.group(0)
            if "<ClCompile>" not in block:
                return block
            compile_pattern = re.compile(r"<ClCompile>(.*?)(</ClCompile>)", re.DOTALL)

            def patch_compile(compile_group):
                body = compile_group.group(1)
                options = re.search(r"<AdditionalOptions>(.*?)</AdditionalOptions>", body, re.DOTALL)
                if options:
                    value = options.group(1)
                    value = "/utf-8 " + value if value.strip() else "/utf-8 %(AdditionalOptions)"
                    body = body[:options.start(1)] + value + body[options.end(1):]
                else:
                    body = "\n      <AdditionalOptions>/utf-8 %(AdditionalOptions)</AdditionalOptions>" + body
                return "<ClCompile>" + body + compile_group.group(2)

            return compile_pattern.sub(patch_compile, block, count=1)

        updated, groups_patched = re.subn(
            r"<ItemDefinitionGroup\b[^>]*>.*?</ItemDefinitionGroup>",
            patch_compile_definitions,
            updated,
            flags=re.DOTALL,
        )
        if groups_patched == 0:
            continue
        backup_file(project)
        strip_bom_and_write_utf8(project, updated)


def patch_chinese_font_families(repo_root: Path):
    fonts = "Diablo|Immortal|Underwood|ARChristy|LatoRegular|DejaVuSansMonoBold|DejaVuSansMono"
    xaml_re = re.compile(r'(?P<prefix>FontFamily\s*=\s*")(?P<font>' + fonts + r')(?P<suffix>")')
    cs_re = re.compile(r'(?P<prefix>\b(?:[A-Za-z_]\w*\.)*FontFamily\s*=\s*")(?P<font>' + fonts + r')(?P<suffix>")', re.IGNORECASE)
    for project_dir in (
        repo_root / "win" / "win32" / "xpl" / "GnollHackX",
        repo_root / "win" / "win32" / "xpl" / "GnollHackM",
    ):
        if not project_dir.is_dir():
            continue
        for source_path in list(project_dir.rglob("*.xaml")) + list(project_dir.rglob("*.cs")):
            if any(part in ("bin", "obj") for part in source_path.parts):
                continue
            text = source_path.read_text(encoding="utf-8-sig", errors="replace")
            pattern = xaml_re if source_path.suffix.lower() == ".xaml" else cs_re
            updated = pattern.sub(lambda m: m.group("prefix") + "Microsoft YaHei UI" + m.group("suffix"), text)
            if updated != text:
                backup_file(source_path)
                strip_bom_and_write_utf8(source_path, updated)


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
    parser.add_argument("--skip-native-c", action="store_true", help=argparse.SUPPRESS)
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
    if not args.skip_native_c:
        patch_native_c_messages(repo_root, patch_root)
    patch_chinese_font_families(repo_root)
    patch_xaml_files(repo_root, patch_root / "win" / "win32" / "xpl" / "GnollHackX" / "XamlTranslationDict_zh_CN.json")
    patch_xaml_files_at_maui_root(repo_root, patch_root)
    generate_runtime_dictionary(repo_root, full_dict, patch_root)
    print("[DONE] Display localization generated; native identifiers preserved.")



if __name__ == "__main__":
    main()
