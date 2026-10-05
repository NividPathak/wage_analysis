"""Build the static GitHub Pages site (site/) from results/. Every number is read from JSON.

Usage: python -m causal.site [output_dir]
"""

from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

from causal.oews_io import REPO_ROOT
from causal.report import LABELS, f3, five_numbers, fp, headline_rows, load, summary

FIG_SRC = REPO_ROOT / "results" / "figures"
DEFAULT_OUT = REPO_ROOT / "site"
REPO_URL = "https://github.com/NividPathak/wage_analysis"
TEAM_APP = "https://wageanalysis.streamlit.app"

CSS = """
:root{--bg:#f7f8fa;--surface:#fff;--text:#1b1f24;--muted:#57606a;--border:#d8dee4;
--accent:#0969da;--accent-soft:#ddf4ff;--good:#1a7f37;--warn:#9a6700}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--surface:#161b22;--text:#e6edf3;
--muted:#9198a1;--border:#30363d;--accent:#4493f8;--accent-soft:#12263f;--good:#3fb950;
--warn:#d29922}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:40px 16px 80px}
h1{font-size:clamp(1.6rem,4vw,2.4rem);line-height:1.2;margin:.2em 0 .4em}
h2{font-size:1.35rem;margin:2.4em 0 .6em;padding-top:.6em;border-top:1px solid var(--border)}
.kicker{color:var(--accent);font-weight:600;letter-spacing:.04em;text-transform:uppercase;
font-size:.8rem}
.lede{color:var(--muted);max-width:760px}
a{color:var(--accent)}
.links{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.links a{border:1px solid var(--border);background:var(--surface);padding:6px 12px;
border-radius:8px;text-decoration:none;font-size:.9rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}
.card .label{color:var(--muted);font-size:.85rem}
.card .value{font-size:1.05rem;font-weight:600;margin-top:4px}
.summary{background:var(--accent-soft);border-radius:12px;padding:18px 20px}
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;
background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap}
th{color:var(--muted);font-weight:600}
td.num{font-variant-numeric:tabular-nums;text-align:right}
tr:last-child td{border-bottom:0}
figure{margin:0;background:#fff;border:1px solid var(--border);border-radius:12px;padding:8px}
figure img{width:100%;height:auto;display:block}
figcaption{color:#57606a;font-size:.85rem;padding:6px 4px 0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.tabs button{font:inherit;font-size:.85rem;border:1px solid var(--border);
background:var(--surface);color:var(--text);padding:6px 12px;border-radius:999px;cursor:pointer}
.tabs button[aria-selected=true]{background:var(--accent);border-color:var(--accent);color:#fff}
.panel[hidden]{display:none}
.pill{display:inline-block;font-size:.8rem;padding:2px 8px;border-radius:999px;
border:1px solid var(--border);margin-right:6px}
.pass{color:var(--good)} .fail{color:var(--warn)}
ul.lim li{margin-bottom:6px}
footer{margin-top:60px;color:var(--muted);font-size:.85rem}
"""

JS = """
document.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected','false'));
  b.setAttribute('aria-selected','true');
  document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==b.dataset.target);
}));
"""


def e(text: object) -> str:
    return html.escape(str(text))


def bold_md(text: str) -> str:
    """Escape text and turn **x** into <strong>x</strong>."""
    parts = e(text).split("**")
    return "".join(f"<strong>{p}</strong>" if i % 2 else p for i, p in enumerate(parts))


