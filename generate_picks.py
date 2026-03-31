#!/usr/bin/env python3
"""
generate_picks.py
Generates a dated consensus picks HTML file from a Chalkline CSV export.
Also updates the PICKS registry in index.html.

Usage:
    python generate_picks.py <path_to_csv>

Output:
    picks/YYYY-MM-DD.html
    index.html (updated registry)
"""

import sys
import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).parent
PICKS_DIR   = REPO_ROOT / "picks"
INDEX_FILE  = REPO_ROOT / "index.html"
PICKS_DIR.mkdir(exist_ok=True)


# ── Load & analyse CSV ────────────────────────────────────────────────────────
def analyse(csv_path: str):
    df = pd.read_csv(csv_path)

    # Derive date from created_date column
    raw_date = df["created_date"].dropna().iloc[0]
    date_obj = datetime.fromisoformat(raw_date).date()
    date_str = str(date_obj)                          # YYYY-MM-DD
    display  = date_obj.strftime("%B %-d, %Y")        # March 31, 2026 (Linux/Mac)
    # Windows fallback:
    try:
        display = date_obj.strftime("%B %-d, %Y")
    except ValueError:
        display = date_obj.strftime("%B %#d, %Y")

    entries  = df["entry_id"].nunique()
    games    = df["event"].nunique()

    results  = []
    for event in df["event"].unique():
        sub   = df[df["event"] == event]
        total = len(sub)
        vc    = sub["market"].value_counts()
        team1, team2 = [t.strip() for t in event.split(" vs ")]
        c1 = int(vc.get(team1, 0))
        c2 = int(vc.get(team2, 0))
        results.append(dict(
            team1=team1, team2=team2,
            c1=c1, c2=c2, total=total,
            pct1=round(c1 / total * 100, 1),
            pct2=round(c2 / total * 100, 1),
        ))

    results.sort(key=lambda x: x["total"], reverse=True)
    return date_str, display, entries, games, results


# ── Nav link helpers ──────────────────────────────────────────────────────────
def get_sorted_dates():
    """Return sorted list of existing YYYY-MM-DD dates in picks/."""
    dates = []
    for f in PICKS_DIR.glob("????-??-??.html"):
        dates.append(f.stem)
    dates.sort()
    return dates


def nav_links(date_str: str, existing_dates: list):
    """
    Return (prev_html, next_html) nav anchor strings.
    existing_dates should NOT yet include date_str when this is called for a new file.
    """
    all_dates = sorted(existing_dates + [date_str])
    idx = all_dates.index(date_str)

    def fmt(d):
        dt = datetime.strptime(d, "%Y-%m-%d")
        return dt.strftime("%b %-d") if os.name != "nt" else dt.strftime("%b %#d")

    prev_html = (
        f'<a href="{all_dates[idx-1]}.html">← {fmt(all_dates[idx-1])}</a>'
        if idx > 0 else '<div class="nav-placeholder"></div>'
    )
    next_html = (
        f'<a href="{all_dates[idx+1]}.html">{fmt(all_dates[idx+1])} →</a>'
        if idx < len(all_dates) - 1 else '<div class="nav-placeholder"></div>'
    )
    return prev_html, next_html


def patch_prev_file(existing_dates: list, new_date: str):
    """Add a → next link to the previously last file now that a new day exists."""
    if not existing_dates:
        return
    prev_date = existing_dates[-1]
    prev_file = PICKS_DIR / f"{prev_date}.html"
    if not prev_file.exists():
        return

    dt = datetime.strptime(new_date, "%Y-%m-%d")
    label = dt.strftime("%b %-d") if os.name != "nt" else dt.strftime("%b %#d")
    new_link = f'<a href="{new_date}.html">{label} →</a>'

    content = prev_file.read_text(encoding="utf-8")
    # Replace the right-side placeholder with the new next link
    content = content.replace(
        '<div class="nav-placeholder"></div>\n</nav>',
        f'{new_link}\n</nav>',
        1  # only replace the last occurrence (right side)
    )
    prev_file.write_text(content, encoding="utf-8")
    print(f"  Patched next-link into {prev_date}.html")


