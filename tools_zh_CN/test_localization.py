"""Regression checks for compiler-name preservation and display dictionary generation."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PRINTF = re.compile(
    r"%(?:%|(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspn])"
)


class LocalizationTests(unittest.TestCase):
    def test_patch_preserves_engine_names_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for folder in ('tools_zh_CN', 'include', 'src', 'dat', 'win/win32/xpl/GnollHackX', 'win/win32/xpl/GnollHackM'):
                (repo / folder).mkdir(parents=True, exist_ok=True)
            for relative in ('tools_zh_CN/apply_zh_cn_patch.py', 'tools_zh_CN/native_messages_zh_CN.json', 'tools_zh_CN/validate_native_messages.py', 'include/artilist_zh_cn.h', 'src/objects_zh_cn.c', 'src/monst_role_skill_zh_cn.c', 'src/spells_zh_cn.c', 'win/win32/xpl/GnollHackX/XamlTranslationDict_zh_CN.json'):
                shutil.copyfile(ROOT / relative, repo / relative)
            protected = ('src/objects.c', 'src/monst.c', 'src/role.c', 'include/artilist.h', 'include/global.h', 'dat/test.des')
            original = b'/* native lookup names */\n"crystal ball"\n"tentacled one"\n#define BUFSZ 256\n'
            for name in protected:
                (repo / name).write_bytes(original)
            translations = {'Settings? (Advanced)': '设置？（高级）', 'A & B': '甲 & 乙'}
            dictionary = repo / 'win/win32/xpl/GnollHackX/XamlTranslationDict_zh_CN.json'
            dictionary.write_text(json.dumps({'translations': translations, 'attributes_to_translate': ['Text']}, ensure_ascii=False), encoding='utf-8')
            for name in ('GnollHackX', 'GnollHackM'):
                (repo / ('win/win32/xpl/' + name + '/test.xaml')).write_text('<Page><Label Text="Settings? (Advanced)" FontFamily="Diablo"/><Label Text="A &amp; B"/></Page>', encoding='utf-8')
            (repo / 'win/win32/xpl/GnollHackM/Theme.cs').write_text('public class Theme { public string FontFamily = "Immortal"; }', encoding='utf-8')
            command = [sys.executable, str(repo / 'tools_zh_CN/apply_zh_cn_patch.py'), '--repo', str(repo), '--skip-native-c']
            subprocess.run(command, check=True)
            for name in protected:
                self.assertEqual((repo / name).read_bytes(), original, name)
            generated = repo / 'win/win32/xpl/GnollHackM/GnhZhCnDictionary.g.cs'
            first = generated.read_bytes()
            self.assertIn('水晶球', first.decode('utf-8'))
            self.assertIn('MessageRule', first.decode('utf-8'))
            self.assertIn('撞穿了', first.decode('utf-8'))
            for name in ('GnollHackX', 'GnollHackM'):
                tree = ET.parse(repo / ('win/win32/xpl/' + name + '/test.xaml'))
                self.assertEqual([e.attrib['Text'] for e in tree.findall('Label')], list(translations.values()))
                self.assertEqual(tree.find('Label').attrib['FontFamily'], 'Microsoft YaHei UI')
            self.assertIn('FontFamily = "Microsoft YaHei UI"', (repo / 'win/win32/xpl/GnollHackM/Theme.cs').read_text(encoding='utf-8'))
            subprocess.run(command, check=True)
            self.assertEqual(generated.read_bytes(), first)

    def test_imported_messages_preserve_printf_contracts(self):
        command = [sys.executable, str(ROOT / 'tools_zh_CN/validate_native_messages.py')]
        subprocess.run(command, check=True)

    def test_c_message_map_matches_native_sources_and_runtime_hook(self):
        payload = json.loads((ROOT / 'tools_zh_CN/zh_cn_c_locations.json').read_text(encoding='utf-8'))
        entries = payload.get('c_locations', [])
        self.assertEqual(len(entries), 2253)
        source_lines = {}

        def has_unescaped_quote(value):
            backslashes = 0
            for character in value:
                if character == '\\':
                    backslashes += 1
                elif character == '"':
                    if backslashes % 2 == 0:
                        return True
                    backslashes = 0
                else:
                    backslashes = 0
            return False

        for entry in entries:
            relative = Path(entry['path'])
            self.assertEqual(relative.parts[0], 'src')
            self.assertEqual(relative.suffix, '.c')
            self.assertEqual(PRINTF.findall(entry['source']), PRINTF.findall(entry['translation']))
            self.assertNotIn('\ufffd', entry['translation'])
            self.assertFalse(has_unescaped_quote(entry['translation']), f"Unescaped quote: {relative}:{entry['line']}")
            if relative not in source_lines:
                source_lines[relative] = (ROOT / relative).read_text(encoding='utf-8-sig').splitlines()
            lines = source_lines[relative]
            target = max(0, int(entry['line']) - 1)
            self.assertTrue(
                any('"' + entry['source'] + '"' in line for line in lines[max(0, target - 25):target + 26]),
                f"C source site moved or changed: {relative}:{entry['line']}",
            )
        runtime = (ROOT / 'include/gnh_zh_cn_runtime.h').read_text(encoding='utf-8-sig')
        self.assertIn('gnh_zh_fix_pline_fmt', runtime)
        runtime_rows = re.findall(r'^\s*\{ ".*", ".*" \},$', runtime, re.MULTILINE)
        self.assertEqual(len(runtime_rows), 2015)
        self.assertIn('int hi = 2014;', runtime)

    def test_static_content_overlay_preserves_game_data_structure(self):
        command = [
            sys.executable,
            str(ROOT / 'tools_zh_CN/apply_content_zh_cn.py'),
            '--repo', str(ROOT),
            '--check-only',
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        self.assertIn('Validated 15 zh-CN content files; errors: 0', result.stdout)

    def test_static_content_overlay_is_copied_to_build_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            manifest = json.loads((ROOT / 'tools_zh_CN/content_zh_CN/MANIFEST.json').read_text(encoding='utf-8'))
            for relative in manifest['files']:
                source = repo / relative
                translated = repo / 'tools_zh_CN/content_zh_CN' / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                translated.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, source)
                shutil.copyfile(ROOT / 'tools_zh_CN/content_zh_CN' / relative, translated)
            manifest_target = repo / 'tools_zh_CN/content_zh_CN/MANIFEST.json'
            manifest_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'tools_zh_CN/content_zh_CN/MANIFEST.json', manifest_target)
            command = [sys.executable, str(ROOT / 'tools_zh_CN/apply_content_zh_cn.py'), '--repo', str(repo)]
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            for relative in manifest['files']:
                self.assertEqual((repo / relative).read_bytes(), (repo / 'tools_zh_CN/content_zh_CN' / relative).read_bytes(), relative)


if __name__ == '__main__':
    unittest.main()
