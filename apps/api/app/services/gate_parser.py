"""Parse VALID-01 gate output into structured gate results."""

import re
from typing import Any

GATE_PATTERN = re.compile(
    r"Gate\s+(\d+)\s+.*?:\s*(PASS|FAIL|PARTIAL)\s*\(Score:\s*(\d+)\)\s*-?\s*Evidence:\s*(.*?)$",
    re.MULTILINE | re.IGNORECASE,
)

CONFIDENCE_PATTERN = re.compile(
    r"Overall\s+Confidence:\s*(\d+)%?",
    re.IGNORECASE,
)

def parse_gates(output: str) -> list[dict[str, Any]]:
    """Parse VALID-01 output into gate results."""
    results = []
    for match in GATE_PATTERN.finditer(output):
        gate_num = int(match.group(1))
        state = match.group(2).lower()
        score = float(match.group(3))
        evidence = match.group(4).strip()
        results.append({
            "gate_number": gate_num,
            "state": state,
            "score": score,
            "evidence": evidence,
        })
    return results

def parse_confidence(output: str) -> float:
    """Extract overall confidence from VALID-01 output."""
    match = CONFIDENCE_PATTERN.search(output)
    return float(match.group(1)) if match else 0.0
