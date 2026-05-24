#!/usr/bin/env python3
"""Generate comprehensive final HTML report from all Qwen results."""
import json, os, sys
from datetime import datetime
from pathlib import Path

def escape(t):
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def load(p):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return []

# Load all results
base = "reports/qwen"
l1_weak = load(f"{base}/results.json")
l1_med = load(f"{base}/layer1_medium/results.json")
l1_strong = load(f"{base}/layer1_strong/results.json")
l2_weak = load(f"{base}/software_results.json")
l2_med = load(f"{base}/layer2_medium/software_results.json")
l2_strong = load(f"{base}/layer2_strong/software_results.json")
refinement = load(f"{base}/refinement/refinement_results.json")
taxonomy = load(f"{base}/gap_taxonomy.json") if os.path.exists(f"{base}/gap_taxonomy.json") else {}
sampling = load(f"{base}/sampling/sampling_results.json")

# Compute stats
def l1_stats(data):
    specs = len(data)
    attacks = sum(r["attacks_attempted"] for r in data)
    gaps = sum(r["gaps_confirmed"] for r in data)
    return specs, attacks, gaps

def l2_stats(data):
    specs = len(data)
    attacks = sum(r["attacks_attempted"] for r in data)
    gaps = sum(r["attacks_adversarial"] for r in data)
    return specs, attacks, gaps

w_s, w_a, w_g = l1_stats(l1_weak)
m_s, m_a, m_g = l1_stats(l1_med)
s_s, s_a, s_g = l1_stats(l1_strong)
sw_s, sw_a, sw_g = l2_stats(l2_weak)
sm_s, sm_a, sm_g = l2_stats(l2_med)
ss_s, ss_a, ss_g = l2_stats(l2_strong)

total_specs = w_s + m_s + s_s + sw_s + sm_s + ss_s
total_attacks = w_a + m_a + s_a + sw_a + sm_a + ss_a
total_gaps = w_g + m_g + s_g + sw_g + sm_g + ss_g

# Refinement stats
ref_converged = sum(1 for r in refinement if r.get("converged"))
ref_total_gaps = sum(r.get("total_gaps_found", 0) for r in refinement)
ref_closed = sum(r.get("total_gaps_closed", 0) for r in refinement)

# Build gap cards HTML
def build_gap_html(g, is_l2=False):
    fix = ""
    sf = g.get("suggested_fix","")
    # Truncate very long fixes
    if sf and len(sf) > 300:
        sf = sf[:300] + "..."
    if sf:
        fix = f'<div class="fix"><div class="fix-label">Suggested Fix:</div><pre><code>{escape(sf)}</code></pre></div>'
    conf = ""
    if is_l2 and g.get("judge_confidence"):
        conf = f" | Confidence: {g['judge_confidence']:.0%}"
    return f'''<div class="gap">
        <div class="gap-header"><span class="strategy-badge">{g.get("strategy","")}</span></div>
        <p><strong>Gap:</strong> {escape(g.get("exploited_gap",""))}</p>
        <p>{escape(g.get("explanation",""))}{conf}</p>
        <details><summary>Adversarial Code</summary><pre><code>{escape(g.get("adversarial_code",""))}</code></pre></details>
        {fix}
    </div>'''

def build_l1_tier(data, tier_name):
    parts = []
    for r in data:
        has_gaps = r["gaps_confirmed"] > 0
        tag = '<span class="tag tag-gap">GAPS</span>' if has_gaps else '<span class="tag tag-ok">OK</span>'
        cc = "has-gaps" if has_gaps else "no-gaps"
        gaps_html = "".join(build_gap_html(g) for g in r["gaps"])
        name = Path(r["spec_file"]).name
        parts.append(f'''<div class="spec-card {cc}">
            <h3>{tag} {name}</h3>
            <p><strong>Intent:</strong> {escape(r["intent"])}</p>
            <p>Attacks: {r["attacks_attempted"]} | Verified: {r.get("attacks_verified",0)} | Gaps: {r["gaps_confirmed"]} | {r["duration_seconds"]:.0f}s</p>
            {gaps_html}
        </div>''')
    return "".join(parts)

