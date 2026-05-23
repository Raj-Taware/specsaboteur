"""HTML report generator for SpecSaboteur results — supports both layers."""

import json
import os
from datetime import datetime
from pathlib import Path


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpecSaboteur Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        h1 { color: #58a6ff; font-size: 2rem; margin-bottom: 0.5rem; }
        h2 { color: #f0883e; font-size: 1.4rem; margin: 1.5rem 0 0.5rem; }
        h3 { color: #7ee787; font-size: 1.1rem; margin: 1rem 0 0.5rem; }
        .subtitle { color: #8b949e; margin-bottom: 0.5rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
        .stat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.2rem; text-align: center; }
        .stat-value { font-size: 2rem; font-weight: bold; color: #58a6ff; }
        .stat-label { color: #8b949e; font-size: 0.85rem; }
        .stat.danger .stat-value { color: #f85149; }
        .stat.success .stat-value { color: #7ee787; }
        .spec-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin: 1rem 0; padding: 1.5rem; }
        .spec-card.has-gaps { border-left: 4px solid #f85149; }
        .spec-card.no-gaps { border-left: 4px solid #7ee787; }
        .gap { background: #1c1e24; border: 1px solid #f8514933; border-radius: 6px; margin: 0.8rem 0; padding: 1rem; }
        .gap-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .strategy-badge { background: #f0883e22; color: #f0883e; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
        .domain-badge { background: #58a6ff22; color: #58a6ff; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
        pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.85rem; margin: 0.5rem 0; }
        code { font-family: 'Cascadia Code', 'Fira Code', monospace; }
        .fix { background: #7ee78711; border: 1px solid #7ee78733; border-radius: 6px; padding: 0.8rem; margin-top: 0.5rem; }
        .fix-label { color: #7ee787; font-weight: bold; font-size: 0.85rem; }
        .tag { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-right: 4px; }
        .tag-gap { background: #f8514922; color: #f85149; }
        .tag-ok { background: #7ee78722; color: #7ee787; }
        .tag-layer1 { background: #58a6ff22; color: #58a6ff; }
        .tag-layer2 { background: #d2a8ff22; color: #d2a8ff; }
        .layer-note { background: #d2a8ff11; border: 1px solid #d2a8ff33; border-radius: 6px; padding: 1rem; margin: 1rem 0; font-size: 0.9rem; }
        .layer-note strong { color: #d2a8ff; }
        footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #30363d; color: #8b949e; font-size: 0.85rem; }
        .pipeline { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; font-family: monospace; white-space: pre; font-size: 0.8rem; color: #8b949e; overflow-x: auto; }
        .tab-container { display: flex; gap: 0; margin-top: 1.5rem; }
        .tab { padding: 0.8rem 1.5rem; cursor: pointer; border: 1px solid #30363d; border-bottom: none; border-radius: 8px 8px 0 0; background: #0d1117; color: #8b949e; font-weight: bold; }
        .tab.active { background: #161b22; color: #58a6ff; border-color: #58a6ff; }
        .tab-content { display: none; border: 1px solid #30363d; border-radius: 0 8px 8px 8px; padding: 1rem; background: #161b22; }
        .tab-content.active { display: block; }
    </style>
    <script>
    function showTab(tabId) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById('tab-' + tabId).classList.add('active');
        document.getElementById('content-' + tabId).classList.add('active');
    }
    </script>
</head>
<body>
    <div class="container">
        <h1>SpecSaboteur Report</h1>
        <p class="subtitle">Specification Adequacy via Adversarial Implementation Synthesis</p>
        <p class="subtitle">Generated: TIMESTAMP_PLACEHOLDER</p>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">TOTAL_SPECS_PLACEHOLDER</div>
                <div class="stat-label">Specs Attacked</div>
            </div>
            <div class="stat danger">
                <div class="stat-value">TOTAL_GAPS_PLACEHOLDER</div>
                <div class="stat-label">Gaps Found</div>
            </div>
            <div class="stat">
                <div class="stat-value">TOTAL_ATTACKS_PLACEHOLDER</div>
                <div class="stat-label">Attacks Attempted</div>
            </div>
            <div class="stat success">
                <div class="stat-value">SUCCESS_RATE_PLACEHOLDER%</div>
                <div class="stat-label">Gap Detection Rate</div>
            </div>
        </div>

        TABS_PLACEHOLDER

        <footer>
            <p>SpecSaboteur &mdash; Adversarial Specification Validation for Secure Program Synthesis</p>
            <p>Apart Research Hackathon 2026 | Track: Specification Validation</p>
        </footer>
    </div>
</body>
</html>"""


def _escape(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _build_layer1_html(results: list[dict]) -> str:
    """Build HTML for Layer 1 (Dafny) results."""
    parts = []
    for r in results:
        has_gaps = len(r["gaps"]) > 0
        card_class = "has-gaps" if has_gaps else "no-gaps"
        tag = '<span class="tag tag-gap">GAPS FOUND</span>' if has_gaps else '<span class="tag tag-ok">ADEQUATE</span>'

        gaps_html = ""
        for g in r["gaps"]:
            fix_html = ""
            if g.get("suggested_fix"):
                fix_html = f"""
                <div class="fix">
                    <div class="fix-label">Suggested Fix:</div>
                    <pre><code>{_escape(g["suggested_fix"])}</code></pre>
                </div>"""

            gaps_html += f"""
            <div class="gap">
                <div class="gap-header">
                    <h3>Gap: {_escape(g["exploited_gap"])}</h3>
                    <span class="strategy-badge">{g["strategy"]}</span>
                </div>
                <p>{_escape(g["explanation"])}</p>
                <h3>Adversarial Implementation</h3>
                <pre><code>{_escape(g["adversarial_code"])}</code></pre>
                {fix_html}
            </div>"""

        spec_name = Path(r["spec_file"]).name
        verified = r.get("attacks_verified", 0)
        parts.append(f"""
        <div class="spec-card {card_class}">
            <h3>{tag} <span class="tag tag-layer1">DAFNY</span> {spec_name}</h3>
            <p><strong>Intent:</strong> {_escape(r["intent"])}</p>
            <p>Attacks: {r["attacks_attempted"]} | Verified: {verified} | Gaps: {len(r["gaps"])} | Time: {r["duration_seconds"]:.1f}s</p>
            {gaps_html}
        </div>""")

    return "\n".join(parts)


def _build_layer2_html(results: list[dict]) -> str:
    """Build HTML for Layer 2 (software spec) results."""
    parts = []
    parts.append("""
    <div class="layer-note">
        <strong>Layer 2: LLM-as-Judge</strong> &mdash; These results use LLM evaluation instead of
        formal verification. Weaker guarantees than Dafny (Layer 1), but demonstrates the concept
        applied to real software specifications (APIs, smart contracts, auth systems, databases).
    </div>""")

    for r in results:
        has_gaps = len(r["gaps"]) > 0
        card_class = "has-gaps" if has_gaps else "no-gaps"
        tag = '<span class="tag tag-gap">GAPS FOUND</span>' if has_gaps else '<span class="tag tag-ok">ADEQUATE</span>'

        gaps_html = ""
        for g in r["gaps"]:
            fix_html = ""
            if g.get("suggested_fix"):
                fix_html = f"""
                <div class="fix">
                    <div class="fix-label">Suggested Spec Additions:</div>
                    <pre><code>{_escape(g["suggested_fix"])}</code></pre>
                </div>"""

            confidence = g.get("judge_confidence", 0)
            conf_str = f" | Confidence: {confidence:.0%}" if confidence else ""

            gaps_html += f"""
            <div class="gap">
                <div class="gap-header">
                    <h3>Gap: {_escape(g["exploited_gap"])}</h3>
                    <span class="strategy-badge">{g["strategy"]}</span>
                </div>
                <p>{_escape(g["explanation"])}{conf_str}</p>
                <h3>Adversarial Implementation</h3>
                <pre><code>{_escape(g["adversarial_code"])}</code></pre>
                {fix_html}
            </div>"""

        domain = r.get("domain", "unknown")
        language = r.get("language", "")
        parts.append(f"""
        <div class="spec-card {card_class}">
            <h3>{tag} <span class="tag tag-layer2">LLM-JUDGE</span> <span class="domain-badge">{domain}</span> {r["spec_name"]}</h3>
            <p><strong>Intent:</strong> {_escape(r["intent"])}</p>
            <p>Language: {language} | Attacks: {r["attacks_attempted"]} | Compliant: {r.get("attacks_compliant", 0)} | Adversarial: {r.get("attacks_adversarial", 0)} | Gaps: {len(r["gaps"])} | Time: {r["duration_seconds"]:.1f}s</p>
            {gaps_html}
        </div>""")

    return "\n".join(parts)


def generate_unified_report(
    layer1_path: str = None,
    layer2_path: str = None,
    output_path: str = "reports/report.html"
):
    """Generate unified HTML report from both layers."""
    layer1_results = []
    layer2_results = []

    if layer1_path and os.path.exists(layer1_path):
        with open(layer1_path) as f:
            layer1_results = json.load(f)

    if layer2_path and os.path.exists(layer2_path):
        with open(layer2_path) as f:
            layer2_results = json.load(f)

    # Aggregate stats
    total_specs = len(layer1_results) + len(layer2_results)
    total_gaps = (
        sum(len(r["gaps"]) for r in layer1_results) +
        sum(len(r["gaps"]) for r in layer2_results)
    )
    total_attacks = (
        sum(r["attacks_attempted"] for r in layer1_results) +
        sum(r["attacks_attempted"] for r in layer2_results)
    )
    # For rate: use verified (L1) + adversarial (L2)
    total_hits = (
        sum(r.get("attacks_verified", 0) for r in layer1_results) +
        sum(r.get("attacks_adversarial", 0) for r in layer2_results)
    )
    success_rate = f"{total_hits/total_attacks*100:.0f}" if total_attacks > 0 else "0"

    # Build tabs
    has_both = layer1_results and layer2_results
    if has_both:
        tabs_html = """
        <div class="tab-container">
            <div class="tab active" id="tab-layer1" onclick="showTab('layer1')">Layer 1: Dafny (Formal)</div>
            <div class="tab" id="tab-layer2" onclick="showTab('layer2')">Layer 2: Software Specs</div>
        </div>
        <div class="tab-content active" id="content-layer1">
            <h2>Layer 1: Formal Verification Results</h2>
            LAYER1_HTML
        </div>
        <div class="tab-content" id="content-layer2">
            <h2>Layer 2: Software Spec Results</h2>
            LAYER2_HTML
        </div>"""
        tabs_html = tabs_html.replace("LAYER1_HTML", _build_layer1_html(layer1_results))
        tabs_html = tabs_html.replace("LAYER2_HTML", _build_layer2_html(layer2_results))
    elif layer1_results:
        tabs_html = "<h2>Formal Verification Results (Dafny)</h2>\n" + _build_layer1_html(layer1_results)
    elif layer2_results:
        tabs_html = "<h2>Software Spec Results (LLM-as-Judge)</h2>\n" + _build_layer2_html(layer2_results)
    else:
        tabs_html = "<p>No results to display.</p>"

    html = REPORT_TEMPLATE
    html = html.replace("TIMESTAMP_PLACEHOLDER", datetime.now().strftime("%Y-%m-%d %H:%M"))
    html = html.replace("TOTAL_SPECS_PLACEHOLDER", str(total_specs))
    html = html.replace("TOTAL_GAPS_PLACEHOLDER", str(total_gaps))
    html = html.replace("TOTAL_ATTACKS_PLACEHOLDER", str(total_attacks))
    html = html.replace("SUCCESS_RATE_PLACEHOLDER", success_rate)
    html = html.replace("TABS_PLACEHOLDER", tabs_html)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"[Report] Generated: {output_path}")
    return output_path


# Backward compat
def generate_report(results_json_path: str, output_path: str = "reports/report.html"):
    """Generate HTML report from Layer 1 results JSON."""
    return generate_unified_report(layer1_path=results_json_path, output_path=output_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.report [--layer1 results.json] [--layer2 software_results.json] [--output report.html]")
        sys.exit(1)

    # Simple arg parsing
    layer1 = layer2 = None
    output = "reports/report.html"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--layer1" and i + 1 < len(args):
            layer1 = args[i + 1]; i += 2
        elif args[i] == "--layer2" and i + 1 < len(args):
            layer2 = args[i + 1]; i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = args[i + 1]; i += 2
        else:
            # Legacy: first positional arg = layer1
            if not layer1:
                layer1 = args[i]
            i += 1

    generate_unified_report(layer1, layer2, output)