def table_html(header: list[str], rows: list[list[str]], num_cols: set[int]) -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in header)
    body = "".join(
        "<tr>" + "".join(f"<td class='num'>{e(c)}</td>" if i in num_cols else f"<td>{e(c)}</td>"
                         for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody>" \
           f"</table></div>"


def build(out_dir: Path = DEFAULT_OUT) -> Path:
    """Write index.html and copy figures into out_dir."""
    twfe, es, synth, power = load()
    o = es["outcomes"]
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_out = out_dir / "figures"
    if fig_out.exists():
        shutil.rmtree(fig_out)
    shutil.copytree(FIG_SRC, fig_out)
    (out_dir / ".nojekyll").write_text("")

    cards = "".join(f"<div class='card'><div class='label'>{e(k)}</div>"
                    f"<div class='value'>{e(v)}</div></div>"
                    for k, v in five_numbers(twfe, es, synth, power))

    head_rows = [[LABELS.get(r["outcome"], r["outcome"]), r["method"], f3(r["estimate"]),
                  f"[{f3(r['ci_low'])}, {f3(r['ci_high'])}]" if r["ci_low"] is not None
                  else "permutation test", fp(r["p_value"]), str(r["n"])]
                 for r in headline_rows(twfe, es, synth)]
    headline = table_html(["Outcome", "Method", "Estimate", "95% CI", "p-value", "N"],
                          head_rows, {2, 4, 5})

    tabs, panels = [], []
    for i, y in enumerate(LABELS):
        tw = o[y]["twfe_event_study"]["pretrend"]["p_value"]
        cs = o[y]["callaway_santanna"]["pretrend"]["p_value"]
        tabs.append(f"<button role='tab' data-target='es-{y}' aria-selected="
                    f"'{'true' if i == 0 else 'false'}'>{e(LABELS[y])}</button>")
        cls = lambda p: "pass" if p >= 0.05 else "fail"  # noqa: E731
        panels.append(
            f"<div class='panel' id='es-{y}' {'' if i == 0 else 'hidden'}>"
            f"<p><span class='pill {cls(tw)}'>TWFE pre-trend p {fp(tw)}</span>"
            f"<span class='pill {cls(cs)}'>CS pre-trend p {fp(cs)}</span></p>"
            f"<figure><img src='figures/{e(o[y]['figure'])}' alt='Event study for {e(y)}' "
            f"loading='lazy'><figcaption>Grey: TWFE event study (endpoints binned). Blue: "
            f"Callaway and Sant'Anna. Event time 0 is the first year of the large increase."
            f"</figcaption></figure></div>")

    robust = table_html(
        ["Outcome", "Specification", "Estimate", "95% CI", "p-value", "N"],
        [[r["outcome"], r["spec"], f3(r["estimate"]), f"[{f3(r['ci_low'])}, {f3(r['ci_high'])}]",
          fp(r["p_value"]), str(r["n"])] for r in twfe], {2, 4, 5})
    es_rob = table_html(
        ["Outcome", "Binary static TWFE", "CS overall ATT", "CS pre-COVID (through 2019)"],
        [[y, f"{f3(o[y]['binary_twfe']['estimate'])} (p {fp(o[y]['binary_twfe']['p_value'])})",
          f"{f3(o[y]['callaway_santanna']['overall_att']['estimate'])} "
          f"(p {fp(o[y]['callaway_santanna']['overall_att']['p_value'])})",
          f"{f3(o[y]['cs_pre_covid']['estimate'])} (p {fp(o[y]['cs_pre_covid']['p_value'])})"]
         for y in LABELS], set())

    weights = ", ".join(f"{k} {v:.2f}" for k, v in sorted(synth["weights"].items(),
                                                          key=lambda kv: -kv[1]) if v >= 0.01)
    power_tbl = table_html(
        ["Outcome", "False positive rate (delta = 0)", "MDE at 80% power"],
        [[y, f"{r['false_positive_rate']:.3f}", f3(r["mde_80"])]
         for y, r in power["outcomes"].items()], {1, 2})
    placebo_tbl = table_html(
        ["Method", "Estimate", "95% CI", "p-value"],
        [[r["method"], f3(r["estimate"]), f"[{f3(r['ci_low'])}, {f3(r['ci_high'])}]",
          fp(r["p_value"])] for r in power["placebo_outcome"]["estimates"]], {1, 3})

    results_md = (REPO_ROOT / "RESULTS.md").read_text()
    lims = results_md.split("## Limitations")[1].split("## Plain-English")[0]
    lim_items = "".join(f"<li>{bold_md(line[2:])}</li>" for line in lims.splitlines()
                        if line.startswith("- "))

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Minimum Wage Causal Study</title>
<meta name="description" content="Causal analysis of state minimum wage increases on low-end
wages and food-service employment, using BLS OEWS data, difference-in-differences, event studies,
synthetic control, and power analysis.">
<style>{CSS}</style></head>
<body><main>
<div class="kicker">Causal inference · BLS OEWS · 2005 to 2022</div>
<h1>Did state minimum wage increases raise low-end wages and cut food-service jobs?</h1>
<p class="lede">A state x year panel of BLS occupational wage data joined to historical minimum
wages. {es['sample']['treated_states']} states with a large increase from 2011 on are compared with
{es['sample']['never_treated_states']} states that stayed at the federal $7.25, using two-way fixed
effects, Callaway and Sant'Anna event studies, a synthetic control, and a simulation power
analysis. Extension by Nivid Pathak of a Group 7 team project (CU Boulder).</p>
<div class="links"><a href="{REPO_URL}">Code on GitHub</a>
<a href="{REPO_URL}/blob/main/RESULTS.md">Full results</a>
<a href="{REPO_URL}/blob/main/docs/METHODS.md">Methods</a>
<a href="{REPO_URL}/blob/main/docs/DECISIONS.md">Decisions log</a>
<a href="{TEAM_APP}">Original team app</a></div>

<h2>Headline numbers</h2>
<div class="cards">{cards}</div>

<h2>Summary</h2>
<div class="summary">{e(summary(twfe, es, synth, power))}</div>

<h2>Headline table</h2>
<p class="lede">Estimates in log points. TWFE rows are elasticities with respect to the log
effective minimum wage; CS rows are average effects of a large increase.</p>
{headline}

<h2>Event studies</h2>
<div class="tabs" role="tablist">{''.join(tabs)}</div>
{''.join(panels)}

<h2>Synthetic control: {e(synth['case_state'])} ({synth['treatment_year']})</h2>
<p class="lede">First large increase +${synth['jump_usd']:.2f} ({100 * synth['jump_pct']:.1f}%).
Donor weights: {e(weights)}. Post/pre RMSPE ratio {synth['rmspe_ratio']:.2f}, rank
{synth['rank']} of {synth['n_units']}, permutation p {fp(synth['permutation_p_value'])}.</p>
<div class="grid2">
<figure><img src="figures/synth_paths.png" alt="Treated vs synthetic path" loading="lazy">
<figcaption>Actual vs synthetic 10th percentile wage.</figcaption></figure>
<figure><img src="figures/synth_placebo_gaps.png" alt="Placebo gaps" loading="lazy">
<figcaption>Treated gap against never-treated placebo gaps.</figcaption></figure></div>

<h2>Power</h2>
{power_tbl}
<p></p>
<figure><img src="figures/power_curves.png" alt="Power curves" loading="lazy"></figure>

<h2>Placebo outcome: computer and math wages</h2>
{placebo_tbl}

<h2>Robustness</h2>
{robust}
<p></p>
{es_rob}

<h2>Context</h2>
<div class="grid2">
<figure><img src="figures/mw_2005_vs_2022.png" alt="Minimum wage by state" loading="lazy">
</figure>
<figure><img src="figures/p10_by_group.png" alt="Low-end wages by group" loading="lazy">
</figure></div>

<h2>Limitations</h2>
<ul class="lim">{lim_items}</ul>

<footer>Generated by <code>python -m causal.site</code> from <code>results/*.json</code>. Data:
BLS OEWS; Vaghul and Zipperer (2022) historical minimum wages v1.4.0. Team: Soorej S Nair,
Anjana Anand, Nivid Pathak, Karan Cheemalapati.</footer>
</main><script>{JS}</script></body></html>
"""
    (out_dir / "index.html").write_text(page)
    return out_dir / "index.html"


if __name__ == "__main__":
    path = build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
    print(f"wrote {path}")
