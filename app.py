##Created by Panos Tsimpoukis with ChatGPT / September 2026##
#!/usr/bin/env python3

import csv
import re
import time

from collections import defaultdict
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import requests
import trafilatura


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "mediacloud_articles.csv"

OUTPUT_FILE = "news_iramuteq.txt"

FAILED_FILE = "failed_articles.txt"

STATS_FILE = "publication_counts_by_year.csv"

DELAY = 1.5

MIN_ARTICLE_LENGTH = 100


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
}


# ============================================================
# NATIONAL PRESS
# ============================================================

NATIONAL_PRESS = {

    "rizospastis.gr",
    "alphatv.gr",
    "amna.gr",
    "elkosmos.gr",
    "ethnos.gr",
    "kathimerini.gr",
    "imerisia.gr",
    "stoxos.gr",
    "tanea.gr",
    "naftemporiki.gr",
    "athensvoice.gr",
    "ekathimerini.com",
    "enet.gr",
    "tovima.gr",
    "enetenglish.gr",
    "protothema.gr",
    "newsbomb.gr",
    "tokarfi.gr",
    "efsyn.gr",
    "lifo.gr",
    "documentonews.gr",
    "antenna.gr",
    "megatv.com",
    "novasports.gr",
    "star.gr",
    "daypress.gr",
    "gavros.gr",
    "ipop.gr",
    "newsit.gr",
    "polispress.gr",
    "politisonline.com",
    "metrogreece.gr",
    "reporter.gr",
    "athinorama.gr",
    "avgi.gr",
    "espressonews.gr",
    "kerdos.gr",
    "press-time.gr",
    "real.gr",
    "eleftherostypos.gr",
    "dimokratianews.gr",
    "parapolitika.gr",
    "topontiki.gr",
    "sportime.gr",
    "prin.gr",
    "fosonline.gr",
    "freesunday.gr",
    "vradini.gr",
    "championsday.gr",
    "kontranews.gr",
    "dimoprasion.gr",
    "makeleio.gr",
    "iefimerida.gr",
    "sport-fm.gr",
    "ereportaz.gr",
    "paron.gr",
    "agronews.gr",
    "agroekfrasi.gr",
    "axianews.gr",
    "orthodoxostypos.gr",
    "wearesolomon.com",
    "insidestory.gr",
    "thepressproject.gr",
    "themanifoldfiles.org",
    "reportersunited.gr",
    "omniatv.com",
}


# ============================================================
# REGIONAL PRESS
# ============================================================

REGIONAL_PRESS = {

    "makthes.gr",
    "rodiaki.gr",
    "trakyaninsesi.com",
    "alithia.gr",
    "thrakikigi.gr",
    "xronos.gr",
    "agonas.gr",
    "alpha1.gr",
    "athinapoli.gr",
    "aixmi-news.gr",
    "pelop.gr",
    "patrisnews.com",
    "patris.gr",
    "star-fm.gr",
    "novazora.gr",
    "ditiki.gr",
    "prlogos.gr",
    "proinoslogos.gr",
    "enimerosi.com",
    "ioanninatoday.blogspot.com",
    "neoiagones.gr",
    "proinanea.gr",
    "kilkistoday.gr",
    "metrosport.gr",
    "laos-epea.gr",
    "haniotika-nea.gr",
    "cretetv.gr",
    "mesogios.gr",
    "neakriti.gr",
    "dimokratiki.gr",
    "eleftheriaonline.gr",
    "eleftheria.gr",
    "evrytanika.gr",
    "kosmoslarissa.gr",
    "e-thessalia.gr",
    "chiosnews.com",
    "emprosnet.gr",
    "estianews.gr",
    "karfitsa.gr",
}


# ============================================================
# CLEAN SOURCE NAME
# ============================================================

def clean_source_name(media_name):
    """
    Convert media_name into a safe IRaMuTeQ source value.

    Example:

        parapolitika.gr

    becomes:

        parapolitikagr

    The original media_name is not changed in the CSV.
    """

    source = media_name.strip().lower()

    source = re.sub(
        r"[^a-z0-9]",
        "",
        source
    )

    return source


# ============================================================
# NORMALIZE SOURCE FOR CLASSIFICATION
# ============================================================

