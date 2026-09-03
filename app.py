##Created by Panos Tsimpoukis with ChatGPT / September 2026##
#!/usr/bin/env python3

import csv
import re
import time
import unicodedata

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

def clean_custom_metadata_token(value, fallback="missing"):
    """
    Convert a user-supplied metadata name/value into an IRaMuTeQ-safe token.

    Accents are removed, whitespace/punctuation become underscores, repeated
    underscores are collapsed, and values are normalized to lowercase.
    Empty cells become the explicit category ``missing``.
    """
    value = "" if value is None else str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or fallback


def prepare_custom_metadata_fields(columns):
    """
    Create unique IRaMuTeQ metadata field names from CSV column headers.
    """
    used = {}
    prepared = []

    for column in columns:
        base = clean_custom_metadata_token(column, fallback="metadata")
        count = used.get(base, 0) + 1
        used[base] = count
        field = base if count == 1 else f"{base}_{count}"
        prepared.append((column, field))

    return prepared


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

    /* High-contrast text for accessibility and reliable rendering across themes. */
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div,
    [data-testid="stSidebar"], [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #111111;
    }
    .research-kicker, .section-note, .research-subtitle, .method-text,
    .method-number, .footer-line, .stCaption, [data-testid="stCaptionContainer"] {
        color: #444444 !important;
    }
    .research-title, .section-title, .method-heading {
        color: #111111 !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #111111 !important;
    }
    input, textarea, [data-baseweb="select"] * {
        color: #111111 !important;
    }
    code {
        color: #111111 !important;
    }

    /* Dark controls: keep text white wherever Streamlit renders a dark widget. */
    [data-testid="stSidebar"] {
        background: #111111 !important;
    }
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [role="spinbutton"] {
        background-color: #111111 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border-color: #555555 !important;
    }

    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
        color: #d0d0d0 !important;
        -webkit-text-fill-color: #d0d0d0 !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background-color: #111111 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: 1px solid #111111 !important;
    }

    .stButton > button *,
    .stDownloadButton > button *,
    [data-testid="stFormSubmitButton"] > button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #2b2b2b !important;
        color: #ffffff !important;
    }

    /* Keep the main source-selection labels readable on the light research canvas. */
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label p,
    [data-testid="stCheckbox"] label span {
        color: #111111 !important;
    }

    /* High-contrast uploader: the selected filename must remain readable. */
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stFileUploaderFileName"],
    [data-testid="stFileUploaderFileName"] *,
    [data-testid="stFileUploader"] small {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important;
        border-color: #777777 !important;
    }

    /* Metadata field names on dark research cards. */
    .metadata-card {
        background: #111111 !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
        padding: 1.1rem 1.2rem !important;
    }
    .metadata-card, .metadata-card * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
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
    with st.expander("About", expanded=False):
        st.markdown(
            """
            **MediaCloud → IRaMuTeQ**

            A research tool for transforming MediaCloud article records into an IRaMuTeQ-compatible corpus.

            **Created by**  
            Panos Tsimpoukis  
            with the help of ChatGPT  
            LERASS (UT) · PhEPoC-ST (NTUA)
            """
        )

    st.markdown("### Corpus language / source classification")
    classification_mode = st.selectbox(
        "How should sources be classified?",
        options=[
            "Greek corpus — use National / Regional press classification",
            "Other language — do not classify as National / Regional press",
        ],
        index=0,
        help="Choose the second option for French or other non-Greek corpora. The article text is still extracted normally; only the Greek-specific National/Regional press classification is switched off.",
    )
    use_press_classification = classification_mode.startswith("Greek corpus")
    st.caption(
        "For non-Greek corpora, the tool keeps the source and date metadata but leaves the press category as unclassified."
        if not use_press_classification else
        "For Greek corpora, the built-in National Press and Regional Press lists are used."
    )

    st.markdown("### Processing settings")
    st.caption(
        "These controls affect how aggressively the application retrieves pages and "
        "how short an extracted text can be before it is excluded."
    )
    delay = st.number_input(
        "Wait between article requests (seconds)",
        min_value=0.0,
        max_value=60.0,
        value=float(DELAY),
        step=0.1,
        help="This is the pause between visits to article webpages. Use 1.5 seconds for normal use. Use 2–5 seconds for very large datasets or when you want to be more conservative toward websites. Lower values are mainly for small tests.",
    )
    min_article_length = st.number_input(
        "Minimum article length (characters)",
        min_value=0,
        max_value=100000,
        value=int(MIN_ARTICLE_LENGTH),
        step=10,
        help="Extracted texts shorter than this threshold are logged as short articles rather than added to the corpus.",
    )

    with st.expander("How should I choose these settings?", expanded=False):
        st.markdown(
            """
            **Wait between article requests**

This controls how long the app waits before visiting the next article webpage. A longer wait is slower but more considerate to the websites being accessed.

            - **1.5 s (recommended default):** good for ordinary research batches and the closest match to the original script.
            - **2–5 s:** preferable for very large corpora, slower servers, or when you want to be especially conservative toward source websites.
            - **0–1 s:** useful only for small test batches. Faster is not necessarily better and may increase the chance of rate limiting.

            **Minimum article length**

            - **100 characters (recommended default):** keeps the original script's behavior and removes obviously empty/very short extractions.
            - **200–500 characters:** useful when you want to exclude snippets, navigation remnants, or unusually poor extractions more aggressively.
            - **0 characters:** mainly for diagnostic/testing purposes; it may allow low-quality extractions into the corpus.

            There is no universally correct threshold: choose values that match the corpus and document them when reporting your research.
            """
        )

    st.markdown("---")
    st.markdown("### Reproducibility")
    st.caption(
        "Original MediaCloud row numbers are preserved in the IRaMuTeQ metadata. "
        "National/Regional press classification is used only when the Greek-corpus option is selected."
    )

    st.markdown("---")
    st.markdown("### Input specification")
    st.markdown(
        "Your CSV must contain these **three column names**. Each row represents one "
        "MediaCloud article record."
    )
    st.markdown(
        """
        **`media_name`** — the name of the newspaper, website, or other media source as recorded by MediaCloud (for example, `kathimerini.gr`).

        **`publish_date`** — the date/time when the article was published. The application uses it to determine the publication year and year-month.

        **`url`** — the complete web address of the article (for example, `https://example.org/article`). The application visits this webpage and attempts to extract the article text.

        **In short:** one CSV row should correspond to one article record from your MediaCloud export. The file can have any filename (for example, `my_french_corpus.csv`); only the required column names matter.
        """
    )

