# MediaCloud → IRaMuTeQ

A Streamlit application for researchers who want to turn **MediaCloud article records into an IRaMuTeQ-compatible textual corpus** while keeping the relationship between the original records, downloaded articles, and corpus metadata transparent and reproducible.

The application is designed as a browser-based research workflow around the supplied MediaCloud → IRaMuTeQ Python processing logic. It does not require users to edit the source code for ordinary corpus construction.

## What the application does

The workflow is:

**Upload CSV → inspect media → select sources → configure metadata → download/extract articles → build corpus → inspect statistics → download outputs**

For each selected MediaCloud record, the application can:

1. validate and clean the article URL;
2. request the article page;
3. extract the main article text with `trafilatura`;
4. reject articles that do not meet the configured minimum length;
5. clean the extracted text;
6. add IRaMuTeQ metadata to the article header;
7. write the successful article to the corpus;
8. record processing failures in a separate log.

The application also keeps track of duplicate URLs, processing errors, and source classifications.

---

## Input CSV

The uploaded file can have **any filename**. It must be a CSV containing these three required columns:

| Column | Description |
|---|---|
| `media_name` | Publication/media source name |
| `publish_date` | Publication date used to derive year and year-month |
| `url` | Article URL to download and extract |

Additional columns can be used as custom corpus metadata.

The application also handles CSV files that use single quotes as the CSV quoting character, which can occur in exported MediaCloud data.

### Example

```csv
media_name,publish_date,url
example.gr,2026-06-23,https://example.gr/article
another.gr,2026-06-24,https://another.gr/story
```

---

## IRaMuTeQ corpus format

Each successfully extracted article is written as an IRaMuTeQ document beginning with a metadata header such as:

```text
**** *source_examplegr *year_2026 *yearmonth_2026-06 *type_nationalpress *rawnb_123
Article text goes here...
```

The standard metadata fields are:

- **`source`** — cleaned publication/media source name.
- **`year`** — publication year.
- **`yearmonth`** — publication year and month in `YYYY-MM` format.
- **`type`** — the built-in National/Regional/Unclassified source classification when Greek press classification is enabled.
- **`rawnb`** — the original CSV record number, providing traceability back to the input data.

The `rawnb` field is particularly important for reproducibility because it allows the saved corpus records to be related back to their original MediaCloud rows.

---

## Greek and non-Greek corpora

The application supports corpora in languages other than Greek.

### Greek corpus

When **Greek corpus — use National / Regional press classification** is selected, the built-in source lists from the original processing script are used to classify sources as:

- `nationalpress`
- `regionalpress`
- `unclassified`

The classification is specific to the supplied Greek press source lists and should not be interpreted as a universal media classification system.

### Other languages

When **Other language — do not classify as National / Regional press** is selected, the Greek-specific `type` field is not written to the IRaMuTeQ header.

Researchers can then use their own classifications through the Custom metadata feature described below.

---

## Custom metadata and multiple classifications

Additional CSV columns can be selected in the **Custom metadata** section. Each selected column becomes an IRaMuTeQ metadata field, and the value in each row becomes that article's category.

For example, a CSV may contain:

```text
media_name,publish_date,url,mediatype,region,ownership
example.gr,2026-06-23,https://example.gr/article,national,attica,private
```

The resulting header can contain:

```text
**** *source_examplegr *year_2026 *yearmonth_2026-06 *type_nationalpress *rawnb_2 *mediatype_national *region_attica *ownership_private
```

This makes it possible to add variables such as:

- media type;
- geographical region;
- ownership;
- editorial category;
- political orientation;
- language;
- manually coded research groups;
- any other classification represented by a CSV column.

Multiple metadata columns can be selected simultaneously.

### Metadata normalization

The original CSV is **not modified**. For IRaMuTeQ metadata, field names and values are normalized by:

- converting text to lowercase;
- removing accents;
- converting whitespace and punctuation to underscores;
- collapsing repeated underscores;
- using `missing` for empty values;
- adding numeric suffixes when two selected column names would otherwise produce the same metadata field name.

---

## Publication statistics

The application produces **two separate year × media tables**.

### 1. Initial articles in the selected CSV

This table counts the records selected from the input CSV **before URL deduplication and before article extraction**.

The format is:

```text
| year | media_A | media_B | media_C |
|------|---------|---------|---------|
| 2024 | 120     | 85      | 43      |
| 2025 | 150     | 91      | 57      |
| 2026 | 174     | 102     | 64      |
```

### 2. Articles successfully saved

This table counts the articles that were actually written to the generated IRaMuTeQ `.txt` corpus.

