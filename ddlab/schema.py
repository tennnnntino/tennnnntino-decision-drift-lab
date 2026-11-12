"""Minimal, dependency-free JSON Schema subset validator (V1.4).

Supported keywords are listed in ``SUPPORTED``. Any other keyword makes the
schema itself invalid (``SchemaError``): an unknown constraint is never
silently ignored. docs/schema.mjs implements the same subset and both are
held to contracts/schema-vectors.json.

This is a contract check for synthetic fixtures. It is not a complete
JSON Schema implementation and not a security boundary.
"""
from __future__ import annotations

import re
from typing import Any

ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs", "$comment"}
SUPPORTED = ANNOTATIONS | {"type", "required", "properties", "additionalProperties", "items", "enum", "const",
                           "minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum", "pattern", "$ref"}
_TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
_MAX_REF_DEPTH = 64


class SchemaError(ValueError):
    """The schema uses something this validator does not implement."""


def _is_type(value: Any, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if name == "number":
        return True
    return isinstance(value, int) or value.is_integer()  # JSON Schema: 1.0 is an integer


def strict_equal(a: Any, b: Any) -> bool:
    """JSON equality: booleans never equal numbers; 1 and 1.0 are the same number."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _resolve(root: dict[str, Any], ref: Any) -> dict[str, Any]:
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        raise SchemaError(f"unsupported $ref: {ref!r}")
    target = root.get("$defs", {}).get(ref[len("#/$defs/"):])
    if not isinstance(target, dict):
        raise SchemaError(f"unresolvable $ref: {ref}")
    return target


def _pattern(source: Any) -> re.Pattern[str]:
    # Anchored patterns only, matched with fullmatch: Python's "$" would otherwise accept a trailing newline.
    if not isinstance(source, str) or len(source) < 2 or not source.startswith("^") or not source.endswith("$"):
        raise SchemaError("pattern must be a string anchored with ^ and $")
    try:
        return re.compile(source[1:-1])
    except re.error as exc:
        raise SchemaError(f"invalid pattern: {exc}") from None


def validate(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Return a sorted list of {"path", "keyword"} violations (empty when valid)."""
    errors: list[dict[str, str]] = []
    _check(instance, schema, root if root is not None else schema, "", errors, 0)
    return sorted(errors, key=lambda e: (e["path"], e["keyword"]))


def _check(value: Any, schema: Any, root: dict[str, Any], path: str, errors: list[dict[str, str]], depth: int) -> None:
    if not isinstance(schema, dict):
        raise SchemaError(f"schema at {path or '/'} must be an object")
    unknown = sorted(set(schema) - SUPPORTED)
    if unknown:
        raise SchemaError(f"unsupported schema keyword(s) at {path or '/'}: {', '.join(unknown)}")
    if depth > _MAX_REF_DEPTH:
        raise SchemaError("schema reference depth exceeded")

    def fail(keyword: str) -> None:
        errors.append({"path": path or "/", "keyword": keyword})

    if "$ref" in schema:
        _check(value, _resolve(root, schema["$ref"]), root, path, errors, depth + 1)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not names or any(n not in _TYPES for n in names):
            raise SchemaError(f"unsupported type at {path or '/'}")
        if not any(_is_type(value, n) for n in names):
            fail("type")
            return
    if "enum" in schema and not any(strict_equal(value, option) for option in schema["enum"]):
        fail("enum")
    if "const" in schema and not strict_equal(value, schema["const"]):
        fail("const")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            fail("minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            fail("maxLength")
        if "pattern" in schema and not _pattern(schema["pattern"]).fullmatch(value):
            fail("pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            fail("minimum")
        if "maximum" in schema and value > schema["maximum"]:
            fail("maximum")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            fail("minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            fail("maxItems")
        if "items" in schema:
            for index, child in enumerate(value):
                _check(child, schema["items"], root, f"{path}/{index}", errors, depth + 1)
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append({"path": f"{path}/{name}", "keyword": "required"})
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise SchemaError("properties must be an object")
        for name, child in value.items():
            if name in properties:
                _check(child, properties[name], root, f"{path}/{name}", errors, depth + 1)
            elif "additionalProperties" in schema:
                extra = schema["additionalProperties"]
                if extra is False:
                    errors.append({"path": f"{path}/{name}", "keyword": "additionalProperties"})
                elif extra is not True:
                    _check(child, extra, root, f"{path}/{name}", errors, depth + 1)
