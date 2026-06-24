# Media Link Hub

An auto-updating, FMHY-style directory of curated links for four topics:

**🎏 Anime · 🧰 Software · 🤖 AI · 🎬 Movies**

It's a single static page (no build step) backed by a JSON dataset that is
regenerated automatically every day by a GitHub Actions workflow.

## How it works

```
index.html        # UI shell
styles.css        # dark, FMHY-inspired theme
app.js            # tabs, live search, section grouping
data/links.json   # generated dataset (committed by CI)
scripts/update_links.py   # fetches + verifies links
.github/workflows/update.yml  # daily cron: refresh -> verify -> commit -> deploy
```

### Auto-update + verification loop

`scripts/update_links.py` pulls fresh links from the open-source
[FMHY dataset](https://github.com/fmhy/edit) and maps them to the four topics:

| Topic    | Source                                   |
|----------|------------------------------------------|
| AI       | `ai.md`                                  |
| Software | `system-tools.md`, `developer-tools.md`  |
| Anime    | anime sections of `video.md`             |
| Movies   | the rest of `video.md`                   |

After building the dataset it runs a **verification loop**: it checks that every
category is populated, every URL is well-formed, and there are no duplicates.
If any check fails it re-fetches and rebuilds (up to 4 attempts). The data file is
written **only** when it verifies clean, so the published site is never broken.

The GitHub Actions workflow runs the same script daily (and on every push / manual
trigger). If verification fails the workflow fails — nothing broken gets deployed.

## Run locally

```bash
python3 scripts/update_links.py     # regenerate data/links.json
python3 -m http.server 8000         # then open http://localhost:8000
```

## Deployment

Served via **GitHub Pages** from the repository root by the workflow.
Enable Pages once under **Settings → Pages → Source: GitHub Actions**.

---

*Links are aggregated from the public FMHY dataset and point to third-party sites.
This project hosts no content itself; use the links responsibly and at your own discretion.*
