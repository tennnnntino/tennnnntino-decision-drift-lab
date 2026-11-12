"""Route-bound connector simulation. No credentials, I/O or external dispatch."""
from copy import deepcopy

from .policy import check_policy, is_exempt, load_policy

_ROUTES = {"draft": ("prepare-draft", "internal"), "send": ("send-document", "external")}
_FIELDS = ("target", "content", "tenant")
_MAX_TICK = 2**53 - 1


def _binding(route, request):
    if type(route) is not str or route not in _ROUTES or type(request) is not dict:
        return None
    if set(request) != set(_FIELDS) or any(type(request[k]) is not str or not request[k] for k in _FIELDS):
        return None
    return (route, *(request[k] for k in _FIELDS))


def _tick(value):
    return type(value) is int and 0 <= value <= _MAX_TICK


class SimulatedConnector:
    """The adapter supplies route, payload and time. The case supplies only a claim."""

    def __init__(self, policy=None):
        self._policy = deepcopy(load_policy() if policy is None else check_policy(policy))
        self._approvals = {}

    def approve(self, approval_id, route, request, expires_at):
        """Trusted fixture/operator input, separate from the analysed case."""
        binding = _binding(route, request)
        if (type(approval_id) is not str or not approval_id or approval_id in self._approvals
                or binding is None or not _tick(expires_at)):
            raise ValueError("Invalid or duplicate simulated approval")
        self._approvals[approval_id] = (binding, expires_at, "ACTIVE")

    def revoke(self, approval_id):
        binding, expires_at, state = self._approvals[approval_id]
        if state == "ACTIVE":
            self._approvals[approval_id] = (binding, expires_at, "REVOKED")

    def attempt(self, claim, *, route, request, now, approval_id=None):
        binding = _binding(route, request)
        effective = dict(zip(("name", "scope"), _ROUTES[route])) if binding else None
        declared = {k: claim.get(k) if type(claim.get(k)) is str else None for k in ("name", "scope")} if type(claim) is dict else None

        def report(reason=None):
            return {"result": "BLOCK_IN_SIMULATION" if reason else "ALLOW_IN_SIMULATION",
                    "reason": reason, "declared": declared, "effective": effective,
                    "policy_version": self._policy["policy_version"],
                    "authenticated": False, "executed": False}

        if binding is None or not _tick(now):
            return report("INVALID_EXECUTION_CONTEXT")
        if declared != effective:
            return report("DECLARATION_MISMATCH")
        requires_human = claim.get("requires_human", True)
        if type(requires_human) is not bool:
            return report("INVALID_DECLARATION")
        if not requires_human and is_exempt(self._policy, **effective):
            return report()
        approval = self._approvals.get(approval_id) if type(approval_id) is str else None
        if approval is None:
            return report("APPROVAL_MISSING")
        approved_binding, expires_at, state = approval
        if state != "ACTIVE":
            return report("APPROVAL_" + state)
        if now >= expires_at:
            return report("APPROVAL_EXPIRED")
        if approved_binding != binding:
            return report("APPROVAL_BINDING_MISMATCH")
        self._approvals[approval_id] = (approved_binding, expires_at, "CONSUMED")
        return report()
