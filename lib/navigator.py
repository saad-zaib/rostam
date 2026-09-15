"""Generate MITRE ATT&CK Navigator layer JSON from execution results."""

import json
import os
from datetime import datetime

_STATUS_COLORS = {
    "success": "#31a354",
    "error": "#e6550d",
    "warning": "#fdae6b",
    "timeout": "#969696",
    "skipped": "#bdbdbd",
    "manual": "#6baed6",
}

_SCORE_MAP = {
    "success": 100,
    "error": 25,
    "warning": 50,
    "timeout": 10,
    "skipped": 5,
    "manual": 15,
}


def generate_layer(chain_name, results, os_platform):
    """
    Build a Navigator layer dict from execution results.

    results: list of dicts, each with:
        technique_id, status, test_name (optional),
        duration_seconds (optional), technique_name (optional)
    """
    techniques = []
    seen = {}

    for r in results:
        tid = r.get("technique_id", "")
        if not tid or r.get("phase") == "cleanup":
            continue

        status = r.get("status", "skipped")
        color = _STATUS_COLORS.get(status, "#bdbdbd")
        score = _SCORE_MAP.get(status, 0)

        test_name = r.get("test_name", r.get("step_name", ""))
        tech_name = r.get("technique_name", "")
        dur = r.get("duration_seconds")
        dur_str = f" ({dur:.1f}s)" if isinstance(dur, (int, float)) else ""
        comment = f"[{status.upper()}] {test_name}{dur_str}"

        if tid in seen:
            existing = seen[tid]
            existing["comment"] += f"\n{comment}"
            if score > existing["score"]:
                existing["score"] = score
                existing["color"] = color
        else:
            entry = {
                "techniqueID": tid,
                "color": color,
                "comment": comment,
                "score": score,
                "enabled": True,
                "showSubtechniques": "." not in tid,
            }
            if tech_name:
                entry["metadata"] = [{"name": "technique_name", "value": tech_name}]
            techniques.append(entry)
            seen[tid] = entry

    layer = {
        "name": f"Rostam — {chain_name}",
        "versions": {
            "attack": "19",
            "navigator": "5.3.2",
            "layer": "4.5",
        },
        "domain": "enterprise-attack",
        "description": f"Kill-chain execution: {chain_name} | Platform: {os_platform} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "filters": {
            "platforms": ["Linux" if os_platform == "linux" else "Windows"],
        },
        "sorting": 3,
        "layout": {
            "layout": "side",
            "aggregateFunction": "average",
            "showID": True,
            "showName": True,
            "showAggregateScores": False,
            "countUnscored": False,
        },
        "hideDisabled": False,
        "techniques": techniques,
        "gradient": {
            "colors": ["#e6550d", "#fdae6b", "#31a354"],
            "minValue": 0,
            "maxValue": 100,
        },
        "legendItems": [
            {"label": "Success", "color": "#31a354"},
            {"label": "Warning", "color": "#fdae6b"},
            {"label": "Error", "color": "#e6550d"},
            {"label": "Timeout", "color": "#969696"},
            {"label": "Skipped", "color": "#bdbdbd"},
            {"label": "Manual", "color": "#6baed6"},
        ],
        "showTacticRowBackground": True,
        "tacticRowBackground": "#205b8f",
        "selectTechniquesAcrossTactics": True,
        "selectSubtechniquesWithParent": False,
        "selectVisibleTechniques": False,
    }

    return layer


def save_layer(base_dir, chain_name, results, os_platform):
    """Generate and save a Navigator layer JSON file. Returns the file path."""
    layer = generate_layer(chain_name, results, os_platform)

    out_dir = os.path.join(base_dir, "layers")
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rostam_{ts}.json"
    path = os.path.join(out_dir, filename)

    with open(path, "w") as f:
        json.dump(layer, f, indent=2)

    return path
