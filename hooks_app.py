"""
HAKI · GANCHOS · HOOKS — two-letter drop, one-letter hook
=========================================================

A study tool for word-puzzle authors and Scrabble players.

    Take a word, drop TWO letters, then add ONE letter at the front or at the
    back so that the result is again a dictionary word.

        KREDA  → drop DA →  KRE   →  KREM, KRET, KREW     back hooks:  MTW
        PIASEK → drop PI →  ASEK  →  LASEK                front hook:  L

    Text notation:   front-STEM-back        e.g.  L-ASEK-Ø   (Ø = nothing)

Two views:
  · one word  — every stem you get by dropping two letters (the last two /
                the first two, or any two), with its front and back hooks;
  · one length — a table of every word of that length: stem after dropping
                the last two letters + back hooks, stem after dropping the
                first two letters + front hooks.

Run locally:
    pip install streamlit pandas
    streamlit run hooks_app.py

Dictionaries — UTF-8, one word per line — next to this file:
    dict_pl.txt   dict_es.txt   dict_en.txt
Any other .txt can be uploaded from the sidebar.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import random
import unicodedata
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd
import streamlit as st

# ==========================================================================
# Languages: UI strings and dictionary files
# ==========================================================================

LANGS = {
    "pl": {"label": "Polski", "file": "dict_pl.txt",
           "alphabet": "aąbcćdeęfghijklłmnńoópqrsśtuvwxyzźż"},
    "es": {"label": "Español", "file": "dict_es.txt",
           "alphabet": "abcdefghijklmnñopqrstuvwxyz"},
    "en": {"label": "English", "file": "dict_en.txt",
           "alphabet": "abcdefghijklmnopqrstuvwxyz"},
}
EMPTY = "Ø"   # no hook on that side
DOT = "·"     # a dropped letter inside the pattern

T = {
    "pl": {
        "title": "Haki dwuliterowe",
        "tagline": "Odrzuć dwie litery, dołóż jedną z przodu lub z tyłu — i sprawdź, czy wychodzi słowo ze słownika.",
        "ui": "Interfejs", "dict": "Słownik",
        "upload": "…lub wgraj własny .txt", "upload_help": "Jedno słowo w wierszu, UTF-8.",
        "missing": "Nie znaleziono pliku `{file}` obok skryptu — wgraj słownik z paska bocznego.",
        "loading": "Wczytuję słownik…",
        "stats": "**{n}** słów · długości {a}–{b} · `{src}`",
        "tab_word": "Jedno słowo", "tab_len": "Wszystkie słowa danej długości",
        "length": "Długość", "word": "Słowo", "word_ph": "np. kreda", "random": "🎲 Losuj",
        "mode": "Odrzucane litery", "mode_ends": "dwie ostatnie / dwie pierwsze", "mode_any": "dowolne dwie",
        "only_hooks": "tylko rdzenie z hakami",
        "not_in_dict": "**{w}** nie występuje w słowniku — liczę mimo to.",
        "enter_word": "Wpisz słowo albo wylosuj.", "no_stems": "Żaden rdzeń nie ma haków.",
        "c_pattern": "wzór", "c_stem": "rdzeń", "c_front": "◀ przód", "c_back": "tył ▶",
        "c_n": "#", "c_words": "słowa", "c_notation": "zapis",
        "c_word": "SŁOWO", "c_end": "−koniec", "c_start": "−początek",
        "c_nb": "#▶", "c_nf": "#◀", "c_total": "#haki",
        "side": "Haki", "side_all": "wszystkie", "side_back": "z tyłu", "side_front": "z przodu",
        "side_both": "z obu stron", "side_none": "bez haków",
        "min_hooks": "Min. haków", "sort": "Kolejność", "sort_alpha": "alfabetycznie", "sort_hooks": "najwięcej haków",
        "starts": "Zaczyna się na", "ends": "Kończy się na", "contains": "Zawiera",
        "rows": "Wierszy na ekranie",
        "summary": "**{k}** słów · {b} z hakiem z tyłu · {f} z hakiem z przodu · {t} bez haków",
        "showing": "Pokazano {k} z {t} — CSV zawiera wszystkie.",
        "view_table": "Tabela", "view_text": "Tekst",
        "csv": "Eksport CSV ({k} wierszy)", "download": "⬇️ Pobierz", "empty": "Brak wyników.",
        "c_bs": "rdzenie▶", "c_nbw": "słowa▶", "c_fs": "◀rdzenie", "c_nfw": "◀słowa",
        "sort_few": "najmniej haków",
        "unique": "tylko jednoznaczne", "unique_help": "Tylko jeden układ odrzucenia liter daje hak po wybranej stronie i jest to dokładnie jedna litera — zadanie ma jedno rozwiązanie (przy „wszystkie”: jedno w sumie, z przodu albo z tyłu).",
        "computing": "Liczę wszystkie pary liter…",
        "summary_any": "**{k}** słów · {b} z hakiem z tyłu ({ub} jednoznacznych) · {f} z hakiem z przodu ({uf} jednoznacznych)",
        "legend": ("**wzór** — słowo z odrzuconymi literami jako `·` · "
                   "**◀ przód / tył ▶** — litery, które dołożone do rdzenia dają słowo ze słownika · "
                   "**zapis** — przód‑RDZEŃ‑tył, `Ø` = brak haka · dokładana litera jest zawsze inna niż dwie odrzucone."),
    },
    "es": {
        "title": "Ganchos de dos letras",
        "tagline": "Quita dos letras, añade una por delante o por detrás — y comprueba si sale una palabra del diccionario.",
        "ui": "Interfaz", "dict": "Diccionario",
        "upload": "…o sube tu propio .txt", "upload_help": "Una palabra por línea, UTF-8.",
        "missing": "No se encontró `{file}` junto al script — sube un diccionario desde la barra lateral.",
        "loading": "Cargando el diccionario…",
        "stats": "**{n}** palabras · longitudes {a}–{b} · `{src}`",
        "tab_word": "Una palabra", "tab_len": "Todas las palabras de una longitud",
        "length": "Longitud", "word": "Palabra", "word_ph": "p. ej. tiza", "random": "🎲 Al azar",
        "mode": "Letras que se quitan", "mode_ends": "las dos últimas / las dos primeras", "mode_any": "dos cualesquiera",
        "only_hooks": "solo raíces con ganchos",
        "not_in_dict": "**{w}** no está en el diccionario — se calcula igualmente.",
        "enter_word": "Escribe una palabra o elige una al azar.", "no_stems": "Ninguna raíz tiene ganchos.",
        "c_pattern": "patrón", "c_stem": "raíz", "c_front": "◀ delante", "c_back": "detrás ▶",
        "c_n": "#", "c_words": "palabras", "c_notation": "notación",
        "c_word": "PALABRA", "c_end": "−final", "c_start": "−inicio",
        "c_nb": "#▶", "c_nf": "#◀", "c_total": "#ganchos",
        "side": "Ganchos", "side_all": "todas", "side_back": "detrás", "side_front": "delante",
        "side_both": "ambos lados", "side_none": "sin ganchos",
        "min_hooks": "Mín. ganchos", "sort": "Orden", "sort_alpha": "alfabético", "sort_hooks": "más ganchos",
        "starts": "Empieza por", "ends": "Termina en", "contains": "Contiene",
        "rows": "Filas en pantalla",
        "summary": "**{k}** palabras · {b} con gancho detrás · {f} con gancho delante · {t} sin ganchos",
        "showing": "Mostrando {k} de {t} — el CSV las lleva todas.",
        "view_table": "Tabla", "view_text": "Texto",
        "csv": "Exportar CSV ({k} filas)", "download": "⬇️ Descargar", "empty": "Ningún resultado.",
        "c_bs": "raíces▶", "c_nbw": "palabras▶", "c_fs": "◀raíces", "c_nfw": "◀palabras",
        "sort_few": "menos ganchos",
        "unique": "solo unívocas", "unique_help": "Un solo patrón de eliminación da gancho por el lado elegido y es una sola letra: el problema tiene una única solución (con «todas»: una en total, delante o detrás).",
        "computing": "Calculando todos los pares de letras…",
        "summary_any": "**{k}** palabras · {b} con gancho detrás ({ub} unívocas) · {f} con gancho delante ({uf} unívocas)",
        "legend": ("**patrón** — la palabra con las letras quitadas como `·` · "
                   "**◀ delante / detrás ▶** — letras que, añadidas a la raíz, dan una palabra del diccionario · "
                   "**notación** — delante‑RAÍZ‑detrás, `Ø` = sin gancho · la letra añadida es siempre distinta de las dos quitadas."),
    },
    "en": {
        "title": "Two-letter hooks",
        "tagline": "Drop two letters, add one at the front or the back — and see whether a dictionary word comes out.",
        "ui": "Interface", "dict": "Dictionary",
        "upload": "…or upload your own .txt", "upload_help": "One word per line, UTF-8.",
        "missing": "`{file}` not found next to the script — upload a dictionary from the sidebar.",
        "loading": "Loading the dictionary…",
        "stats": "**{n}** words · lengths {a}–{b} · `{src}`",
        "tab_word": "One word", "tab_len": "All words of one length",
        "length": "Length", "word": "Word", "word_ph": "e.g. chalk", "random": "🎲 Random",
        "mode": "Letters to drop", "mode_ends": "last two / first two", "mode_any": "any two",
        "only_hooks": "only stems with hooks",
        "not_in_dict": "**{w}** is not in the dictionary — computing anyway.",
        "enter_word": "Type a word or pick one at random.", "no_stems": "No stem has any hook.",
        "c_pattern": "pattern", "c_stem": "stem", "c_front": "◀ front", "c_back": "back ▶",
        "c_n": "#", "c_words": "words", "c_notation": "notation",
        "c_word": "WORD", "c_end": "−end", "c_start": "−start",
        "c_nb": "#▶", "c_nf": "#◀", "c_total": "#hooks",
        "side": "Hooks", "side_all": "all", "side_back": "back", "side_front": "front",
        "side_both": "both sides", "side_none": "none",
        "min_hooks": "Min. hooks", "sort": "Order", "sort_alpha": "alphabetical", "sort_hooks": "most hooks",
        "starts": "Starts with", "ends": "Ends with", "contains": "Contains",
        "rows": "Rows on screen",
        "summary": "**{k}** words · {b} with a back hook · {f} with a front hook · {t} with none",
        "showing": "Showing {k} of {t} — the CSV has them all.",
        "view_table": "Table", "view_text": "Text",
        "csv": "Export CSV ({k} rows)", "download": "⬇️ Download", "empty": "No results.",
        "c_bs": "stems▶", "c_nbw": "words▶", "c_fs": "◀stems", "c_nfw": "◀words",
        "sort_few": "fewest hooks",
        "unique": "unambiguous only", "unique_help": "Only one elimination pattern yields a hook on the chosen side and it is a single letter — the puzzle has one solution (with “all”: one in total, front or back).",
        "computing": "Computing every pair of letters…",
        "summary_any": "**{k}** words · {b} with a back hook ({ub} unambiguous) · {f} with a front hook ({uf} unambiguous)",
        "legend": ("**pattern** — the word with the dropped letters shown as `·` · "
                   "**◀ front / back ▶** — letters that, added to the stem, give a dictionary word · "
                   "**notation** — front‑STEM‑back, `Ø` = no hook · the added letter is always different from the two dropped ones."),
    },
}

st.set_page_config(page_title="Hooks · Haki · Ganchos", page_icon="🪝", layout="wide")

# Tighter page: less top/bottom padding, denser widgets.
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 0.6rem;}
      div[data-testid="stTabs"] {margin-top: -0.6rem;}
      h1 {margin-bottom: 0; padding-bottom: 0;}
    </style>
    """,
    unsafe_allow_html=True,
)

