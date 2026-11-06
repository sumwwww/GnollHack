#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the imported zh-CN message templates before generating runtime rules."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "native_messages_zh_CN.json"
PRINTF_TOKEN = re.compile(
    r"%(?:%|(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspn])"
)


def visible_tokens(value):
    return [
        match for match in PRINTF_TOKEN.finditer(value)
        if match.group() != "%%" and match.group()[-1] != "n"
    ]


def validate(items):
    errors = []
    ids = set()
    sources = set()
    for item in items:
        item_id = item.get("id", "<missing-id>")
        source = item.get("source", "")
        translation = item.get("translation", "")
        if item_id in ids:
            errors.append(item_id + ": duplicate id")
        ids.add(item_id)
        if source in sources:
            errors.append(item_id + ": duplicate source template")
        sources.add(source)
        if not source or not isinstance(translation, str) or not translation.strip():
            errors.append(item_id + ": empty source or translation")
            continue

        if [m.group() for m in PRINTF_TOKEN.finditer(source)] != [m.group() for m in PRINTF_TOKEN.finditer(translation)]:
            errors.append(item_id + ": printf token sequence differs")
        for escape in (r"\n", r"\t", r"\r", r'\"'):
            if source.count(escape) != translation.count(escape):
                errors.append(item_id + ": C escape count differs: " + escape)

        source_tokens = visible_tokens(source)
        translated_tokens = visible_tokens(translation)
        if len(source_tokens) == len(translated_tokens):
            for index in range(len(source_tokens) - 1):
                source_adjacent = source_tokens[index].end() == source_tokens[index + 1].start()
                translated_adjacent = translated_tokens[index].end() == translated_tokens[index + 1].start()
                if source_adjacent and not translated_adjacent:
                    errors.append(item_id + ": adjacent printf arguments were separated")
                    break

    return errors


def main():
    payload = json.loads(DATA.read_text(encoding="utf-8-sig"))
    items = payload.get("items", [])
    errors = validate(items)
    expected = 1941
    if len(items) != expected:
        errors.append(f"expected {expected} native templates, found {len(items)}")
    print(f"Checked: {len(items)} native templates; errors: {len(errors)}")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