def normalize_source_for_classification(media_name):
    """
    Normalize media_name for comparison with the
    National Press and Regional Press lists.

    Classification is based ONLY on media_name,
    not on the article URL.
    """

    value = (
        media_name
        or ""
    ).strip().lower()

    value = value.rstrip("/")

    # If MediaCloud supplies a URL instead of a domain,
    # extract the hostname.
    if "://" in value:

        parts = urlsplit(value)

        value = parts.netloc.lower()

    # Remove www.
    if value.startswith("www."):

        value = value[4:]

    return value


# ============================================================
# CLASSIFY SOURCE
# ============================================================

def classify_source(media_name):
    """
    Classify the source using media_name.

    Returns:

        nationalpress
        regionalpress
        unclassified
    """

    source = normalize_source_for_classification(
        media_name
    )

    if source in NATIONAL_PRESS:

        return "nationalpress"

    if source in REGIONAL_PRESS:

        return "regionalpress"

    return "unclassified"


# ============================================================
# EXTRACT YEAR AND MONTH
# ============================================================

def extract_year_month(value):
    """
    Extract year and month from MediaCloud publish_date.

    Supports common formats including:

        2026-06-23
        2026-06-23T12:30:00Z
        2026-06-23T12:30:00+00:00
        2026-06
    """

    if not value:

        return None, None

    value = value.strip()

    # --------------------------------------------------------
    # YYYY-MM-DD
    # --------------------------------------------------------

    match = re.search(
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
        value
    )

    if match:

        year = match.group(1)

        month = match.group(2).zfill(2)

        day = match.group(3)

        try:

            datetime(
                int(year),
                int(month),
                int(day)
            )

            return year, month

        except ValueError:

            pass

    # --------------------------------------------------------
    # YYYY-MM
    # --------------------------------------------------------

    match = re.search(
        r"\b(20\d{2})-(\d{1,2})\b",
        value
    )

    if match:

        year = match.group(1)

        month = match.group(2).zfill(2)

        try:

            datetime(
                int(year),
                int(month),
                1
            )

            return year, month

        except ValueError:

            pass

    return None, None


# ============================================================
# EXTRACT YEAR
# ============================================================

def extract_year(value):
    """
    Extract only the publication year from publish_date.

    Returns:

        "2026"

    or:

        None
    """

    year, month = extract_year_month(
        value
    )

    return year


# ============================================================
# CLEAN URL
# ============================================================

def clean_url(url):
    """
    Remove query parameters and fragments from a URL.

    Example:

        https://example.gr/article?utm_source=rss

    becomes:

        https://example.gr/article
    """

    parts = urlsplit(
        url.strip()
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            "",
            ""
        )
    )


# ============================================================
# VALIDATE URL
# ============================================================

def valid_url(url):
    """
    Check whether the value is an HTTP/HTTPS URL.
    """

    if not url:

        return False

    return (
        url.startswith("http://")
        or
        url.startswith("https://")
    )


# ============================================================
# CLEAN ARTICLE TEXT
# ============================================================