# `use_container_width` is deprecated in Streamlit ≥1.49, `width` missing before.
WIDE = (
    {"width": "stretch"}
    if "width" in inspect.signature(st.dataframe).parameters
    else {"use_container_width": True}
)


# ==========================================================================
# Lexicon
# ==========================================================================

def normalize(line: str) -> str:
    return unicodedata.normalize("NFC", line.strip().lower())


class Lexicon:
    """Words grouped by length, plus a language-aware sort order."""

    __slots__ = ("key", "alphabet", "order", "table", "by_len", "sorted_by_len", "size")

    def __init__(self, key: str, words: set[str], alphabet: str) -> None:
        self.key = key
        seen = set()
        for w in words:
            seen.update(w)
        extra = sorted(seen - set(alphabet))
        self.alphabet: tuple[str, ...] = tuple(alphabet) + tuple(extra)
        self.order = {c: i for i, c in enumerate(self.alphabet)}
        # Translate each letter to a code point in alphabet order so that plain
        # string comparison sorts like the language's alphabet (ą after a, ñ after n…).
        self.table = str.maketrans({c: chr(0x100 + i) for i, c in enumerate(self.alphabet)})
        by_len: dict[int, list[str]] = {}
        for w in words:
            by_len.setdefault(len(w), []).append(w)
        self.by_len = {n: frozenset(v) for n, v in by_len.items()}
        self.sorted_by_len = {
            n: tuple(sorted(v, key=self.sort_key)) for n, v in sorted(by_len.items())
        }
        self.size = len(words)

    def sort_key(self, w: str) -> str:
        return w.translate(self.table)

    def letters(self, chars) -> str:
        """Hook letters as one upper-case string in alphabet order, Ø if none."""
        s = "".join(sorted(chars, key=lambda c: self.order.get(c, 999))).upper()
        return s or EMPTY

    def hooks(self, stem: str) -> tuple[list[str], list[str]]:
        pool = self.by_len.get(len(stem) + 1, frozenset())
        front = [c for c in self.alphabet if c + stem in pool]
        back = [c for c in self.alphabet if stem + c in pool]
        return front, back