# ── HTML template ─────────────────────────────────────────────────────────────
def build_js_data(results):
    lines = []
    for r in results:
        lines.append(
            f'  {{ team1:"{r["team1"]}", team2:"{r["team2"]}", '
            f'c1:{r["c1"]}, c2:{r["c2"]}, total:{r["total"]} }},'
        )
    return "\n".join(lines)


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Consensus Picks – {display}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #0d1117; color: #e6edf3;
    min-height: 100vh; padding: 0 0 48px;
  }}
  .nav {{
    display: flex; align-items: center; justify-content: space-between;
    background: #161b22; border-bottom: 1px solid #21262d;
    padding: 12px 20px; position: sticky; top: 0; z-index: 100;
  }}
  .nav a {{
    color: #58a6ff; text-decoration: none; font-size: 0.82rem; font-weight: 600;
    padding: 6px 12px; border-radius: 6px; border: 1px solid #30363d;
    background: #0d1117; transition: border-color .2s, background .2s; white-space: nowrap;
  }}
  .nav a:hover {{ border-color: #58a6ff; background: #1c2333; }}
  .nav .nav-center {{
    font-size: 0.82rem; color: #8b949e; text-align: center; flex: 1; padding: 0 12px;
  }}
  .nav-center a {{
    border: none; background: none; color: #8b949e;
    font-size: 0.82rem; font-weight: 400; padding: 0;
  }}
  .nav-center a:hover {{ color: #58a6ff; background: none; border: none; }}
  .nav-placeholder {{ width: 90px; visibility: hidden; }}
  .inner {{ padding: 24px 16px 0; }}
  .header {{ text-align: center; margin-bottom: 32px; }}
  .header h1 {{ font-size: 1.6rem; font-weight: 700; color: #fff; letter-spacing: .5px; }}
  .header .subtitle {{ font-size: .85rem; color: #8b949e; margin-top: 6px; }}
  .header .pill {{
    display: inline-block; background: #1f2937; border: 1px solid #30363d;
    border-radius: 20px; padding: 4px 14px; font-size: .75rem; color: #58a6ff; margin-top: 10px;
  }}
  .sort-bar {{
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 20px; justify-content: flex-end; flex-wrap: wrap;
  }}
  .sort-bar label {{ font-size: .8rem; color: #8b949e; }}
  .sort-bar select {{
    background: #161b22; border: 1px solid #30363d; color: #e6edf3;
    padding: 5px 10px; border-radius: 6px; font-size: .8rem; cursor: pointer;
  }}
  .game-card {{
    background: #161b22; border: 1px solid #21262d; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 14px; transition: border-color .2s;
  }}
  .game-card:hover {{ border-color: #388bfd; }}
  .game-header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 14px; flex-wrap: wrap; gap: 8px;
  }}
  .matchup {{ font-size: .9rem; font-weight: 600; color: #f0f6fc; }}
  .meta {{ font-size: .75rem; color: #8b949e; }}
  .meta span {{
    background: #1f2937; border-radius: 4px; padding: 2px 8px; border: 1px solid #30363d;
  }}
  .bar-section {{ display: flex; flex-direction: column; gap: 10px; }}
  .team-row {{ display: flex; align-items: center; gap: 12px; }}
  .team-name {{
    width: 190px; font-size: .82rem; color: #c9d1d9; text-align: right;
    flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .bar-track {{ flex: 1; height: 30px; background: #0d1117; border-radius: 6px; overflow: hidden; }}
  .bar-fill {{
    height: 100%; border-radius: 6px; display: flex; align-items: center;
    justify-content: flex-end; padding-right: 10px; font-size: .78rem; font-weight: 700;
    color: #fff; transition: width .6s cubic-bezier(.4,0,.2,1); min-width: 2px;
  }}
  .bar-fill.favorite {{ background: linear-gradient(90deg,#1a56db,#3b82f6); }}
  .bar-fill.underdog {{ background: linear-gradient(90deg,#6b3fa0,#a855f7); }}
  .bar-label {{ font-size: .78rem; color: #8b949e; min-width: 60px; flex-shrink: 0; white-space: nowrap; }}
  .consensus-badge {{
    display: inline-block; font-size: .65rem; font-weight: 700; padding: 2px 7px;
    border-radius: 10px; text-transform: uppercase; letter-spacing: .5px;
    margin-left: 8px; vertical-align: middle;
  }}
  .badge-chalk {{ background: #1c4a9c; color: #93c5fd; }}
  .badge-split  {{ background: #1a3a2a; color: #4ade80; }}
  .badge-close  {{ background: #3b2a1a; color: #fb923c; }}
  @media (max-width:600px) {{
    .team-name {{ width: 100px; font-size: .72rem; }}
    .bar-fill  {{ font-size: .68rem; }}
  }}
</style>
</head>
<body>

<nav class="nav">
  {prev_html}
  <div class="nav-center"><a href="../index.html">⌂ Index</a></div>
  {next_html}
</nav>

<div class="inner">
  <div class="header">
    <h1>⚾ Consensus Picks</h1>
    <div class="subtitle">Free-to-Play · Moneyline · {display}</div>
    <div class="pill">{entries} entries · {games} games</div>
  </div>

  <div class="sort-bar">
    <label>Sort by:</label>
    <select id="sortSelect" onchange="renderCards()">
      <option value="entries">Total Entries</option>
      <option value="consensus">Consensus % (highest)</option>
      <option value="closest">Closest Split</option>
      <option value="alpha">Alphabetical</option>
    </select>
  </div>

  <div id="cards"></div>
</div>

<script>
const RAW = [
{js_data}
];

function getBadge(p) {{
  if (p >= 85) return ['chalk','Chalk'];
  if (p <= 55) return ['close','Close'];
  return ['split','Contested'];
}}

function renderCards() {{
  const sort = document.getElementById('sortSelect').value;
  let data = RAW.map(d => {{
    const p1 = parseFloat((d.c1/d.total*100).toFixed(1));
    const p2 = parseFloat((d.c2/d.total*100).toFixed(1));
    return {{...d, p1, p2, maxPct: Math.max(p1,p2)}};
  }});
  if (sort==='entries')   data.sort((a,b)=>b.total-a.total);
  if (sort==='consensus') data.sort((a,b)=>b.maxPct-a.maxPct);
  if (sort==='closest')   data.sort((a,b)=>a.maxPct-b.maxPct);
  if (sort==='alpha')     data.sort((a,b)=>a.team1.localeCompare(b.team1));

  const container = document.getElementById('cards');
  container.innerHTML = '';
  data.forEach(d => {{
    const [bk,bl] = getBadge(d.maxPct);
    const cc1 = d.p1>=50 ? 'favorite' : 'underdog';
    const cc2 = d.p2>=50 ? 'favorite' : 'underdog';
    const card = document.createElement('div');
    card.className = 'game-card';
    card.innerHTML = `
      <div class="game-header">
        <div class="matchup">
          ${{d.team1}} <span style="color:#8b949e;font-weight:400">vs</span> ${{d.team2}}
          <span class="consensus-badge badge-${{bk}}">${{bl}}</span>
        </div>
        <div class="meta"><span>${{d.total}} picks</span></div>
      </div>
      <div class="bar-section">
        <div class="team-row">
          <div class="team-name" title="${{d.team1}}">${{d.team1}}</div>
          <div class="bar-track">
            <div class="bar-fill ${{cc1}}" style="width:${{d.p1}}%">
              ${{d.p1>=12 ? d.p1+'%' : ''}}
            </div>
          </div>
          <div class="bar-label">${{d.p1}}% &nbsp;<span style="color:#555">|</span>&nbsp; ${{d.c1}}</div>
        </div>
        <div class="team-row">
          <div class="team-name" title="${{d.team2}}">${{d.team2}}</div>
          <div class="bar-track">
            <div class="bar-fill ${{cc2}}" style="width:${{d.p2}}%">
              ${{d.p2>=12 ? d.p2+'%' : ''}}
            </div>
          </div>
          <div class="bar-label">${{d.p2}}% &nbsp;<span style="color:#555">|</span>&nbsp; ${{d.c2}}</div>
        </div>
      </div>`;
    container.appendChild(card);
  }});
}}

renderCards();
</script>
</body>
</html>
"""


# ── Update index.html registry ────────────────────────────────────────────────
def update_index(date_str: str, entries: int, games: int):
    if not INDEX_FILE.exists():
        print("  index.html not found, skipping registry update.")
        return

    content = INDEX_FILE.read_text(encoding="utf-8")

    # Check if this date is already in the registry
    if f'date: "{date_str}"' in content:
        print(f"  {date_str} already in index registry, skipping.")
        return

    new_line = f'    {{ date: "{date_str}", entries: {entries},  games: {games} }},'

    # Insert before the closing of the PICKS array
    marker = "  ];"
    if marker in content:
        content = content.replace(marker, f"{new_line}\n  ];", 1)
        INDEX_FILE.write_text(content, encoding="utf-8")
        print(f"  Updated index.html registry with {date_str}")
    else:
        print("  Could not find PICKS array closing marker in index.html.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_picks.py <path_to_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Processing: {csv_path}")

    date_str, display, entries, games, results = analyse(csv_path)
    print(f"  Date: {date_str} | Entries: {entries} | Games: {games}")

    existing_dates = get_sorted_dates()
    prev_html, next_html = nav_links(date_str, existing_dates)

    html = HTML_TEMPLATE.format(
        display=display,
        entries=entries,
        games=games,
        prev_html=prev_html,
        next_html=next_html,
        js_data=build_js_data(results),
    )

    out_file = PICKS_DIR / f"{date_str}.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"  Written: {out_file}")

    # Patch the previous file's next-link
    patch_prev_file(existing_dates, date_str)

    # Update index registry
    update_index(date_str, entries, games)

    print("Done.")


if __name__ == "__main__":
    main()
