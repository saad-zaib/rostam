"""Generate standalone HTML kill-chain execution reports."""

import os
import html
from datetime import datetime

_STATUS_COLORS = {
    "success": "#00c853",
    "error": "#ec0000",
    "warning": "#ff9100",
    "timeout": "#666",
    "skipped": "#555",
    "manual": "#2979ff",
}

_STATUS_BG = {
    "success": "#0a1a0f",
    "error": "#1a0808",
    "warning": "#1a1208",
    "timeout": "#111",
    "skipped": "#111",
    "manual": "#081018",
}


def _esc(text):
    return html.escape(str(text)) if text else ""


def _tactic_name(tid):
    """Extract a simplified tactic category from technique naming patterns."""
    return ""


_TECHNIQUE_CATEGORIES = {
    "T1595": "recon", "T1592": "recon", "T1589": "recon", "T1590": "recon",
    "T1591": "recon", "T1598": "recon", "T1597": "recon", "T1596": "recon",
    "T1593": "recon", "T1594": "recon",
    "T1082": "discovery", "T1083": "discovery", "T1057": "discovery",
    "T1007": "discovery", "T1016": "discovery", "T1049": "discovery",
    "T1018": "discovery", "T1033": "discovery", "T1046": "discovery",
    "T1040": "discovery", "T1135": "discovery", "T1120": "discovery",
    "T1069": "discovery", "T1201": "discovery", "T1518": "discovery",
    "T1003": "credaccess", "T1110": "credaccess", "T1555": "credaccess",
    "T1556": "credaccess", "T1528": "credaccess", "T1558": "credaccess",
    "T1539": "credaccess", "T1552": "credaccess",
    "T1059": "execution", "T1053": "execution", "T1203": "execution",
    "T1047": "execution", "T1106": "execution", "T1129": "execution",
    "T1548": "privesc", "T1134": "privesc", "T1068": "privesc",
    "T1055": "privesc", "T1078": "privesc",
    "T1098": "persistence", "T1136": "persistence", "T1037": "persistence",
    "T1543": "persistence", "T1546": "persistence", "T1547": "persistence",
    "T1574": "persistence", "T1053": "persistence",
    "T1027": "evasion", "T1070": "evasion", "T1036": "evasion",
    "T1014": "evasion", "T1140": "evasion", "T1222": "evasion",
    "T1564": "evasion", "T1562": "evasion",
    "T1021": "lateral", "T1563": "lateral", "T1570": "lateral",
    "T1080": "lateral", "T1550": "lateral",
    "T1560": "collection", "T1005": "collection", "T1074": "collection",
    "T1113": "collection", "T1115": "collection", "T1056": "collection",
    "T1119": "collection",
    "T1041": "exfil", "T1048": "exfil", "T1567": "exfil",
    "T1030": "exfil", "T1020": "exfil", "T1537": "exfil",
    "T1001": "c2", "T1071": "c2", "T1095": "c2", "T1105": "c2",
    "T1572": "c2", "T1573": "c2", "T1090": "c2",
    "T1486": "impact", "T1489": "impact", "T1490": "impact",
    "T1529": "impact", "T1531": "impact", "T1485": "impact",
}