def build_l2_tier(data, tier_name):
    parts = []
    for r in data:
        has_gaps = r["attacks_adversarial"] > 0
        tag = '<span class="tag tag-gap">GAPS</span>' if has_gaps else '<span class="tag tag-ok">OK</span>'
        cc = "has-gaps" if has_gaps else "no-gaps"
        gaps_html = "".join(build_gap_html(g, True) for g in r["gaps"])
        parts.append(f'''<div class="spec-card {cc}">
            <h3>{tag} <span class="domain-badge">{r.get("domain","")}</span> {r["spec_name"]}</h3>
            <p><strong>Intent:</strong> {escape(r["intent"][:200])}</p>
            <p>Lang: {r.get("language","")} | Attacks: {r["attacks_attempted"]} | Compliant: {r["attacks_compliant"]} | Adversarial: {r["attacks_adversarial"]} | {r["duration_seconds"]:.0f}s</p>
            {gaps_html}
        </div>''')
    return "".join(parts)

# Refinement section
def build_refinement():
    parts = []
    for r in refinement:
        name = Path(r["spec_file"]).name
        traj = " → ".join(str(x) for x in r.get("gap_trajectory",[]))
        conv = "✓ CONVERGED" if r.get("converged") else "✗ DID NOT CONVERGE"
        color = "#7ee787" if r.get("converged") else "#f85149"

        iters_html = ""
        for it in r.get("iterations",[]):
            fix_text = escape(it.get("fix_applied","")[:200]) if it.get("fix_applied") else "—"
            iters_html += f'<tr><td>{it["iteration"]}</td><td>{it["gaps_found"]}</td><td style="font-size:0.8em">{fix_text}</td><td>{it["duration_seconds"]:.0f}s</td></tr>'

        parts.append(f'''<div class="spec-card" style="border-left:4px solid {color}">
            <h3>{name} — <span style="color:{color}">{conv}</span></h3>
            <p>Intent: {escape(r["intent"])}</p>
            <p>Gap trajectory: <strong>{traj}</strong> | Total gaps: {r["total_gaps_found"]} | Closed: {r["total_gaps_closed"]} | {r["total_duration_seconds"]:.0f}s</p>
            <table style="width:100%;margin-top:0.5em;border-collapse:collapse">
                <tr style="color:#8b949e;text-align:left"><th>Iter</th><th>Gaps</th><th>Fix Applied</th><th>Time</th></tr>
                {iters_html}
            </table>
        </div>''')
    return "".join(parts)

# Taxonomy section
def build_taxonomy():
    if not taxonomy or "categories" not in taxonomy:
        return "<p>No taxonomy data.</p>"
    parts = []
    cats = taxonomy.get("categories", {})
    for cat, info in cats.items():
        sev = info.get("severity","medium")
        sev_color = {"critical":"#f85149","high":"#f0883e","medium":"#d2a8ff","low":"#8b949e"}.get(sev,"#8b949e")
        parts.append(f'''<div class="spec-card" style="border-left:4px solid {sev_color}">
            <h3>{cat.replace("_"," ").title()} <span style="color:{sev_color};font-size:0.8em">({sev.upper()})</span></h3>
            <p>{info.get("description","")}</p>
            <p>Count: {info["count"]} | Specs: {", ".join(Path(s).name for s in info.get("specs_affected",[]))} | Strategies: {", ".join(info.get("strategies_used",[]))}</p>
        </div>''')
    sev_dist = taxonomy.get("severity_distribution",{})
    sev_html = " | ".join(f"{k}: {v}" for k,v in sev_dist.items())
    dom_dist = taxonomy.get("domain_distribution",{})
    dom_html = " | ".join(f"{k}: {v}" for k,v in dom_dist.items())
    return f'''<div class="stats"><div class="stat danger"><div class="stat-value">{taxonomy.get("total_gaps",0)}</div><div class="stat-label">Total Cataloged Gaps</div></div>
        <div class="stat"><div class="stat-value">{len(cats)}</div><div class="stat-label">Gap Categories</div></div></div>
        <p><strong>Severity:</strong> {sev_html}</p>
        <p><strong>Domains:</strong> {dom_html}</p>
        {"".join(parts)}'''