The saved counts are reconstructed **from the generated corpus itself**. The application reads the `year` and `rawnb` metadata from each saved IRaMuTeQ header and uses `rawnb` to identify the corresponding original CSV record.

This makes the table a direct representation of what entered the final corpus, rather than an estimate based on requests or attempted downloads.

The saved table has exactly the same structure as the initial table:

```text
| year | media_A | media_B | media_C |
|------|---------|---------|---------|
| 2024 | 98      | 71      | 39      |
| 2025 | 121     | 83      | 51      |
| 2026 | 143     | 94      | 58      |
```

Zeros are retained where a media source has no articles for a particular year, making the two tables directly comparable.

### Interactive comparison

The application provides an interactive year-by-year comparison plot. Select a media source and the plot displays two series:

- **Initial articles**
- **Articles saved**

This allows researchers to inspect extraction success separately for each publication and year rather than combining all media into a single total.

---

## Duplicate URLs and failed extraction

The application removes duplicate URLs before downloading, while preserving the original record information needed for traceability.

A record may therefore appear in the initial statistics but not generate a separate corpus document because:

- its URL is a duplicate;
- the metadata is missing or invalid;
- the URL cannot be requested successfully;
- article text cannot be extracted;
- the extracted text is shorter than the configured minimum;
- another processing error occurs.

These cases are recorded in the failure log whenever applicable.

Consequently, **initial CSV counts and saved corpus counts are expected to differ**. This difference is useful for assessing the effective coverage of the corpus construction process.

---

## Processing settings

The sidebar exposes two important settings.

### Request delay

The application waits between article requests to avoid making requests too rapidly.

- **1.5 seconds** is the default.
- A longer delay (for example 2–5 seconds) is more conservative for large runs.
- A shorter delay may be useful for small tests, subject to the policies and technical limits of the target websites.

### Minimum article length

The default minimum is **100 characters** after extraction and cleaning.

Researchers can increase this threshold when they want to exclude very short or incomplete pages, or lower it for diagnostic testing.

---

## Cancellation and partial runs

Long extraction runs can be cancelled from the interface.

Cancellation is cooperative: if an HTTP request is already in progress, the application allows that request to finish before stopping the run. The partial corpus, statistics, and failure log remain available for inspection and download.

This is useful when testing a new corpus configuration before committing to a complete run.

---

## Outputs

The application provides the following research outputs:

| File | Purpose |
|---|---|
| `news_iramuteq.txt` | IRaMuTeQ-compatible corpus containing successfully extracted articles |
| `publication_counts_initial.csv` | Initial year × media counts from the selected CSV |
| `publication_counts_saved.csv` | Year × media counts for articles actually saved to the corpus |
| `failed_articles.txt` | Detailed log of records that could not be processed successfully |

The comparison plot is displayed interactively in the application rather than being provided as a separate downloadable PNG.

---

## Reproducibility notes

For reproducible research, keep the following together with your downloaded corpus:

1. the original MediaCloud CSV;
2. the generated `news_iramuteq.txt` corpus;
3. the initial and saved statistics CSV files;
4. the failure log;
5. the version of this application used for processing;
6. the processing settings used for the run;
7. any documentation describing custom metadata classifications.

Because article pages can change or disappear over time, a later run against the same URLs may not necessarily produce exactly the same corpus.

---

## Run locally

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
```

### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Windows

```text
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The application will open in your browser.

---

## Deploy with Streamlit Community Cloud

1. Create a GitHub repository.
2. Put `app.py`, `requirements.txt`, and `README.md` in the repository.
3. Open Streamlit Community Cloud.
4. Create a new app from the GitHub repository.
5. Select `app.py` as the main file.
6. Deploy.

The application installs its Python dependencies from `requirements.txt`.

---

## Requirements

The main dependencies are:

- Streamlit
- Requests
- Trafilatura
- Matplotlib
- Plotly

See `requirements.txt` for the version constraints used by the application.

---

## Responsible use

This application performs server-side HTTP requests to third-party article websites. When processing large corpora, researchers should use conservative request rates and respect the terms, access restrictions, and applicable policies of the sites being accessed.

A public deployment should also be treated as a research service rather than an unrestricted bulk-download endpoint. For heavily used deployments, consider authentication, per-run limits, request quotas, job management, and additional server-side resource controls.

---

## Scope of the source classification

The built-in Greek National Press and Regional Press classifications originate from the supplied processing script. They are intentionally preserved rather than silently replaced by an external classification scheme.

Researchers working on other countries, languages, or media systems should use the **Other language** mode and/or their own Custom metadata classifications when appropriate.

---

## Credits

Created by **Panos Tsimpoukis** with the help of **ChatGPT**.

**LERASS (Université de Toulouse) · PhEPoC-ST (NTUA)**

