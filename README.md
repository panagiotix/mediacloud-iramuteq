# MediaCloud → IRaMuTeQ

A polished Streamlit research interface for transforming MediaCloud article
records into an IRaMuTeQ-ready corpus.

## Research workflow

**Upload → inspect → select → extract → validate → export**

The application preserves the processing logic of the supplied MediaCloud →
IRaMuTeQ Python script while replacing the command-line interaction with a
browser-based research interface.

### Input

The uploaded CSV must contain:

- `media_name`
- `publish_date`
- `url`

### Outputs

The application produces:

- `news_iramuteq.txt` — IRaMuTeQ corpus
- `publication_counts_by_year.csv` — publication counts by year/source
- `failed_articles.txt` — detailed processing failures

### IRaMuTeQ metadata

Successfully extracted articles receive:

- `source`
- `year`
- `yearmonth`
- `type`
- `rawnb`

`rawnb` preserves the original MediaCloud CSV row number.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate the environment with:

```text
.venv\Scripts\activate
```

## Deploy from GitHub

1. Create a GitHub repository.
2. Upload:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `README.md`
3. Open Streamlit Community Cloud.
4. Create a new app from the repository.
5. Select `app.py` as the main file.
6. Deploy.

## Important operational consideration

This application makes server-side HTTP requests to article URLs. A public
deployment should therefore be used responsibly, especially for large
corpora. The sidebar exposes a request delay and minimum article length.

For a heavily used public service, consider adding authentication, per-run
article limits, request quotas, job queues, and additional server-side
resource controls.

## Scope and reproducibility

The built-in National Press and Regional Press classifications come from the
original supplied script. The application does not silently replace those
lists with an external classification.

Publication statistics are calculated before duplicate URL removal and article
extraction. Consequently, publication statistics and final corpus counts are
expected to differ when records are duplicated or extraction fails.
