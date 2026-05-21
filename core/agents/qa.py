from __future__ import annotations

from typing import Any, Dict, List


def qa_check(script: str, citations: List[Dict[str, Any]], visuals: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    if not script or len(script) < 80:
        issues.append("Script too short or missing")
    if not citations:
        issues.append("No citations/chunk references")
    if not visuals:
        issues.append("No visuals selected")
    return {"grounded": len(issues) == 0, "issues": issues}
