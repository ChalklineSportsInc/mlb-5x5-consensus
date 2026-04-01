#!/usr/bin/env python3
"""
generate_picks.py  —  v4 design
Generates a dated consensus picks HTML from a Chalkline CSV export.
Also updates the PICKS registry in index.html.

Usage:
    python generate_picks.py <path_to_csv>
"""

import sys
import os
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT  = Path(__file__).parent
PICKS_DIR  = REPO_ROOT / "picks"
INDEX_FILE = REPO_ROOT / "index.html"
PICKS_DIR.mkdir(exist_ok=True)

VERSION = "v4"


# ── Analyse CSV ───────────────────────────────────────────────────────────────
def analyse(csv_path):
    df = pd.read_csv(csv_path)
    dates    = pd.to_datetime(df["created_date"].dropna()).dt.date
    date_obj = dates.value_counts().idxmax()
    date_str = str(date_obj)
    try:
        display = date_obj.strftime("%B %-d, %Y")
    except ValueError:
        display = date_obj.strftime("%B %#d, %Y")

    entries = df["entry_id"].nunique()
    games   = df["event"].nunique()

    results = []
    for event in df["event"].unique():
        sub   = df[df["event"] == event]
        total = len(sub)
        vc    = sub["market"].value_counts()
        team1, team2 = [t.strip() for t in event.split(" vs ")]
        c1 = int(vc.get(team1, 0))
        c2 = int(vc.get(team2, 0))
        results.append(dict(team1=team1, team2=team2, c1=c1, c2=c2, total=total))

    results.sort(key=lambda x: x["total"], reverse=True)
    return date_str, display, entries, games, results


# ── Nav helpers ───────────────────────────────────────────────────────────────
def get_sorted_dates():
    return sorted(f.stem for f in PICKS_DIR.glob("????-??-??.html"))

def fmt_label(d):
    dt = datetime.strptime(d, "%Y-%m-%d")
    try:    return dt.strftime("%b %-d")
    except: return dt.strftime("%b %#d")

def build_nav(date_str, existing_dates):
    all_dates = sorted(existing_dates + [date_str])
    idx       = all_dates.index(date_str)
    prev_date = all_dates[idx - 1] if idx > 0 else None
    next_date = all_dates[idx + 1] if idx < len(all_dates) - 1 else None

    prev_top = f'<a href="{prev_date}.html" class="nav-arrow">&#8592; {fmt_label(prev_date)}</a>' if prev_date else '<div class="nav-placeholder"></div>'
    next_top = f'<a href="{next_date}.html" class="nav-arrow">{fmt_label(next_date)} &#8594;</a>' if next_date else '<div class="nav-placeholder"></div>'
    prev_bot = f'<a href="{prev_date}.html">&#8592; {fmt_label(prev_date)}</a>' if prev_date else '<a class="disabled">&#8592; Prev</a>'
    next_bot = f'<a href="{next_date}.html">{fmt_label(next_date)} &#8594;</a>' if next_date else '<a class="disabled">Next &#8594;</a>'
    return prev_top, next_top, prev_bot, next_bot

def patch_prev_file(existing_dates, new_date):
    if not existing_dates:
        return
    prev_date = existing_dates[-1]
    prev_file = PICKS_DIR / f"{prev_date}.html"
    if not prev_file.exists():
        return
    label    = fmt_label(new_date)
    new_link_top = f'<a href="{new_date}.html" class="nav-arrow">{label} &#8594;</a>'
    new_link_bot = f'<a href="{new_date}.html">{label} &#8594;</a>'
    content  = prev_file.read_text(encoding="utf-8")
    content  = content.replace('<div class="nav-placeholder"></div>\n</nav>', f'{new_link_top}\n</nav>', 1)
    content  = content.replace('<a class="disabled">Next &#8594;</a>', new_link_bot, 1)
    prev_file.write_text(content, encoding="utf-8")
    print(f"  Patched next-link into {prev_date}.html")


# ── JS data ───────────────────────────────────────────────────────────────────
def build_js_data(results):
    return "\n".join(
        f'  {{ team1:"{r["team1"]}", team2:"{r["team2"]}", c1:{r["c1"]}, c2:{r["c2"]}, total:{r["total"]} }},'
        for r in results
    )