@st.cache_resource(show_spinner=False)
def registry() -> dict[str, Lexicon]:
    """Loaded lexicons by key; survives reruns so cache_data tables can find them."""
    return {}


@st.cache_resource(show_spinner=False)
def load_lexicon(key: str, _data: bytes, alphabet: str) -> Lexicon:
    text = _data.decode("utf-8", errors="replace")
    words = {w for w in map(normalize, text.splitlines()) if w and w.isalpha()}
    lex = Lexicon(key, words, alphabet)
    registry()[key] = lex
    return lex


@st.cache_data(show_spinner=False)
def read_file(path: str, _mtime: float) -> bytes:
    return Path(path).read_bytes()


# ==========================================================================
# Computations
# ==========================================================================

def analyse_word(lex: Lexicon, word: str, any_two: bool) -> list[dict]:
    """Every stem obtained by dropping two letters, with its hooks."""
    n = len(word)
    if any_two:
        pairs = list(combinations(range(n), 2))
    else:
        pairs = [(n - 2, n - 1), (0, 1)]
    stems: dict[str, list[str]] = {}
    for i, j in pairs:
        stem = word[:i] + word[i + 1 : j] + word[j + 1 :]
        pattern = "".join(DOT if k in (i, j) else c for k, c in enumerate(word))
        stems.setdefault(stem, []).append(pattern.upper())
    rows = []
    for stem, patterns in stems.items():
        # The added letter must differ from the two dropped ones.
        dropped = set((Counter(word) - Counter(stem)).elements())
        front, back = lex.hooks(stem)
        front = [c for c in front if c not in dropped]
        back = [c for c in back if c not in dropped]
        f, b = lex.letters(front), lex.letters(back)
        words = [c + stem for c in front] + [stem + c for c in back]
        rows.append(
            {
                "pattern": " ".join(patterns),
                "stem": stem.upper(),
                "front": f,
                "back": b,
                "n": len(front) + len(back),
                "notation": f"{f}-{stem.upper()}-{b}",
                "words": ", ".join(w.upper() for w in words),
            }
        )
    return rows