# Build HTML
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SpecSaboteur — Final Results Report</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#c9d1d9;line-height:1.6}}
.container{{max-width:1200px;margin:0 auto;padding:2rem}}
h1{{color:#58a6ff;font-size:2.2rem;margin-bottom:0.3rem}}
h2{{color:#f0883e;font-size:1.5rem;margin:2rem 0 0.5rem;padding-bottom:0.3rem;border-bottom:1px solid #30363d}}
h3{{color:#7ee787;font-size:1rem;margin:0.8rem 0 0.4rem}}
.subtitle{{color:#8b949e;margin-bottom:0.3rem}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.8rem;margin:1.5rem 0}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem;text-align:center}}
.stat-value{{font-size:1.8rem;font-weight:bold;color:#58a6ff}}
.stat-label{{color:#8b949e;font-size:0.8rem}}
.stat.danger .stat-value{{color:#f85149}}
.stat.success .stat-value{{color:#7ee787}}
.stat.warn .stat-value{{color:#f0883e}}
.spec-card{{background:#161b22;border:1px solid #30363d;border-radius:8px;margin:0.8rem 0;padding:1.2rem}}
.spec-card.has-gaps{{border-left:4px solid #f85149}}
.spec-card.no-gaps{{border-left:4px solid #7ee787}}
.gap{{background:#1c1e24;border:1px solid #f8514933;border-radius:6px;margin:0.6rem 0;padding:0.8rem}}
.gap-header{{margin-bottom:0.4rem}}
.strategy-badge{{background:#f0883e22;color:#f0883e;padding:2px 8px;border-radius:4px;font-size:0.8rem}}
.domain-badge{{background:#58a6ff22;color:#58a6ff;padding:2px 8px;border-radius:4px;font-size:0.8rem}}
pre{{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:0.8rem;overflow-x:auto;font-size:0.8rem;margin:0.4rem 0}}
code{{font-family:'Cascadia Code','Fira Code',monospace}}
.fix{{background:#7ee78711;border:1px solid #7ee78733;border-radius:6px;padding:0.6rem;margin-top:0.4rem}}
.fix-label{{color:#7ee787;font-weight:bold;font-size:0.8rem}}
.tag{{display:inline-block;padding:2px 6px;border-radius:3px;font-size:0.75rem;margin-right:4px}}
.tag-gap{{background:#f8514922;color:#f85149}}
.tag-ok{{background:#7ee78722;color:#7ee787}}
details{{margin:0.4rem 0}}
summary{{cursor:pointer;color:#58a6ff;font-size:0.85rem}}
table{{font-size:0.85rem}}
th,td{{padding:0.3rem 0.8rem;text-align:left;border-bottom:1px solid #30363d}}
.gradient-table{{width:100%;margin:1rem 0;border-collapse:collapse}}
.gradient-table th{{color:#8b949e;font-weight:normal;font-size:0.8rem}}
.gradient-table td{{padding:0.5rem 1rem}}
.nav{{display:flex;gap:0.5rem;flex-wrap:wrap;margin:1.5rem 0;position:sticky;top:0;background:#0d1117;padding:0.5rem 0;z-index:10}}
.nav a{{color:#58a6ff;text-decoration:none;padding:0.4rem 0.8rem;border:1px solid #30363d;border-radius:6px;font-size:0.85rem}}
.nav a:hover{{background:#161b22}}
footer{{margin-top:3rem;padding-top:1rem;border-top:1px solid #30363d;color:#8b949e;font-size:0.85rem}}
.hero{{background:linear-gradient(135deg,#161b22,#1c2333);border:1px solid #30363d;border-radius:12px;padding:2rem;margin:1.5rem 0}}
.arch{{font-family:monospace;white-space:pre;font-size:0.75rem;color:#8b949e;overflow-x:auto;background:#0d1117;padding:1rem;border-radius:8px;margin:1rem 0}}
</style>
</head>
<body>
<div class="container">
    <h1>🔍 SpecSaboteur</h1>
    <p class="subtitle" style="font-size:1.1rem;color:#c9d1d9">Specification Adequacy via Adversarial Implementation Synthesis</p>
    <p class="subtitle">Apart Research × Atlas Computing — Secure Program Synthesis Hackathon 2026</p>
    <p class="subtitle">Model: Qwen2.5-Coder-32B (Ollama, L40S GPU) | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>

    <div class="nav">
        <a href="#overview">Overview</a>
        <a href="#gradient">Spec Strength Gradient</a>
        <a href="#l1">Layer 1: Dafny</a>
        <a href="#l2">Layer 2: Software</a>
        <a href="#refinement">Refinement</a>
        <a href="#taxonomy">Gap Taxonomy</a>
        <a href="#arch">Architecture</a>
    </div>

    <div class="hero" id="overview">
        <h2 style="border:none;margin-top:0">Key Insight</h2>
        <p style="font-size:1.1rem;color:#c9d1d9">Formal verification proves an implementation satisfies a spec — but <strong style="color:#f85149">who checks the spec?</strong></p>
        <p style="margin-top:0.5rem">SpecSaboteur generates <em>malicious compliance</em> implementations that formally verify against specs but violate intended behavior. Each verified adversarial impl = concrete spec gap. This is the <strong style="color:#58a6ff">dual of CEGIS</strong> — counterexample-guided <em>specification</em> refinement.</p>
    </div>

    <div class="stats">
        <div class="stat"><div class="stat-value">{total_specs}</div><div class="stat-label">Specs Attacked (All Tiers)</div></div>
        <div class="stat"><div class="stat-value">{total_attacks}</div><div class="stat-label">Total Attacks</div></div>
        <div class="stat danger"><div class="stat-value">{total_gaps}</div><div class="stat-label">Gaps Confirmed</div></div>
        <div class="stat success"><div class="stat-value">{ref_converged}/{len(refinement)}</div><div class="stat-label">Specs Converged (Refinement)</div></div>
        <div class="stat warn"><div class="stat-value">{taxonomy.get("total_gaps",0)}</div><div class="stat-label">Gaps Cataloged (Taxonomy)</div></div>
    </div>

    <!-- SPEC STRENGTH GRADIENT -->
    <h2 id="gradient">📊 Specification Strength Gradient</h2>
    <p>Same 6 algorithms tested with weak → medium → strong specs. Stronger specs → fewer gaps. Validates the approach.</p>

    <h3>Layer 1: Dafny (Formal Verification)</h3>
    <table class="gradient-table">
        <tr><th>Tier</th><th>Specs</th><th>Attacks</th><th>Gaps Found</th><th>Gap Rate</th></tr>
        <tr style="color:#f85149"><td>Weak</td><td>{w_s}</td><td>{w_a}</td><td>{w_g}</td><td><strong>{w_g/w_a*100:.0f}%</strong></td></tr>
        <tr style="color:#f0883e"><td>Medium</td><td>{m_s}</td><td>{m_a}</td><td>{m_g}</td><td><strong>{m_g/m_a*100:.0f}%</strong></td></tr>
        <tr style="color:#7ee787"><td>Strong</td><td>{s_s}</td><td>{s_a}</td><td>{s_g}</td><td><strong>{s_g/s_a*100:.0f}%</strong> *</td></tr>
    </table>
    <p style="color:#8b949e;font-size:0.8rem">* Strong tier gap on 03_max.dfy is a false positive — adversarial impl actually computes correct max. Qwen confused itself.</p>

    <h3>Layer 2: Software Specs (LLM-as-Judge)</h3>
    <table class="gradient-table">
        <tr><th>Tier</th><th>Specs</th><th>Attacks</th><th>Gaps Found</th><th>Gap Rate</th></tr>
        <tr style="color:#f85149"><td>Weak</td><td>{sw_s}</td><td>{sw_a}</td><td>{sw_g}</td><td><strong>{sw_g/sw_a*100:.0f}%</strong></td></tr>
        <tr style="color:#f0883e"><td>Medium</td><td>{sm_s}</td><td>{sm_a}</td><td>{sm_g}</td><td><strong>{sm_g/sm_a*100:.0f}%</strong></td></tr>
        <tr style="color:#7ee787"><td>Strong</td><td>{ss_s}</td><td>{ss_a}</td><td>{ss_g}</td><td><strong>{ss_g/ss_a*100:.0f}%</strong></td></tr>
    </table>

    <!-- LAYER 1 DETAILS -->
    <h2 id="l1">🔒 Layer 1: Dafny Formal Verification</h2>

    <h3>Weak Tier — Deliberately Incomplete Specs</h3>
    {build_l1_tier(l1_weak, "weak")}

    <h3>Medium Tier — Partially Strengthened Specs</h3>
    {build_l1_tier(l1_med, "medium")}

    <h3>Strong Tier — Fully Specified</h3>
    {build_l1_tier(l1_strong, "strong")}

    <!-- LAYER 2 DETAILS -->
    <h2 id="l2">🌐 Layer 2: Software Specification (LLM-as-Judge)</h2>
    <p style="color:#d2a8ff">Uses LLM evaluation instead of formal verification. Weaker guarantees but applies to real software specs (APIs, smart contracts, auth systems, databases).</p>

    <h3>Weak Tier</h3>
    {build_l2_tier(l2_weak, "weak")}

    <h3>Medium Tier</h3>
    {build_l2_tier(l2_med, "medium")}

    <h3>Strong Tier</h3>
    {build_l2_tier(l2_strong, "strong")}

    <!-- REFINEMENT -->
    <h2 id="refinement">🔄 Iterative Refinement: Attack → Fix → Re-attack → Converge</h2>
    <p>The core demo: adversarial feedback strengthens specs until no more gaps can be found.</p>
    <div class="stats">
        <div class="stat success"><div class="stat-value">{ref_converged}/{len(refinement)}</div><div class="stat-label">Converged</div></div>
        <div class="stat danger"><div class="stat-value">{ref_total_gaps}</div><div class="stat-label">Gaps Found</div></div>
        <div class="stat success"><div class="stat-value">{ref_closed}</div><div class="stat-label">Gaps Closed</div></div>
    </div>
    {build_refinement()}

    <!-- TAXONOMY -->
    <h2 id="taxonomy">📋 Gap Taxonomy</h2>
    <p>Categorized gap patterns — useful for spec linting and training data.</p>
    {build_taxonomy()}

    <!-- ARCHITECTURE -->
    <h2 id="arch">🏗️ Architecture</h2>
    <div class="arch">NL Intent + Formal Spec
        │
        ▼
┌──────────────────────┐     ┌─────────────┐
│  Adversarial Impl    │────▶│   Dafny     │
│  Generator (LLM)     │     │   Verifier  │
│  Strategies:         │     └──────┬──────┘
│  - Trivial Satisfy   │           │
│  - Edge Case Exploit │    ┌──────┴──────┐
│  - Security Bypass   │    │ VERIFIED?   │
│  - Vacuous Satisfy   │    ├─YES─────────┤
└──────────────────────┘    │ Behavioral  │
                            │ Test Filter │
                            ├─FAIL────────┤
                            │ CONFIRMED   │
                            │ SPEC GAP    │
                            ├─────────────┤
                            │ Gap Report  │
                            │ + Spec Fix  │
                            └─────────────┘
                                  │
                            ┌─────▼─────┐
                            │ Iterate   │
                            │ until no  │
                            │ gaps found│
                            └───────────┘</div>

    <h2>Limitations</h2>
    <ul style="margin:1rem 0;padding-left:1.5rem">
        <li><strong>False negatives:</strong> LLM may miss spec gaps. Tool finds gaps, doesn't prove absence.</li>
        <li><strong>Dafny-specific:</strong> Layer 1 requires Dafny. Concept generalizes to any spec language with verifier.</li>
        <li><strong>Test oracle is finite:</strong> Behavioral filter confirms adversarial behavior via test cases, not formal proof.</li>
        <li><strong>LLM-as-Judge (L2):</strong> Weaker than formal verification. Subject to LLM judgment errors.</li>
        <li><strong>Strong tier false positive:</strong> Qwen generated correct max impl but labeled it adversarial.</li>
    </ul>

    <footer>
        <p><strong>SpecSaboteur</strong> — Adversarial Specification Validation for Secure Program Synthesis</p>
        <p>Apart Research × Atlas Computing Hackathon 2026 | Model: Qwen2.5-Coder-32B-Instruct (Q4_K_M) via Ollama on NVIDIA L40S</p>
        <p>GitHub: <a href="https://github.com/Raj-Taware/specsaboteur" style="color:#58a6ff">github.com/Raj-Taware/specsaboteur</a></p>
    </footer>
</div>
</body>
</html>'''

os.makedirs("reports/qwen", exist_ok=True)
with open("reports/qwen/final_report.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"[DONE] Final report: reports/qwen/final_report.html")