# ── Update index registry ─────────────────────────────────────────────────────
def update_index(date_str, entries, games):
    if not INDEX_FILE.exists():
        print("  index.html not found.")
        return
    content = INDEX_FILE.read_text(encoding="utf-8")
    if f'date: "{date_str}"' in content:
        # Update existing entry with fresh counts
        import re
        content = re.sub(
            rf'{{ date: "{date_str}", entries: \d+,\s*games: \d+ }},',
            f'{{ date: "{date_str}", entries: {entries},  games: {games} }},',
            content
        )
        INDEX_FILE.write_text(content, encoding="utf-8")
        print(f"  Updated existing index entry for {date_str}")
        return
    new_line = f'    {{ date: "{date_str}", entries: {entries},  games: {games} }},'
    if "  ];" in content:
        content = content.replace("  ];", f"{new_line}\n  ];", 1)
        INDEX_FILE.write_text(content, encoding="utf-8")
        print(f"  Added {date_str} to index.")


# ── HTML template ─────────────────────────────────────────────────────────────
HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="MLB 5x5 free-to-play consensus picks — see where the crowd is leaning on every moneyline.">
<meta property="og:title" content="MLB 5x5 Consensus Picks — {display}">
<meta property="og:description" content="{entries} entries across {games} games. See where the crowd is leaning on every MLB moneyline.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+CiAgPHRleHQgeT0iMjYiIGZvbnQtc2l6ZT0iMjgiPuKavjwvdGV4dD4KPC9zdmc+">
<title>MLB 5x5 Consensus &middot; {display}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800;900&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --covers-yellow: #FFD200;
    --covers-orange: #FD5000;
    --covers-navy:   #15202B;
    --covers-steel:  #253341;
    --covers-mid:    #2E3F52;
    --covers-dim:    #8899AA;
    --covers-light:  #C8D6E5;
    --white:         #FFFFFF;
    --card-bg:       #1C2B3A;
    --card-border:   #2E3F52;
    --fav-bar:       linear-gradient(90deg, #0066CC, #0099FF);
    --dog-bar:       linear-gradient(90deg, #CC4400, #FF6622);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Barlow', sans-serif;
    background: var(--covers-navy);
    color: var(--white);
    min-height: 100vh;
    background-image:
      radial-gradient(ellipse at 0% 0%, rgba(253,80,0,0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 100% 100%, rgba(255,210,0,0.06) 0%, transparent 50%);
  }}

  /* ── TOP NAV ── */
  .nav-top {{
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(21,32,43,0.95);
    border-bottom: 3px solid var(--covers-yellow);
    padding: 0 24px;
    height: 56px;
    position: sticky; top: 0; z-index: 100;
    backdrop-filter: blur(8px);
  }}
  .nav-placeholder {{ width: 120px; visibility: hidden; }}
  .nav-arrow {{
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700; font-size: 0.85rem; letter-spacing: 0.05em;
    text-transform: uppercase; text-decoration: none;
    color: var(--covers-yellow);
    padding: 8px 16px; border-radius: 4px;
    border: 1px solid rgba(255,210,0,0.3);
    transition: background .15s, border-color .15s;
    white-space: nowrap;
  }}
  .nav-arrow:hover {{ background: rgba(255,210,0,0.1); border-color: var(--covers-yellow); }}
  .nav-center-links {{
    display: flex; gap: 24px; align-items: center;
  }}
  .nav-center-links a {{
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 600; font-size: 0.8rem; letter-spacing: 0.08em;
    text-transform: uppercase; text-decoration: none;
    color: var(--covers-dim);
    transition: color .15s;
  }}
  .nav-center-links a:hover {{ color: var(--white); }}
  .nav-center-links .lboard {{
    color: var(--covers-orange);
    border: 1px solid rgba(253,80,0,0.4);
    padding: 5px 12px; border-radius: 4px;
  }}
  .nav-center-links .lboard:hover {{ color: var(--white); background: rgba(253,80,0,0.15); border-color: var(--covers-orange); }}

  /* ── HERO HEADER ── */
  .inner {{ max-width: 1000px; margin: 0 auto; padding: 0 16px; }}

  .hero {{
    padding: 36px 0 28px;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 28px;
  }}
  .hero-eyebrow {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--covers-orange);
    margin-bottom: 8px;
  }}
  .hero-title {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 3rem; font-weight: 900; line-height: 1;
    letter-spacing: -0.01em; text-transform: uppercase;
    color: var(--white);
  }}
  .hero-title span {{ color: var(--covers-yellow); }}
  .hero-meta {{
    display: flex; gap: 20px; align-items: center;
    margin-top: 16px; flex-wrap: wrap;
  }}
  .hero-stat {{
    display: flex; flex-direction: column;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 10px 20px;
    min-width: 100px;
  }}
  .hero-stat .stat-num {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.8rem; font-weight: 800; line-height: 1;
    color: var(--covers-yellow);
  }}
  .hero-stat .stat-label {{
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--covers-dim);
    margin-top: 2px;
  }}
  .hero-date {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem; font-weight: 600; letter-spacing: 0.05em;
    color: var(--covers-dim);
    text-transform: uppercase;
    margin-left: auto;
  }}

  /* ── FILTER PILLS ── */
  .filter-bar {{
    display: flex; gap: 8px; flex-wrap: wrap;
    align-items: center; margin-bottom: 20px;
  }}
  .filter-label {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--covers-dim);
    margin-right: 4px;
  }}
  .pill-btn {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 6px 16px; border-radius: 4px;
    border: 1px solid var(--card-border);
    background: var(--card-bg); color: var(--covers-dim);
    cursor: pointer; transition: all .15s;
  }}
  .pill-btn:hover {{ border-color: var(--covers-yellow); color: var(--covers-yellow); }}
  .pill-btn.active {{
    background: var(--covers-yellow); border-color: var(--covers-yellow);
    color: var(--covers-navy);
  }}

  /* ── GAME CARDS ── */
  .game-card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color .2s, transform .15s;
    position: relative;
    overflow: hidden;
  }}
  .game-card::before {{
    content: '';
    position: absolute; top: 0; left: 0;
    width: 4px; height: 100%;
    background: var(--card-border);
    transition: background .2s;
  }}
  .game-card:hover {{ border-color: var(--covers-yellow); transform: translateX(2px); }}
  .game-card:hover::before {{ background: var(--covers-yellow); }}
  .game-card.chalk::before {{ background: var(--covers-yellow); }}
  .game-card.close::before {{ background: var(--covers-orange); }}

  .game-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 16px; gap: 12px; flex-wrap: wrap;
  }}
  .matchup {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem; font-weight: 700; letter-spacing: 0.02em;
    text-transform: uppercase; color: var(--white);
    line-height: 1.2;
  }}
  .matchup .vs {{ color: var(--covers-dim); font-weight: 600; margin: 0 6px; }}

  .game-right {{ display: flex; align-items: center; gap: 10px; flex-shrink: 0; }}
  .pick-count {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--covers-dim);
  }}
  .consensus-badge {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.68rem; font-weight: 800; letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 10px; border-radius: 3px;
  }}
  .badge-chalk {{ background: rgba(255,210,0,0.15); color: var(--covers-yellow); border: 1px solid rgba(255,210,0,0.3); }}
  .badge-close  {{ background: rgba(253,80,0,0.15);  color: var(--covers-orange); border: 1px solid rgba(253,80,0,0.3); }}
  .badge-split  {{ background: rgba(0,153,255,0.1);  color: #66CCFF;              border: 1px solid rgba(0,153,255,0.3); }}

  /* ── BARS ── */
  .bar-section {{ display: flex; flex-direction: column; gap: 8px; }}
  .team-row {{ display: flex; align-items: center; gap: 12px; }}
  .team-name {{
    width: 180px; flex-shrink: 0;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.88rem; font-weight: 600; letter-spacing: 0.03em;
    text-transform: uppercase; color: var(--covers-light);
    text-align: right;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .bar-track {{
    flex: 1; height: 32px;
    background: rgba(255,255,255,0.05);
    border-radius: 4px; overflow: hidden;
  }}
  .bar-fill {{
    height: 100%; border-radius: 4px;
    display: flex; align-items: center; justify-content: flex-end;
    padding-right: 10px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.82rem; font-weight: 800; letter-spacing: 0.04em;
    color: var(--white);
    transition: width .7s cubic-bezier(.4,0,.2,1);
    min-width: 2px; position: relative;
  }}
  .bar-fill.favorite {{ background: var(--fav-bar); }}
  .bar-fill.underdog {{ background: var(--dog-bar); }}

  .bar-stats {{
    flex-shrink: 0; min-width: 90px;
    display: flex; align-items: center; gap: 6px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.82rem; font-weight: 700;
    color: var(--covers-light);
  }}
  .bar-pct {{ font-size: 0.95rem; color: var(--white); }}
  .bar-sep {{ color: var(--covers-mid); }}
  .bar-count {{ color: var(--covers-dim); }}

  /* ── BOTTOM NAV ── */
  .nav-bottom {{
    display: flex; gap: 10px; justify-content: center;
    flex-wrap: wrap; padding: 32px 0 48px;
    border-top: 1px solid var(--card-border);
    margin-top: 32px;
  }}
  .nav-bottom a {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.82rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; text-decoration: none;
    color: var(--covers-yellow);
    padding: 10px 20px; border-radius: 4px;
    border: 1px solid rgba(255,210,0,0.3);
    background: var(--card-bg);
    transition: all .15s;
  }}
  .nav-bottom a:hover {{ background: rgba(255,210,0,0.1); border-color: var(--covers-yellow); }}
  .nav-bottom a.disabled {{ opacity: 0.25; pointer-events: none; }}
  .nav-bottom a.lboard {{
    color: var(--covers-orange); border-color: rgba(253,80,0,0.3);
  }}
  .nav-bottom a.lboard:hover {{ background: rgba(253,80,0,0.1); border-color: var(--covers-orange); }}

  /* ── FOOTER ── */
  .site-footer {{
    text-align: center; padding: 0 16px 32px;
    font-size: 0.68rem; color: var(--covers-mid);
    letter-spacing: 0.05em;
  }}

  @media (max-width:640px) {{
    .hero-title {{ font-size: 2rem; }}
    .team-name {{ width: 90px; font-size: .75rem; }}
    .bar-fill {{ font-size: .72rem; }}
    .hero-date {{ margin-left: 0; }}
  }}
</style>
</head>
<body>

<nav class="nav-top">
  {prev_top}
  <div class="nav-center-links">
    <a href="../index.html">&#8962; Home</a>
    <a href="https://freeplay.covers.com/games/mlb-5x5/leaderboard" target="_blank" class="lboard">&#127942; Leaderboard</a>
  </div>
  {next_top}
</nav>

<div class="inner">

  <div class="hero">
    <div class="hero-eyebrow">MLB 5x5 Free-to-Play &mdash; Moneyline</div>
    <div class="hero-title">Consensus <span>Picks</span></div>
    <div class="hero-meta">
      <div class="hero-stat">
        <span class="stat-num">{entries}</span>
        <span class="stat-label">Entries</span>
      </div>
      <div class="hero-stat">
        <span class="stat-num">{games}</span>
        <span class="stat-label">Games</span>
      </div>
      <div class="hero-date">{display}</div>
    </div>
  </div>

  <div class="filter-bar">
    <span class="filter-label">Sort:</span>
    <button class="pill-btn active" onclick="setSort('entries', this)">Most Picked</button>
    <button class="pill-btn" onclick="setSort('consensus', this)">Chalk First</button>
    <button class="pill-btn" onclick="setSort('closest', this)">Closest Split</button>
    <button class="pill-btn" onclick="setSort('alpha', this)">A&ndash;Z</button>
  </div>

  <div id="cards"></div>

  <div class="nav-bottom">
    {prev_bot}
    <a href="../index.html">&#8962; Home</a>
    <a href="https://freeplay.covers.com/games/mlb-5x5/leaderboard" target="_blank" class="lboard">&#127942; Leaderboard</a>
    {next_bot}
  </div>

</div>

<div class="site-footer">
  {version} &nbsp;&middot;&nbsp; Data refreshed {timestamp}
</div>

<script>
const RAW = [
{js_data}
];

let currentSort = 'entries';

function getBadge(p) {{
  if (p >= 85) return ['chalk','Chalk'];
  if (p <= 55) return ['close','Close'];
  return ['split','Contested'];
}}

function setSort(sort, btn) {{
  currentSort = sort;
  document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderCards();
}}

function renderCards() {{
  let data = RAW.map(d => {{
    const p1 = parseFloat((d.c1/d.total*100).toFixed(1));
    const p2 = parseFloat((d.c2/d.total*100).toFixed(1));
    return {{...d, p1, p2, maxPct: Math.max(p1,p2)}};
  }});
  if (currentSort==='entries')   data.sort((a,b)=>b.total-a.total);
  if (currentSort==='consensus') data.sort((a,b)=>b.maxPct-a.maxPct);
  if (currentSort==='closest')   data.sort((a,b)=>a.maxPct-b.maxPct);
  if (currentSort==='alpha')     data.sort((a,b)=>a.team1.localeCompare(b.team1));

  const container = document.getElementById('cards');
  container.innerHTML = '';

  data.forEach((d, i) => {{
    const [bk,bl] = getBadge(d.maxPct);
    const cc1 = d.p1 >= 50 ? 'favorite' : 'underdog';
    const cc2 = d.p2 >= 50 ? 'favorite' : 'underdog';
    const card = document.createElement('div');
    card.className = 'game-card ' + bk;
    card.style.animationDelay = (i * 30) + 'ms';
    card.innerHTML = `
      <div class="game-header">
        <div class="matchup">${{d.team1}}<span class="vs">vs</span>${{d.team2}}<span class="consensus-badge badge-${{bk}}" style="margin-left:10px">${{bl}}</span></div>
        <div class="game-right">
          <span class="pick-count">${{d.total}} picks</span>
        </div>
      </div>
      <div class="bar-section">
        <div class="team-row">
          <div class="team-name" title="${{d.team1}}">${{d.team1}}</div>
          <div class="bar-track">
            <div class="bar-fill ${{cc1}}" style="width:${{d.p1}}%">${{d.p1 >= 10 ? d.p1 + '%' : ''}}</div>
          </div>
          <div class="bar-stats">
            <span class="bar-pct">${{d.p1}}%</span>
            <span class="bar-sep">|</span>
            <span class="bar-count">${{d.c1}}</span>
          </div>
        </div>
        <div class="team-row">
          <div class="team-name" title="${{d.team2}}">${{d.team2}}</div>
          <div class="bar-track">
            <div class="bar-fill ${{cc2}}" style="width:${{d.p2}}%">${{d.p2 >= 10 ? d.p2 + '%' : ''}}</div>
          </div>
          <div class="bar-stats">
            <span class="bar-pct">${{d.p2}}%</span>
            <span class="bar-sep">|</span>
            <span class="bar-count">${{d.c2}}</span>
          </div>
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


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_picks.py <path_to_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Processing: {csv_path}")

    date_str, display, entries, games, results = analyse(csv_path)
    print(f"  Date: {date_str} | Entries: {entries} | Games: {games}")

    now = datetime.now(timezone.utc)
    try:    timestamp = now.strftime("%B %-d, %Y at %-I:%M %p UTC")
    except: timestamp = now.strftime("%B %#d, %Y at %#I:%M %p UTC")

    # Exclude current date so patch_prev_file always targets the genuinely previous file
    existing_dates = [d for d in get_sorted_dates() if d != date_str]
    prev_top, next_top, prev_bot, next_bot = build_nav(date_str, existing_dates)

    html = HTML.format(
        display=display, entries=entries, games=games,
        prev_top=prev_top, next_top=next_top,
        prev_bot=prev_bot, next_bot=next_bot,
        js_data=build_js_data(results),
        timestamp=timestamp,
        version=VERSION,
    )

    out_file = PICKS_DIR / f"{date_str}.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"  Written: {out_file}")

    patch_prev_file(existing_dates, date_str)
    update_index(date_str, entries, games)
    print("Done.")


if __name__ == "__main__":
    main()