@st.cache_data(show_spinner=False)
def length_table(key: str, n: int) -> pd.DataFrame:
    """All words of length n: stem after dropping the last two letters + back
    hooks, stem after dropping the first two letters + front hooks."""
    lex = registry()[key]
    words = lex.sorted_by_len.get(n, ())
    shorter = lex.by_len.get(n - 1, frozenset())
    end_stems = {w[:-2] for w in words}
    start_stems = {w[2:] for w in words}
    # One pass over the (n-1)-letter words is far cheaper than trying every
    # letter of the alphabet against every stem.
    back: dict[str, list[str]] = {}
    front: dict[str, list[str]] = {}
    for s in shorter:
        head, tail = s[:-1], s[1:]
        if head in end_stems:
            back.setdefault(head, []).append(s[-1])
        if tail in start_stems:
            front.setdefault(tail, []).append(s[0])
    rows = []
    for w in words:
        # The added letter must differ from the two dropped ones.
        b = [c for c in back.get(w[:-2], ()) if c not in w[-2:]]
        f = [c for c in front.get(w[2:], ()) if c not in w[:2]]
        rows.append(
            (
                w.upper(),
                (w[:-2] + DOT * 2).upper(),
                lex.letters(b),
                len(b),
                (DOT * 2 + w[2:]).upper(),
                lex.letters(f),
                len(f),
                len(b) + len(f),
            )
        )
    return pd.DataFrame(
        rows, columns=["word", "end", "back", "nb", "start", "front", "nf", "total"]
    )


