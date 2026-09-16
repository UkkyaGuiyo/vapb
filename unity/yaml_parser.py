"""Focused parser for the Unity YAML subset used by prefabs and materials."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass
class UnityYAMLDocument:
    class_id: int
    file_id: int
    data: dict[str, Any]
    raw: str


_HEADER = re.compile(r"^---\s+!u!(\d+)\s+&(\d+)", re.MULTILINE)


def _split_top_level(text: str) -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    quote = None
    for index, char in enumerate(text):
        if quote:
            if char == quote and (index == 0 or text[index - 1] != "\\"):
                quote = None
        elif char in "'\"":
            quote = char
        elif char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
        elif char == "," and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    result.append(text[start:].strip())
    return [part for part in result if part]


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value.startswith("{") and value.endswith("}"):
        parsed: dict[str, Any] = {}
        for part in _split_top_level(value[1:-1]):
            if ":" in part:
                key, item = part.split(":", 1)
                parsed[key.strip()] = parse_scalar(item)
        return parsed
    if value.startswith("[") and value.endswith("]"):
        return [parse_scalar(item) for item in _split_top_level(value[1:-1])]
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1].replace("\\'", "'").replace('\\"', '"')
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", value):
        return float(value)
    return value


def _parse_indented(lines: list[str]) -> Any:
    nonempty = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not nonempty:
        return None
    base_indent = min(len(line) - len(line.lstrip()) for line in nonempty)
    if nonempty[0][base_indent:].startswith("-"):
        values: list[Any] = []
        for line in nonempty:
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            item = stripped[1:].strip()
            if not item:
                values.append(None)
            elif ":" in item and not item.startswith("{"):
                key, value = item.split(":", 1)
                values.append({key.strip(): parse_scalar(value)})
            else:
                values.append(parse_scalar(item))
        return values

    result: dict[str, Any] = {}
    index = 0
    while index < len(nonempty):
        line = nonempty[index]
        indent = len(line) - len(line.lstrip())
        if indent != base_indent or ":" not in line:
            index += 1
            continue
        key, value = line.strip().split(":", 1)
        value = value.strip()
        if value:
            result[key.strip()] = parse_scalar(value)
            index += 1
            continue
        child: list[str] = []
        index += 1
        while index < len(nonempty):
            child_indent = len(nonempty[index]) - len(nonempty[index].lstrip())
            same_indent_list_item = child_indent == base_indent and nonempty[index].lstrip().startswith("-")
            if child_indent < base_indent or (child_indent == base_indent and not same_indent_list_item):
                break
            child.append(nonempty[index])
            index += 1
        result[key.strip()] = _parse_indented(child)
    return result


def _fold_flow_lines(lines: list[str]) -> list[str]:
    """Join wrapped flow maps/lists before parsing indentation-based fields."""
    folded: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        stripped = line.strip()
        value = stripped[2:].lstrip() if stripped.startswith("- ") else stripped
        if not value.startswith(("{", "[")):
            value = value.split(":", 1)[1].lstrip() if ":" in value else ""
        if value.startswith(("{", "[")):
            depth = 0
            quote = None
            escaped = False
            while True:
                for char in value:
                    if quote:
                        if char == quote and not escaped:
                            quote = None
                        escaped = char == "\\" and not escaped
                    elif char in "'\"":
                        quote = char
                        escaped = False
                    elif char in "{[":
                        depth += 1
                    elif char in "}]":
                        depth -= 1
                if depth <= 0 or index >= len(lines):
                    break
                value = lines[index].strip()
                line += " " + value
                index += 1
        folded.append(line)
    return folded


def _parse_document_body(body: str) -> dict[str, Any]:
    lines = _fold_flow_lines(body.splitlines())
    data: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith(("%", "...")):
            index += 1
            continue
        if line[0].isspace() or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = parse_scalar(value)
            index += 1
            continue
        nested: list[str] = []
        index += 1
        while index < len(lines):
            next_line = lines[index]
            if next_line.strip() and not next_line[0].isspace() and ":" in next_line:
                break
            nested.append(next_line)
            index += 1
        data[key] = _parse_indented(nested)
    if len(data) == 1:
        value = next(iter(data.values()))
        if isinstance(value, dict):
            data = value
    return data


def parse_unity_yaml(text: str) -> list[UnityYAMLDocument]:
    matches = list(_HEADER.finditer(text))
    documents: list[UnityYAMLDocument] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end]
        documents.append(UnityYAMLDocument(int(match.group(1)), int(match.group(2)), _parse_document_body(body), body))
    return documents
