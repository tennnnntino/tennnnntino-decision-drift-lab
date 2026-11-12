"""External simulation authorization policy (V1.4.1).

Which declared actions need a simulated human approval is decided here, from a
policy the operator supplies, and never from the case under analysis. A case
may ask for *more* caution than the policy; it cannot ask for less.

The policy is still part of a simulation. It authenticates nobody, and the
approval record it is checked against is an unauthenticated fixture field.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .intake import parse_json_strict
from .schema import validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "contracts" / "authorization-policy.json"
POLICY_SCHEMA_PATH = ROOT / "contracts" / "authorization-policy.schema.json"
MAX_POLICY_BYTES = 65_536
# Keys that look like an attempt to carry a policy inside the analysed data.
POLICY_LIKE_KEYS = frozenset({"policy", "authorization_policy", "exempt_actions", "policy_id", "exempt"})

_default: dict[str, Any] | None = None


class PolicyError(ValueError):
    """The policy file is missing, malformed or self-contradictory."""


def check_policy(policy: Any) -> dict[str, Any]:
    """Validate a policy object against the packaged schema. Fail closed."""
    schema = json.loads(POLICY_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = validate(policy, schema)
    if errors:
        shown = "; ".join(f"{e['path']} [{e['keyword']}]" for e in errors[:5])
        raise PolicyError(f"policy schema violations ({len(errors)}): {shown}")
    pairs = [(e["name"], e["scope"]) for e in policy["exempt_actions"]]
    if len(pairs) != len(set(pairs)):
        raise PolicyError("policy lists the same exempt action twice")
    return policy


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Load the packaged default policy, or an operator-supplied file."""
    global _default
    if path is None and _default is not None:
        return _default
    target = DEFAULT_POLICY_PATH if path is None else path
    with target.open("rb") as stream:
        raw = stream.read(MAX_POLICY_BYTES + 1)
    if len(raw) > MAX_POLICY_BYTES:
        raise PolicyError("policy file exceeds size limit")
    policy = check_policy(parse_json_strict(raw))
    if path is None:
        _default = policy
    return policy


def policy_digest(policy: dict[str, Any]) -> str:
    canonical = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_exempt(policy: dict[str, Any], name: Any, scope: Any) -> bool:
    """Exact string match on both name and scope; anything else is not exempt."""
    if not isinstance(name, str) or not isinstance(scope, str):
        return False
    return any(entry["name"] == name and entry["scope"] == scope for entry in policy["exempt_actions"])