@st.cache_data(show_spinner=False)
def any_table(key: str, n: int) -> pd.DataFrame:
    """All words of length n, dropping ANY two letters.

    For each word: how many stems admit a back hook, how many resulting words
    that gives in total, and the list of solutions (same for front hooks).
    A word with exactly one resulting word on a side is unambiguous there:
    the puzzle "drop two letters, add one at that end" has a single answer."""
    lex = registry()[key]
    words = lex.sorted_by_len.get(n, ())
    shorter = lex.by_len.get(n - 1, frozenset())
    back: dict[str, list[str]] = {}
    front: dict[str, list[str]] = {}
    for s in shorter:
        back.setdefault(s[:-1], []).append(s[-1])
        front.setdefault(s[1:], []).append(s[0])
    pairs = list(combinations(range(n), 2))
    rows = []
    for w in words:
        b_stems = b_words = f_stems = f_words = 0
        b_sol: list[str] = []
        f_sol: list[str] = []
        seen: set[str] = set()  # the same stem can come from several position pairs (repeated letters)
        for i, j in pairs:
            stem = w[:i] + w[i + 1 : j] + w[j + 1 :]
            if stem in seen:
                continue
            seen.add(stem)
            b = back.get(stem)
            f = front.get(stem)
            if not b and not f:
                continue
            dropped = (w[i], w[j])
            b = [c for c in b if c not in dropped] if b else []
            f = [c for c in f if c not in dropped] if f else []
            if not b and not f:
                continue
            pattern = "".join(DOT if k in (i, j) else c for k, c in enumerate(w)).upper()
            if b:
                b_stems += 1
                b_words += len(b)
                b_sol.append(f"{pattern}+{lex.letters(b)}")
            if f:
                f_stems += 1
                f_words += len(f)
                f_sol.append(f"{lex.letters(f)}+{pattern}")
        rows.append(
            (w.upper(), b_stems, b_words, "  ".join(b_sol) or EMPTY,
             f_stems, f_words, "  ".join(f_sol) or EMPTY, b_words + f_words)
        )
    return pd.DataFrame(
        rows, columns=["word", "bs", "nb", "back", "fs", "nf", "front", "total"]
    )


# ==========================================================================
# Sidebar: language and dictionary
# ==========================================================================

codes = list(LANGS)
ui = st.sidebar.selectbox("Interface · Interfejs · Interfaz", codes,
                          format_func=lambda c: LANGS[c]["label"], key="ui")
t = T[ui]
dict_code = st.sidebar.selectbox(t["dict"], codes, index=codes.index(ui),
                                 format_func=lambda c: LANGS[c]["label"], key="dict")
uploaded = st.sidebar.file_uploader(t["upload"], type=["txt"], help=t["upload_help"])

alphabet = LANGS[dict_code]["alphabet"]
data: bytes | None = None
source = ""
if uploaded is not None:
    data, source = uploaded.getvalue(), uploaded.name
else:
    path = Path(__file__).with_name(LANGS[dict_code]["file"])
    if path.exists():
        data, source = read_file(str(path), path.stat().st_mtime), path.name

st.title(f"🪝 {t['title']}")
st.caption(t["tagline"])

if data is None:
    st.info(t["missing"].format(file=LANGS[dict_code]["file"]))
    st.stop()

key = hashlib.sha1(data).hexdigest()[:12] + "-" + dict_code
with st.spinner(t["loading"]):
    lex = load_lexicon(key, data, alphabet)
registry().setdefault(key, lex)