def _build_filename(results):
    """Build filename from unique kill-chain phases in execution order."""
    seen = set()
    parts = []
    for r in results:
        tid = r.get("technique_id", "")
        base = tid.split(".")[0]
        cat = _TECHNIQUE_CATEGORIES.get(base, "")
        if cat and cat not in seen and len(parts) < 4:
            seen.add(cat)
            parts.append(cat)
    if not parts:
        parts = ["chain"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return "_".join(parts) + f"_{ts}"


def generate_html(chain_name, results, os_platform, layer_path=None):
    """Generate a standalone HTML report string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len([r for r in results if r.get("technique_id")])
    counts = {}
    for r in results:
        s = r.get("status", "skipped")
        counts[s] = counts.get(s, 0) + 1

    total_dur = sum(r.get("duration_seconds", 0) or 0 for r in results)

    badges_html = ""
    for status in ("success", "error", "warning", "timeout", "skipped", "manual"):
        c = counts.get(status, 0)
        if c > 0:
            color = _STATUS_COLORS[status]
            badges_html += f'<span class="badge" style="background:{color}">{c} {status}</span>\n'

    cards_html = ""
    for i, r in enumerate(results):
        tid = r.get("technique_id", "")
        if not tid:
            continue
        status = r.get("status", "skipped")
        color = _STATUS_COLORS.get(status, "#bdbdbd")
        bg = _STATUS_BG.get(status, "#fafafa")
        tname = _esc(r.get("technique_name", ""))
        test_name = _esc(r.get("test_name", ""))
        desc = _esc(r.get("description", "")).replace("\n", "<br>")
        dur = r.get("duration_seconds")
        dur_str = f"{dur:.1f}s" if isinstance(dur, (int, float)) else "-"
        output = _esc(r.get("output_preview", ""))

        output_section = ""
        if output.strip():
            output_section = f'''
            <details>
              <summary>Output</summary>
              <pre class="output">{output}</pre>
            </details>'''

        desc_section = ""
        if desc.strip():
            desc_section = f'<p class="desc">{desc}</p>'

        cards_html += f'''
    <div class="card" style="border-left:4px solid {color}; background:{bg}">
      <div class="card-header">
        <span class="step-num">{i + 1}</span>
        <span class="tid">{_esc(tid)}</span>
        <span class="tname">{tname}</span>
        <span class="badge-sm" style="background:{color}">{status.upper()}</span>
        <span class="dur">{dur_str}</span>
      </div>
      <div class="card-body">
        <p class="test-name">{test_name}</p>
        {desc_section}
        {output_section}
      </div>
    </div>'''

    connector = '<div class="connector"></div>'
    cards_with_connectors = connector.join(
        cards_html.split('</div>\n\n    <div class="card"')
    )

    legend_html = ""
    for status, color in _STATUS_COLORS.items():
        legend_html += f'<span class="legend-item"><span class="legend-dot" style="background:{color}"></span>{status}</span>\n'

    layer_link = ""
    if layer_path:
        layer_link = f'<p class="layer-link">Navigator layer: <code>{_esc(layer_path)}</code></p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rostam — {_esc(chain_name)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "Courier New", Consolas, monospace; background: #000; color: #ccc; padding: 2rem; }}
  .container {{ max-width: 920px; margin: 0 auto; }}
  .header {{ background: #0a0a0a; border: 1px solid #ec0000; border-radius: 0; padding: 2rem; margin-bottom: 2rem; }}
  .header h1 {{ color: #ec0000; font-size: 1.6rem; margin-bottom: 0.3rem; letter-spacing: 4px; text-transform: uppercase; }}
  .header h2 {{ color: #2979ff; font-size: 1rem; font-weight: normal; margin-bottom: 1rem; }}
  .meta {{ display: flex; gap: 2rem; color: #777; font-size: 0.85rem; margin-bottom: 1rem; }}
  .badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
  .badge {{ color: #fff; padding: 4px 12px; border-radius: 2px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
  .chain-flow {{ position: relative; padding-left: 20px; border-left: 2px solid #ec0000; }}
  .card {{ background: #0a0a0a; border: 1px solid #1a1a1a; border-radius: 0; margin-bottom: 0; overflow: hidden; }}
  .card-header {{ display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; border-bottom: 1px solid #1a1a1a; }}
  .step-num {{ background: #ec0000; color: #000; width: 26px; height: 26px; border-radius: 0; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }}
  .tid {{ font-family: "Courier New", monospace; color: #2979ff; font-weight: 700; font-size: 0.9rem; }}
  .tname {{ color: #ccc; flex: 1; }}
  .badge-sm {{ color: #000; padding: 2px 8px; border-radius: 0; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
  .dur {{ color: #666; font-size: 0.8rem; font-family: "Courier New", monospace; }}
  .card-body {{ padding: 0.75rem 1rem; }}
  .test-name {{ color: #888; font-size: 0.85rem; margin-bottom: 0.4rem; }}
  .desc {{ color: #666; font-size: 0.8rem; line-height: 1.5; margin-bottom: 0.5rem; }}
  details {{ margin-top: 0.5rem; }}
  summary {{ color: #ec0000; font-size: 0.8rem; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; }}
  .output {{ background: #000; color: #00c853; padding: 0.75rem; border: 1px solid #1a1a1a; border-radius: 0; font-size: 0.75rem; line-height: 1.4; overflow-x: auto; margin-top: 0.5rem; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; }}
  .connector {{ width: 2px; height: 12px; background: #ec0000; margin: 0 auto; }}
  .legend {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 1rem 1.5rem; margin-top: 2rem; display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: #777; text-transform: uppercase; letter-spacing: 1px; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 0; }}
  .layer-link {{ color: #666; font-size: 0.8rem; margin-top: 1rem; }}
  .layer-link code {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 2px 6px; color: #2979ff; }}
  .footer {{ text-align: center; color: #333; font-size: 0.75rem; margin-top: 2rem; letter-spacing: 2px; text-transform: uppercase; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Rostam</h1>
    <h2>{_esc(chain_name)}</h2>
    <div class="meta">
      <span>Platform: {_esc(os_platform.upper())}</span>
      <span>Steps: {total}</span>
      <span>Duration: {total_dur:.1f}s</span>
      <span>{now}</span>
    </div>
    <div class="badges">
      {badges_html}
    </div>
  </div>

  <div class="chain-flow">
    {cards_html}
  </div>

  <div class="legend">
    {legend_html}
  </div>

  {layer_link}

  <p class="footer">Generated by Rostam — ATT&CK Kill-Chain Telemetry Generator</p>
</div>
</body>
</html>'''


def save_report(base_dir, chain_name, results, os_platform, layer_path=None):
    """Generate and save an HTML report. Returns the file path."""
    report_html = generate_html(chain_name, results, os_platform, layer_path)

    out_dir = os.path.join(base_dir, "reports")
    os.makedirs(out_dir, exist_ok=True)

    base_name = _build_filename(results)
    filename = f"{base_name}.html"
    path = os.path.join(out_dir, filename)

    with open(path, "w") as f:
        f.write(report_html)

    return path
