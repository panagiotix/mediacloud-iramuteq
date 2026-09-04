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

## Credits

Created by **Panos Tsimpoukis**, **LERASS**, **NTUA**.


### Corpus language and source classification

The application can also be used for corpora in languages other than Greek (for example French). Article text extraction is Unicode-aware and does not require the corpus to be Greek. In the sidebar, select **Other language — do not classify as National / Regional press** to switch off the built-in Greek-specific National/Regional source classification. In this mode, no `*type_...` metadata is written at all. Researchers can instead add their own classifications through Custom metadata.

The uploaded CSV filename does not need to be `mediacloud_articles.csv`; any `.csv` filename is accepted. The required column names are `media_name`, `publish_date`, and `url`.

### Custom metadata and multiple classifications

Researchers can add their own classifications without changing the source code.
In the **Custom metadata** section, select one or more additional columns from
the uploaded CSV. Each selected CSV header becomes an IRaMuTeQ metadata field,
and the value in that row becomes the category for the article.

For example, a CSV containing:

```text
media_name,publish_date,url,mediatype,region,ownership
example.gr,2026-06-23,https://example.gr/article,national,attica,private
```

can produce a header containing:

```text
**** *source_examplegr *year_2026 *yearmonth_2026-06 *type_nationalpress *rawnb_2 *mediatype_national *region_attica *ownership_private
```

This allows researchers to create their own national/regional classification,
regional coding, ownership categories, political-orientation variables, or any
other classification represented by columns in their CSV.

Multiple classifications can be selected simultaneously. The application does
not modify the original CSV values. For IRaMuTeQ compatibility, custom metadata
names and values are normalized to lowercase ASCII-safe tokens: accents are
removed, whitespace and punctuation become underscores, repeated underscores
are collapsed, and empty cells become `missing`. If two selected column headers
normalize to the same metadata name, a numeric suffix is added to keep the
fields unique.

The built-in Greek `type` classification remains independent of custom metadata.
For non-Greek corpora, users can switch off the built-in National/Regional
classification and use their own classification columns instead.