# Lengths that make sense: a stem of n-2 ≥ 1 letters and (n-1)-letter words to hook into.
lengths = [n for n in lex.sorted_by_len if n >= 3 and (n - 1) in lex.by_len]
if not lengths:
    st.error(t["empty"])
    st.stop()
st.sidebar.caption(
    t["stats"].format(n=f"{lex.size:,}".replace(",", " "), a=min(lengths), b=max(lengths), src=source)
)
st.sidebar.markdown(t["legend"])


# ==========================================================================
# Tabs
# ==========================================================================

tab_word, tab_len = st.tabs([t["tab_word"], t["tab_len"]])

# --------------------------------------------------------------------------
# 1 · One word
# --------------------------------------------------------------------------

with tab_word:
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.6, 0.8, 1.6, 1.2], vertical_alignment="bottom")
    n_w = c1.select_slider(t["length"], options=lengths,
                           value=5 if 5 in lengths else lengths[0], key="n_w")

    def pick_random() -> None:
        st.session_state["word_in"] = random.choice(lex.sorted_by_len[st.session_state["n_w"]])

    word = normalize(c2.text_input(t["word"], placeholder=t["word_ph"], key="word_in"))
    c3.button(t["random"], on_click=pick_random, **WIDE)
    any_two = c4.radio(t["mode"], [t["mode_ends"], t["mode_any"]], horizontal=True) == t["mode_any"]
    only_hooks = c5.checkbox(t["only_hooks"], value=any_two)

    if not word:
        st.info(t["enter_word"])
    elif len(word) < 3:
        st.warning(t["enter_word"])
    else:
        if word not in lex.by_len.get(len(word), ()):
            st.warning(t["not_in_dict"].format(w=word.upper()))
        rows = analyse_word(lex, word, any_two)
        if only_hooks:
            rows = [r for r in rows if r["n"]]
        if not rows:
            st.warning(t["no_stems"])
        else:
            df = pd.DataFrame(rows)
            left, right = st.columns([3, 2])
            view = df[["pattern", "stem", "front", "back", "n", "words"]].rename(
                columns={
                    "pattern": t["c_pattern"], "stem": t["c_stem"], "front": t["c_front"],
                    "back": t["c_back"], "n": t["c_n"], "words": t["c_words"],
                }
            )
            height = min(38 + 35 * len(view), 640)
            left.dataframe(view, hide_index=True, height=height, **WIDE)
            w_pat = max(len(r["pattern"]) for r in rows)
            right.code(
                "\n".join(f"{r['pattern']:<{w_pat}}   {r['notation']}" for r in rows),
                language=None,
            )

# --------------------------------------------------------------------------
# 2 · All words of one length
# --------------------------------------------------------------------------