def clean_text(text):
    """
    Prepare article text for IRaMuTeQ.

    Tabs are removed because tabs are reserved for
    IRaMuTeQ metadata.

    Whitespace and line breaks are normalized.
    """

    if not text:

        return ""

    # --------------------------------------------------------
    # Remove tabs.
    # --------------------------------------------------------

    text = text.replace(
        "\t",
        " "
    )

    # --------------------------------------------------------
    # Normalize carriage returns.
    # --------------------------------------------------------

    text = text.replace(
        "\r",
        "\n"
    )

    # --------------------------------------------------------
    # Normalize spaces.
    # --------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # Normalize line breaks.
    # --------------------------------------------------------

    text = re.sub(
        r"\n+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# WRITE FAILURE
# ============================================================

def write_failure(
    failed_file,
    row_number,
    media_name,
    publish_date,
    url,
    reason
):
    """
    Write a detailed failure record.

    row_number is the ORIGINAL MediaCloud CSV row number.
    """

    failed_file.write(
        f"[ROW {row_number}]\n"
    )

    failed_file.write(
        f"source: {media_name}\n"
    )

    failed_file.write(
        f"publish_date: {publish_date}\n"
    )

    failed_file.write(
        f"url: {url}\n"
    )

    failed_file.write(
        f"error: {reason}\n"
    )

    failed_file.write(
        "-" * 70
        + "\n\n"
    )

    failed_file.flush()


# ============================================================
# GENERATE PUBLICATION STATISTICS
# ============================================================

def generate_publication_statistics(rows):
    """
    Generate a CSV containing the number of MediaCloud
    publications per year for each selected media source.

    IMPORTANT:

    This is calculated directly from the selected MediaCloud
    records BEFORE URL deduplication and BEFORE article
    downloading/extraction.

    Therefore, these numbers may differ from the number of
    articles ultimately included in the IRaMuTeQ TXT corpus.
    """

    # ========================================================
    # GET SELECTED SOURCES
    # ========================================================

    sources = sorted(
        {
            (
                row.get(
                    "media_name",
                    ""
                )
                or ""
            ).strip()
            for row in rows
            if (
                row.get(
                    "media_name",
                    ""
                )
                or ""
            ).strip()
        },
        key=str.lower
    )

    # ========================================================
    # COUNT ARTICLES
    # ========================================================

    counts = defaultdict(
        lambda: defaultdict(int)
    )

    years = set()

    invalid_date_rows = 0

    for row in rows:

        media_name = (
            row.get(
                "media_name",
                ""
            )
            or ""
        ).strip()

        publish_date = (
            row.get(
                "publish_date",
                ""
            )
            or ""
        ).strip()

        year = extract_year(
            publish_date
        )

        if not year:

            invalid_date_rows += 1

            continue

        counts[year][media_name] += 1

        years.add(
            year
        )

    # ========================================================
    # WRITE CSV
    # ========================================================

    with open(
        STATS_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.writer(
            f
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        writer.writerow(
            ["year"] + sources
        )

        # ----------------------------------------------------
        # One row per year
        # ----------------------------------------------------

        for year in sorted(
            years,
            key=int
        ):

            row_values = [
                year
            ]

            for source in sources:

                row_values.append(
                    counts[year].get(
                        source,
                        0
                    )
                )

            writer.writerow(
                row_values
            )

    # ========================================================
    # REPORT
    # ========================================================

    print()

    print("=" * 70)

    print("PUBLICATION STATISTICS")

    print("=" * 70)

    print()

    print(
        f"Statistics file: {STATS_FILE}"
    )

    print(
        f"Selected media: {len(sources)}"
    )

    print(
        f"Years found: {len(years)}"
    )

    if invalid_date_rows:

        print(
            f"Rows with unparseable dates: "
            f"{invalid_date_rows}"
        )

    print()

    print(
        "WARNING:"
    )

    print(
        "These statistics are calculated directly from "
        "the selected MediaCloud records."
    )

    print(
        "They may differ from the number of articles "
        "included in the final IRaMuTeQ .txt file."
    )

    print(
        "The .txt file can contain fewer articles because "
        "of duplicate URLs, inaccessible pages, request "
        "errors, extraction failures, or articles that "
        "are too short."
    )

    print()

    return STATS_FILE




# ============================================================
# POLISHED ACADEMIC RESEARCH INTERFACE
# ============================================================

import io
from datetime import datetime

import streamlit as st


st.set_page_config(
    page_title="MediaCloud → IRaMuTeQ | Corpus Research Tool",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Visual identity
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --academic-ink: #172033;
        --academic-muted: #667085;
        --academic-line: #d9dee8;
        --academic-paper: #fbfcfe;
    }

    .stApp {
        background: var(--academic-paper);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    .research-kicker {
        font-size: 0.78rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #667085;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .research-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(2.2rem, 4vw, 3.65rem);
        line-height: 1.05;
        color: #172033;
        margin: 0;
        font-weight: 600;
    }

    .research-subtitle {
        font-size: 1.08rem;
        line-height: 1.65;
        color: #667085;
        max-width: 850px;
        margin-top: 1rem;
    }

    .section-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.55rem;
        color: #172033;
        margin: 2.2rem 0 0.35rem 0;
    }

    .section-note {
        color: #667085;
        margin-bottom: 1rem;
    }

    .method-card {
        border: 1px solid #d9dee8;
        border-radius: 12px;
        padding: 1.1rem 1.2rem;
        background: white;
        min-height: 125px;
    }

    .method-number {
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #667085;
        font-weight: 700;
    }

    .method-heading {
        font-family: Georgia, "Times New Roman", serif;
        color: #172033;
        font-size: 1.12rem;
        margin-top: 0.35rem;
    }

    .method-text {
        color: #667085;
        font-size: 0.91rem;
        line-height: 1.45;
    }

    .citation-box {
        border-left: 3px solid #172033;
        background: white;
        padding: 0.85rem 1rem;
        color: #475467;
        font-size: 0.9rem;
        line-height: 1.55;
        margin: 1rem 0 1.5rem 0;
    }

    .footer-line {
        border-top: 1px solid #d9dee8;
        margin-top: 3rem;
        padding-top: 1rem;
        color: #667085;
        font-size: 0.82rem;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #d9dee8;
        padding: 0.85rem;
        border-radius: 10px;
    }

    div[data-testid="stFileUploader"] {
        background: white;
        border: 1px dashed #b9c1cf;
        border-radius: 12px;
        padding: 0.35rem;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid #d9dee8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown('<div class="research-kicker">Open research utility · corpus preparation</div>',
            unsafe_allow_html=True)
st.markdown('<h1 class="research-title">MediaCloud → IRaMuTeQ</h1>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="research-subtitle">'
    'A reproducible workflow for transforming MediaCloud article records into '
    'an IRaMuTeQ-ready textual corpus, with source classification, publication '
    'statistics, duplicate control, and transparent extraction diagnostics.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="citation-box">'
    '<strong>Workflow.</strong> Upload → inspect → select → extract → validate → export. '
    'The application processes the supplied records and does not require users to '
    'manually manipulate the resulting corpus file.'
    '</div>',
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Method overview
# ------------------------------------------------------------
steps = [
    ("01", "Upload", "Provide a MediaCloud CSV with media name, publication date, and URL."),
    ("02", "Configure", "Select sources and review extraction parameters before processing."),
    ("03", "Extract", "Download pages, extract article text, clean it, and apply IRaMuTeQ metadata."),
    ("04", "Export", "Download the corpus, publication statistics, and complete failure log."),
]
cols = st.columns(4)
for col, (num, heading, description) in zip(cols, steps):
    with col:
        st.markdown(
            f'<div class="method-card">'
            f'<div class="method-number">{num}</div>'
            f'<div class="method-heading">{heading}</div>'
            f'<div class="method-text">{description}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ------------------------------------------------------------
# Sidebar: reproducibility / parameters
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("### Processing parameters")
    delay = st.number_input(
        "Request delay",
        min_value=0.0,
        max_value=60.0,
        value=float(DELAY),
        step=0.1,
        help="Pause between requests to reduce load on source websites.",
    )
    min_article_length = st.number_input(
        "Minimum article length",
        min_value=0,
        max_value=100000,
        value=int(MIN_ARTICLE_LENGTH),
        step=10,
        help="Articles shorter than this number of characters are recorded as failures.",
    )

    st.markdown("---")
    st.markdown("### Reproducibility")
    st.caption(
        "Source classification follows the built-in National Press and Regional "
        "Press lists. Original MediaCloud row numbers are preserved in the IRaMuTeQ metadata."
    )

    st.markdown("---")
    st.markdown("### Input specification")
    st.code("media_name\npublish_date\nurl", language="text")

# ------------------------------------------------------------
# Upload
# ------------------------------------------------------------
st.markdown('<div class="section-title">1. Corpus input</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">Upload the CSV exported from MediaCloud.</div>',
    unsafe_allow_html=True,
)

uploaded = st.file_uploader(
    "MediaCloud CSV",
    type=["csv"],
    label_visibility="collapsed",
    help="Required columns: media_name, publish_date, url",
)

if uploaded is None:
    st.info(
        "No corpus loaded yet. Upload a CSV to inspect its sources and begin."
    )
    st.markdown(
        '<div class="footer-line">'
        'Designed for corpus preparation and transparent downstream analysis in IRaMuTeQ.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ------------------------------------------------------------
# Read input
# ------------------------------------------------------------
try:
    uploaded_bytes = uploaded.getvalue()
    decoded = uploaded_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    if not reader.fieldnames:
        st.error("The CSV contains no header.")
        st.stop()

    required_columns = {"media_name", "publish_date", "url"}
    missing = required_columns - set(reader.fieldnames)

    if missing:
        st.error(
            "The uploaded CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )
        st.stop()

    rows = []
    for row_number, row in enumerate(reader, 2):
        row["_rawnb"] = row_number
        rows.append(row)

except Exception as e:
    st.error(f"Unable to read the CSV: {type(e).__name__}: {e}")
    st.stop()

if not rows:
    st.warning("The CSV contains no article records.")
    st.stop()

source_counts = {}
for row in rows:
    media_name = (row.get("media_name", "") or "").strip()
    if media_name:
        source_counts[media_name] = source_counts.get(media_name, 0) + 1

if not source_counts:
    st.error("No usable `media_name` values were found.")
    st.stop()

# Dataset overview.
overview = st.columns(3)
overview[0].metric("Input records", f"{len(rows):,}")
overview[1].metric("Unique media names", f"{len(source_counts):,}")
overview[2].metric("CSV size", f"{len(uploaded_bytes) / 1024:.1f} KB")

# ------------------------------------------------------------
# Source selection
# ------------------------------------------------------------
st.markdown('<div class="section-title">2. Corpus scope</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">Choose which media sources should enter the extraction workflow.</div>',
    unsafe_allow_html=True,
)

sorted_sources = sorted(source_counts.items(), key=lambda item: item[0].lower())

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    if st.button("Select all sources", use_container_width=True):
        st.session_state["selected_sources"] = {s for s, _ in sorted_sources}
with c2:
    if st.button("Clear selection", use_container_width=True):
        st.session_state["selected_sources"] = set()

if "selected_sources" not in st.session_state:
    st.session_state["selected_sources"] = {s for s, _ in sorted_sources}

selected_sources = set()

# Compact two-column source selector.
source_cols = st.columns(2)
for i, (source, count) in enumerate(sorted_sources):
    key = "source_" + re.sub(r"[^a-zA-Z0-9_]", "_", source)
    with source_cols[i % 2]:
        checked = st.checkbox(
            f"{source}  ·  {count:,}",
            value=source in st.session_state["selected_sources"],
            key=key,
        )
        if checked:
            selected_sources.add(source)

st.session_state["selected_sources"] = selected_sources

selected_rows = [
    row for row in rows
    if (row.get("media_name", "") or "").strip() in selected_sources
]

s1, s2, s3 = st.columns(3)
s1.metric("Selected sources", f"{len(selected_sources):,}")
s2.metric("Selected records", f"{len(selected_rows):,}")
s3.metric(
    "Share of input",
    f"{(100 * len(selected_rows) / len(rows)):.1f}%" if rows else "0.0%",
)

with st.expander("Review source classification", expanded=False):
    preview = []
    for source in sorted(selected_sources, key=str.lower):
        preview.append(
            {
                "Source": source,
                "Articles": source_counts[source],
                "Classification": classify_source(source),
            }
        )
    if preview:
        st.dataframe(
            preview,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No sources selected.")

if not selected_rows:
    st.warning("Select at least one source to continue.")
    st.stop()

# ------------------------------------------------------------
# Run
# ------------------------------------------------------------
st.markdown('<div class="section-title">3. Corpus construction</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">'
    'The application will deduplicate URLs, retrieve article pages, extract text, '
    'and construct IRaMuTeQ metadata headers.'
    '</div>',
    unsafe_allow_html=True,
)

with st.expander("What will be produced?", expanded=False):
    st.markdown(
        """
        **IRaMuTeQ corpus**

        Each successfully extracted article receives the metadata fields:
        `source`, `year`, `yearmonth`, `type`, and `rawnb`.

        **Publication statistics**

        Counts are calculated from the selected MediaCloud records before URL
        deduplication and article extraction.

        **Failure log**

        Records missing metadata, invalid URLs, request failures, extraction
        failures, short articles, and unexpected errors.
        """
    )

run = st.button(
    "Begin corpus construction",
    type="primary",
    use_container_width=True,
)

if run:
    runtime_output = "news_iramuteq.txt"
    runtime_failed = "failed_articles.txt"
    runtime_stats = "publication_counts_by_year.csv"

    # Publication statistics: same logic as original script.
    sources = sorted(
        {
            (row.get("media_name", "") or "").strip()
            for row in selected_rows
            if (row.get("media_name", "") or "").strip()
        },
        key=str.lower,
    )

    counts = defaultdict(lambda: defaultdict(int))
    years = set()
    invalid_date_rows = 0

    for row in selected_rows:
        media_name = (row.get("media_name", "") or "").strip()
        publish_date = (row.get("publish_date", "") or "").strip()
        year = extract_year(publish_date)

        if not year:
            invalid_date_rows += 1
            continue

        counts[year][media_name] += 1
        years.add(year)

    stats_buffer = io.StringIO()
    writer = csv.writer(stats_buffer)
    writer.writerow(["year"] + sources)
    for year in sorted(years, key=int):
        writer.writerow(
            [year] + [counts[year].get(source, 0) for source in sources]
        )
    stats_bytes = stats_buffer.getvalue().encode("utf-8-sig")

    # URL deduplication: same logic as original.
    selected_count = len(selected_rows)
    unique_rows = []
    seen = set()
    duplicate_count = 0

    for row in selected_rows:
        raw_url = (row.get("url", "") or "").strip()

        if not valid_url(raw_url):
            unique_rows.append(row)
            continue

        normalized_url = clean_url(raw_url)

        if normalized_url in seen:
            duplicate_count += 1
            continue

        seen.add(normalized_url)
        unique_rows.append(row)

    rows_to_process = unique_rows

    st.markdown("### Extraction progress")
    progress = st.progress(0, text="Preparing requests…")
    status = st.empty()
    metrics = st.empty()

    output_buffer = io.StringIO()
    failed_buffer = io.StringIO()

    successful = 0
    errors = 0
    missing_metadata = 0
    request_errors = 0
    extraction_errors = 0
    short_articles = 0
    unexpected_errors = 0
    national_count = 0
    regional_count = 0
    unclassified_count = 0

    def write_failure_web(row_number, media_name, publish_date, url, reason):
        failed_buffer.write(f"[ROW {row_number}]\n")
        failed_buffer.write(f"source: {media_name}\n")
        failed_buffer.write(f"publish_date: {publish_date}\n")
        failed_buffer.write(f"url: {url}\n")
        failed_buffer.write(f"error: {reason}\n")
        failed_buffer.write("-" * 70 + "\n\n")

    session = requests.Session()

    for number, row in enumerate(rows_to_process, 1):
        raw_number = row.get("_rawnb")
        media_name = (row.get("media_name", "") or "").strip()
        publish_date = (row.get("publish_date", "") or "").strip()
        raw_url = (row.get("url", "") or "").strip()

        status.write(
            f"Processing **{number:,} / {len(rows_to_process):,}** · "
            f"{media_name} · MediaCloud row {raw_number}"
        )

        if not media_name:
            reason = "Missing media_name"
            write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
            errors += 1
            missing_metadata += 1
            continue

        year, month = extract_year_month(publish_date)
        if not year:
            reason = "Could not parse publish_date"
            write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
            errors += 1
            missing_metadata += 1
            continue

        if not valid_url(raw_url):
            reason = "Invalid or missing URL"
            write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
            errors += 1
            missing_metadata += 1
            continue

        url = clean_url(raw_url)

        try:
            response = session.get(
                url,
                headers=HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            html = response.text

            article = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=False,
                include_images=False,
                include_links=False,
                favor_precision=True,
                output_format="txt",
            )

            if not article:
                reason = "Trafilatura returned no text"
                write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
                errors += 1
                extraction_errors += 1
                progress.progress(
                    number / len(rows_to_process),
                    text=f"Processed {number:,} / {len(rows_to_process):,}",
                )
                if number < len(rows_to_process):
                    time.sleep(delay)
                continue

            article = clean_text(article)

            if len(article) < min_article_length:
                reason = (
                    "Extracted article is too short "
                    f"({len(article)} characters; minimum is {min_article_length})"
                )
                write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
                errors += 1
                short_articles += 1
                progress.progress(
                    number / len(rows_to_process),
                    text=f"Processed {number:,} / {len(rows_to_process):,}",
                )
                if number < len(rows_to_process):
                    time.sleep(delay)
                continue

            source = clean_source_name(media_name)
            press_type = classify_source(media_name)

            if press_type == "nationalpress":
                national_count += 1
            elif press_type == "regionalpress":
                regional_count += 1
            else:
                unclassified_count += 1

            header = (
                "****"
                f" *source_{source}"
                f" *year_{year}"
                f" *yearmonth_{year}-{month}"
                f" *type_{press_type}"
                f" *rawnb_{raw_number}"
            )

            output_buffer.write(header + "\n")
            output_buffer.write(article + "\n\n")
            successful += 1

            if press_type == "unclassified":
                write_failure_web(
                    raw_number,
                    media_name,
                    publish_date,
                    raw_url,
                    "Source could not be classified as National Press or Regional Press",
                )

        except requests.exceptions.RequestException as e:
            reason = f"Request error: {type(e).__name__}: {e}"
            write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
            errors += 1
            request_errors += 1

        except Exception as e:
            reason = f"Unexpected error: {type(e).__name__}: {e}"
            write_failure_web(raw_number, media_name, publish_date, raw_url, reason)
            errors += 1
            unexpected_errors += 1

        progress.progress(
            number / len(rows_to_process),
            text=f"Processed {number:,} / {len(rows_to_process):,}",
        )
        metrics.write(
            f"**Saved:** {successful:,} &nbsp; · &nbsp; "
            f"**Failed:** {errors:,} &nbsp; · &nbsp; "
            f"**National:** {national_count:,} &nbsp; · &nbsp; "
            f"**Regional:** {regional_count:,} &nbsp; · &nbsp; "
            f"**Unclassified:** {unclassified_count:,}"
        )

        if number < len(rows_to_process):
            time.sleep(delay)

    progress.progress(1.0, text="Corpus construction complete.")

    corpus_bytes = output_buffer.getvalue().encode("utf-8")
    failed_bytes = failed_buffer.getvalue().encode("utf-8")

    st.success("Corpus construction completed.")

    st.markdown("### Research output summary")
    result_cols = st.columns(5)
    result_cols[0].metric("Articles saved", f"{successful:,}")
    result_cols[1].metric("Articles failed", f"{errors:,}")
    result_cols[2].metric("Duplicate URLs", f"{duplicate_count:,}")
    result_cols[3].metric("National press", f"{national_count:,}")
    result_cols[4].metric("Regional press", f"{regional_count:,}")

    if successful:
        success_rate = 100 * successful / len(rows_to_process)
        st.caption(
            f"Extraction success rate: **{success_rate:.1f}%** "
            f"({successful:,} of {len(rows_to_process):,} processed records)."
        )

    st.markdown("### Diagnostics")
    failure_data = [
        {"Failure category": "Metadata errors", "Count": missing_metadata},
        {"Failure category": "Request errors", "Count": request_errors},
        {"Failure category": "Extraction errors", "Count": extraction_errors},
        {"Failure category": "Short articles", "Count": short_articles},
        {"Failure category": "Unexpected errors", "Count": unexpected_errors},
    ]
    st.dataframe(
        failure_data,
        use_container_width=True,
        hide_index=True,
    )

    if invalid_date_rows:
        st.warning(
            f"{invalid_date_rows:,} selected rows had unparseable dates and were "
            "therefore omitted from publication statistics."
        )

    if unclassified_count:
        st.warning(
            f"{unclassified_count:,} successfully extracted articles came from "
            "sources not present in the built-in National/Regional Press lists."
        )

    st.markdown("### Download research outputs")
    st.caption(
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
        "Files are produced for this session and are not intended as permanent storage."
    )

    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "Download IRaMuTeQ corpus",
            data=corpus_bytes,
            file_name=runtime_output,
            mime="text/plain",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "Download publication statistics",
            data=stats_bytes,
            file_name=runtime_stats,
            mime="text/csv",
            use_container_width=True,
        )
    with d3:
        st.download_button(
            "Download failure log",
            data=failed_bytes,
            file_name=runtime_failed,
            mime="text/plain",
            use_container_width=True,
        )

    with st.expander("Methodological notes", expanded=False):
        st.markdown(
            """
            **Publication statistics** are calculated directly from the selected
            MediaCloud records before duplicate URL removal and before article
            extraction.

            **Corpus counts** can therefore differ from the publication statistics.
            Records may be excluded because of duplicate URLs, invalid metadata,
            inaccessible pages, extraction failures, or article length.

            **IRaMuTeQ metadata** retain the original MediaCloud row number through
            the `rawnb` field, allowing the resulting corpus to be traced back to
            the source CSV.
            """
        )

st.markdown(
    '<div class="footer-line">'
    'MediaCloud → IRaMuTeQ · corpus preparation interface · '
    'Designed for reproducible text analysis workflows'
    '</div>',
    unsafe_allow_html=True,
)