# ------------------------------------------------------------
# Upload
# ------------------------------------------------------------
st.markdown('<div class="section-title">1. Corpus input</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">Upload the CSV exported from MediaCloud. The filename itself does not matter; the application reads the file you upload.</div>',
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


def classify_for_corpus(media_name):
    """Apply the selected corpus-level classification policy."""
    if not use_press_classification:
        return "unclassified"
    return classify_source(media_name)

# ------------------------------------------------------------
# Source selection
# ------------------------------------------------------------
st.markdown('<div class="section-title">2. Corpus scope</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">Choose which media sources should enter the extraction workflow.</div>',
    unsafe_allow_html=True,
)

sorted_sources = sorted(source_counts.items(), key=lambda item: item[0].lower())

# Use widget state for each checkbox. This avoids the common Streamlit issue where
# a button changes a separate set and the checkbox widgets immediately overwrite it.
source_fingerprint = "|".join(f"{s}:{c}" for s, c in sorted_sources)
if st.session_state.get("source_fingerprint") != source_fingerprint:
    st.session_state["source_fingerprint"] = source_fingerprint
    for idx, (source, _) in enumerate(sorted_sources):
        st.session_state[f"source_choice_{idx}"] = True

def set_all_sources(value):
    for idx, _ in enumerate(sorted_sources):
        st.session_state[f"source_choice_{idx}"] = value


# Selection controls are deliberately placed before the checkbox widgets so
# Streamlit can update their session state cleanly on the next rerun.
control_col1, control_col2, _ = st.columns([1, 1, 2])
with control_col1:
    st.button(
        "Select all",
        key="select_all_sources",
        on_click=set_all_sources,
        args=(True,),
        use_container_width=True,
    )
with control_col2:
    st.button(
        "Deselect all",
        key="deselect_all_sources",
        on_click=set_all_sources,
        args=(False,),
        use_container_width=True,
    )

selected_sources = set()
source_cols = st.columns(2)
for i, (source, count) in enumerate(sorted_sources):
    with source_cols[i % 2]:
        checked = st.checkbox(
            f"{source}  ·  {count:,} articles",
            key=f"source_choice_{i}",
        )
        if checked:
            selected_sources.add(source)

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
                "Classification": classify_for_corpus(source),
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
# Custom metadata
# ------------------------------------------------------------
st.markdown('<div class="section-title">3. Custom metadata</div>', unsafe_allow_html=True)
st.markdown(
    "<div class='section-note'>Optionally carry one or more additional CSV columns into each IRaMuTeQ document header. The column header becomes the metadata name, and each row value becomes that article's metadata category.</div>",
    unsafe_allow_html=True,
)

required_columns = {"media_name", "publish_date", "url"}
custom_metadata_options = [
    column for column in reader.fieldnames
    if column not in required_columns and not column.startswith("_")
]

custom_metadata_columns = st.multiselect(
    "Select CSV columns to add as metadata",
    options=custom_metadata_options,
    help="You can select multiple columns. For example, a column named mediatype with values national/regional will produce *mediatype_national and *mediatype_regional in the IRaMuTeQ headers.",
)

custom_metadata_fields = prepare_custom_metadata_fields(custom_metadata_columns)

if custom_metadata_fields:
    st.caption(
        "Selected columns are preserved as separate metadata fields. "
        "Accents are removed and spaces/punctuation are converted to underscores "
        "for IRaMuTeQ-safe names and values; empty cells become `missing`."
    )

    preview_row = selected_rows[0] if selected_rows else rows[0]
    metadata_preview = []
    for original_column, field_name in custom_metadata_fields:
        raw_value = preview_row.get(original_column, "")
        safe_value = clean_custom_metadata_token(raw_value)
        metadata_preview.append(
            {
                "CSV column": original_column,
                "IRaMuTeQ metadata": f"*{field_name}_{safe_value}",
            }
        )

    with st.expander("Preview custom metadata", expanded=True):
        st.dataframe(metadata_preview, use_container_width=True, hide_index=True)
else:
    st.caption(
        "No custom metadata selected. The corpus will use the built-in source/date/type/rawnb metadata only."
    )

# ------------------------------------------------------------
# Run
# ------------------------------------------------------------
st.markdown('<div class="section-title">4. Corpus construction</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">'
    'The application will deduplicate URLs, retrieve article pages, extract text, '
    'and construct IRaMuTeQ metadata headers.'
    '</div>',
    unsafe_allow_html=True,
)

with st.expander("What will be produced?", expanded=False):
    st.markdown('<div class="metadata-card">', unsafe_allow_html=True)
    st.markdown(
        """
        **IRaMuTeQ corpus**

        Each successfully extracted article receives five core metadata fields:

        - `source` — cleaned name of the publication or media source.
        - `year` — publication year.
        - `yearmonth` — publication year and month, in `YYYY-MM` format.
        - `type` — source category: national press, regional press, or unclassified.
        - `rawnb` — original row number of the article in the uploaded CSV, useful for tracing the corpus entry back to the source data.

        **Custom metadata**

        Any additional CSV columns selected above are appended to the same IRaMuTeQ header. The CSV header becomes the metadata name and each cell becomes that article's category. Multiple classifications can be selected at once, such as `mediatype`, `region`, `ownership`, or `political_orientation`.

        **Publication statistics**

        Counts are calculated from the selected MediaCloud records before URL
        deduplication and article extraction.

        **Failure log**

        Records missing metadata, invalid URLs, request failures, extraction
        failures, short articles, and unexpected errors.
        """
    )
    st.markdown('</div>', unsafe_allow_html=True)

run = st.button(
    "Begin corpus construction",
    type="primary",
    use_container_width=True,
)

if run:
    st.session_state["corpus_run_requested"] = True
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
            press_type = classify_for_corpus(media_name)

            if press_type == "nationalpress":
                national_count += 1
            elif press_type == "regionalpress":
                regional_count += 1
            else:
                unclassified_count += 1

            custom_tokens = []
            for original_column, field_name in custom_metadata_fields:
                raw_value = row.get(original_column, "")
                safe_value = clean_custom_metadata_token(raw_value)
                custom_tokens.append(f"*{field_name}_{safe_value}")

            header_parts = [
                "****",
                f"*source_{source}",
                f"*year_{year}",
                f"*yearmonth_{year}-{month}",
                f"*type_{press_type}",
                f"*rawnb_{raw_number}",
                *custom_tokens,
            ]
            header = " ".join(header_parts)

            output_buffer.write(header + "\n")
            output_buffer.write(article + "\n\n")
            successful += 1

            if press_type == "unclassified" and use_press_classification:
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

            **Custom metadata** are copied from the selected CSV columns. The column
            header becomes the metadata field name and each cell becomes the category
            for that article. Metadata names and values are normalized to lowercase
            ASCII-safe tokens; empty cells are represented as `missing`.
            """
        )

    st.session_state["research_outputs"] = {
        "corpus": corpus_bytes,
        "failed": failed_bytes,
        "stats": stats_bytes,
        "successful": successful,
        "errors": errors,
        "duplicate_count": duplicate_count,
        "national_count": national_count,
        "regional_count": regional_count,
        "unclassified_count": unclassified_count,
        "rows_processed": len(rows_to_process),
        "missing_metadata": missing_metadata,
        "request_errors": request_errors,
        "extraction_errors": extraction_errors,
        "short_articles": short_articles,
        "unexpected_errors": unexpected_errors,
        "invalid_date_rows": invalid_date_rows,
        "custom_metadata_columns": custom_metadata_columns,
    }

# ------------------------------------------------------------
# Persistent research outputs
# ------------------------------------------------------------
# Streamlit reruns the script when a download button is pressed. Keep the generated
# files in session state so the results section remains available for subsequent downloads.
if st.session_state.get("research_outputs") and not run:
    out = st.session_state["research_outputs"]
    st.markdown('<div class="section-title">5. Research outputs</div>', unsafe_allow_html=True)
    st.success("Corpus construction is complete. Your generated files remain available for download in this session.")

    r = st.columns(5)
    r[0].metric("Articles saved", f"{out['successful']:,}")
    r[1].metric("Articles failed", f"{out['errors']:,}")
    r[2].metric("Duplicate URLs", f"{out['duplicate_count']:,}")
    r[3].metric("National press", f"{out['national_count']:,}")
    r[4].metric("Regional press", f"{out['regional_count']:,}")

    if out["successful"]:
        st.caption(f"Extraction success rate: **{100 * out['successful'] / out['rows_processed']:.1f}%** ({out['successful']:,} of {out['rows_processed']:,} processed records).")

    st.markdown("### Download research outputs")
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button("Download IRaMuTeQ corpus", data=out["corpus"], file_name="news_iramuteq.txt", mime="text/plain", use_container_width=True, key="download_corpus_persistent")
    with d2:
        st.download_button("Download publication statistics", data=out["stats"], file_name="publication_counts_by_year.csv", mime="text/csv", use_container_width=True, key="download_stats_persistent")
    with d3:
        st.download_button("Download failure log", data=out["failed"], file_name="failed_articles.txt", mime="text/plain", use_container_width=True, key="download_failed_persistent")

    with st.expander("Diagnostics", expanded=False):
        st.dataframe([
            {"Failure category": "Metadata errors", "Count": out["missing_metadata"]},
            {"Failure category": "Request errors", "Count": out["request_errors"]},
            {"Failure category": "Extraction errors", "Count": out["extraction_errors"]},
            {"Failure category": "Short articles", "Count": out["short_articles"]},
            {"Failure category": "Unexpected errors", "Count": out["unexpected_errors"]},
        ], use_container_width=True, hide_index=True)
        if out["invalid_date_rows"]:
            st.warning(f"{out['invalid_date_rows']:,} selected rows had unparseable dates and were omitted from publication statistics.")
        if out["unclassified_count"]:
            st.warning(f"{out['unclassified_count']:,} successfully extracted articles came from sources not present in the built-in National/Regional Press lists.")

    with st.expander("Methodological notes", expanded=False):
        st.markdown(
            """
            **Publication statistics** are calculated directly from the selected MediaCloud records before duplicate URL removal and before article extraction.

            **Corpus counts** can therefore differ from publication statistics because records may be excluded for duplicate URLs, invalid metadata, inaccessible pages, extraction failures, or insufficient text length.

            **IRaMuTeQ metadata** retain the original MediaCloud row number through the `rawnb` field, allowing the resulting corpus to be traced back to the source CSV.
            """
        )

st.markdown(
    '<div class="footer-line">'
    'MediaCloud → IRaMuTeQ · corpus preparation interface'
    '</div>',
    unsafe_allow_html=True,
)