with tab_len:
    c0, c1, c2, c3, c4 = st.columns([1.6, 1.2, 1, 0.8, 1], vertical_alignment="bottom")
    any_l = c0.radio(t["mode"], [t["mode_ends"], t["mode_any"]], horizontal=True,
                     key="mode_l") == t["mode_any"]
    n = c1.select_slider(t["length"], options=lengths,
                         value=5 if 5 in lengths else lengths[0], key="n_l")
    sides = [t["side_all"], t["side_back"], t["side_front"], t["side_both"], t["side_none"]]
    side = c2.selectbox(t["side"], sides, key="side_l")
    min_hooks = c3.number_input(t["min_hooks"], 0, 200, 0, step=1)
    order = c4.selectbox(t["sort"], [t["sort_alpha"], t["sort_hooks"], t["sort_few"]])

    f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1.2, 1.4], vertical_alignment="bottom")
    starts = normalize(f1.text_input(t["starts"], key="s_l"))
    ends = normalize(f2.text_input(t["ends"], key="e_l"))
    contains = normalize(f3.text_input(t["contains"], key="c_l"))
    unique = f4.checkbox(t["unique"], value=False, help=t["unique_help"], key="uniq_l")
    top = f5.slider(t["rows"], 200, 20000, 2000, step=200)

    if any_l:
        with st.spinner(t["computing"]):
            df = any_table(lex.key, n)
    else:
        df = length_table(lex.key, n)
    wl = df["word"].str.lower()
    if starts:
        df = df[wl.str.startswith(starts)]
    if ends:
        df = df[wl.str.endswith(ends)]
    if contains:
        df = df[wl.str.contains(contains, regex=False)]
    if side == t["side_back"]:
        df = df[df["nb"] > 0]
    elif side == t["side_front"]:
        df = df[df["nf"] > 0]
    elif side == t["side_both"]:
        df = df[(df["nb"] > 0) & (df["nf"] > 0)]
    elif side == t["side_none"]:
        df = df[df["total"] == 0]
    if unique:  # exactly one resulting word on the chosen side(s)
        # one elimination pattern AND one letter on that side
        ub = (df["nb"] == 1) & (df.get("bs", 1) == 1)
        uf = (df["nf"] == 1) & (df.get("fs", 1) == 1)
        if side == t["side_back"]:
            df = df[ub]
        elif side == t["side_front"]:
            df = df[uf]
        elif side == t["side_both"]:
            df = df[ub & uf]
        else:
            df = df[(ub & (df["nf"] == 0)) | (uf & (df["nb"] == 0))]
    df = df[df["total"] >= min_hooks].reset_index(drop=True)
    if order == t["sort_hooks"]:
        df = df.sort_values(["total", "word"], ascending=[False, True], ignore_index=True)
    elif order == t["sort_few"]:
        df = df[df["total"] > 0].sort_values(["total", "word"], ignore_index=True)

    if df.empty:
        st.warning(t["empty"])
    else:
        v1, v2 = st.columns([1, 4], vertical_alignment="center")
        view = v1.radio("view", [t["view_table"], t["view_text"]], horizontal=True, key="view_l",
                        label_visibility="collapsed")
        k = f"{len(df):,}".replace(",", " ")
        if any_l:
            v2.markdown(
                t["summary_any"].format(
                    k=k,
                    b=f"{(df['nb'] > 0).mean():.0%}", ub=int((df["nb"] == 1).sum()),
                    f=f"{(df['nf'] > 0).mean():.0%}", uf=int((df["nf"] == 1).sum()),
                )
            )
        else:
            v2.markdown(
                t["summary"].format(
                    k=k,
                    b=f"{(df['nb'] > 0).mean():.0%}",
                    f=f"{(df['nf'] > 0).mean():.0%}",
                    t=f"{(df['total'] == 0).mean():.0%}",
                )
            )
        shown = df.head(top)
        if view == t["view_table"] and any_l:
            st.dataframe(
                shown.rename(columns={
                    "word": t["c_word"], "bs": t["c_bs"], "nb": t["c_nbw"], "back": t["c_back"],
                    "fs": t["c_fs"], "nf": t["c_nfw"], "front": t["c_front"], "total": t["c_total"],
                }),
                hide_index=True, height=600, **WIDE,
            )
        elif view == t["view_table"]:
            st.dataframe(
                shown.rename(columns={
                    "word": t["c_word"], "end": t["c_end"], "back": t["c_back"], "nb": t["c_nb"],
                    "start": t["c_start"], "front": t["c_front"], "nf": t["c_nf"], "total": t["c_total"],
                }),
                hide_index=True, height=600, **WIDE,
            )
        elif any_l:
            wb = max(int(shown["back"].str.len().max()), 1)
            st.code(
                "\n".join(
                    f"{w}  ▶ {b:<{wb}}  ◀ {f}".rstrip()
                    for w, b, f in zip(shown["word"], shown["back"], shown["front"])
                ),
                language=None,
            )
        else:
            wb = max(int(shown["back"].str.len().max()), 1)
            st.code(
                "\n".join(
                    f"{w}  {e}-{b:<{wb}}  {f:>{wb}}-{s}".rstrip()
                    for w, e, b, s, f in zip(
                        shown["word"], shown["end"], shown["back"], shown["start"], shown["front"]
                    )
                ),
                language=None,
            )
        if len(df) > top:
            st.caption(t["showing"].format(k=f"{top:,}".replace(",", " "),
                                           t=f"{len(df):,}".replace(",", " ")))
        if st.checkbox(t["csv"].format(k=f"{len(df):,}".replace(",", " ")), key="dl_len"):
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            st.download_button(t["download"], buf.getvalue(),
                               file_name=f"hooks_{dict_code}_{n}.csv", mime="text/csv")
