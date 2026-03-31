# MLB 5x5 Consensus Picks

Automated consensus picks library for the 2026 MLB season.

Live site: https://ChalklineSportsInc.github.io/mlb-5x5-consensus/

---

## Daily workflow

1. Export the contest CSV from Chalkline
2. Rename it anything you like (date in the filename is optional — the script reads the date from the data)
3. Drop it into the `csv/` folder in this repo via GitHub Desktop or the GitHub web UI
4. The GitHub Action runs automatically, generates the picks page, updates the index, and publishes within ~30 seconds

That's it.

---

## Repo structure

```
/
├── index.html              ← Season library landing page (auto-updated)
├── generate_picks.py       ← HTML generation script
├── csv/                    ← Drop daily CSVs here to trigger the action
│   └── .gitkeep
├── picks/                  ← Generated HTML files (auto-created)
│   └── YYYY-MM-DD.html
└── .github/
    └── workflows/
        └── generate-picks.yml
```

---

## One-time setup

1. Clone or download this repo
2. Install [GitHub Desktop](https://desktop.github.com/) for easy drag-and-drop syncing
3. That's all — the GitHub Action runs on GitHub's servers, nothing to install locally

---

## Local testing (optional)

If you want to test the script locally before pushing:

```bash
pip install pandas
python generate_picks.py path/to/your/export.csv
```

This will generate the HTML file in `picks/` and update `index.html` locally.
