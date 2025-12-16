"""
Core enrichment engine adapted from the Colab script
"""
import io
import json
import re
import time
import socket
import random
import asyncio
import unicodedata
from typing import Dict, List, Tuple, Set, Optional, Any
from collections import deque
from urllib.parse import urlparse, urljoin

import pandas as pd
import tldextract
import aiohttp
import async_timeout
import requests
import chardet
from bs4 import BeautifulSoup

from backend.config import settings


# -------------------- Constants --------------------
TITLE_LIMIT = 90
SNIPPET_LIMIT = 180

JITTER_RANGE = (0.05, 0.35)

COMPANY_COL_CANDIDATES = [
    "company name", "company", "organisation", "organization",
    "entreprise", "nom entreprise", "raison sociale"
]

# Context categories
CTX_LOCATION = {"country", "pays", "country_code", "iso2", "location", "city", "ville", "region", "state", "province"}
CTX_DESCRIPTION = {"description", "about", "bio", "summary", "notes"}
CTX_SECTOR = {"industry", "sector", "secteur", "naics", "sic"}
CTX_SOCIALS = {"website", "site web", "url", "domain", "homepage", "linkedin", "linkedin url", "profile", "company url"}
CTX_REG = {"siren", "siret", "vat", "vat id", "kvk", "kvk number"}
CONTEXT_KEYWORDS = list(CTX_LOCATION | CTX_DESCRIPTION | CTX_SECTOR | CTX_SOCIALS | CTX_REG)

BLOCK_HOST_PARTS = {
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "tiktok.com",
    "wikipedia.org", "wikidata.org", "crunchbase.com", "rocketreach.co", "apollo.io", "zoominfo.com",
    "glassdoor", "indeed", "ycombinator.com", "angel.co", "medium.com", "blogspot", "news."
}

GENERIC_TOKENS = {
    "group", "holding", "holdings", "company", "co", "inc", "llc", "ltd", "plc", "sa", "sas", "sasu", "spa", "gmbh",
    "bv", "nv", "oy", "ab", "ag", "kg", "srl", "sl", "ltda", "pte", "pty", "limited", "corp", "corporation",
    "international", "global", "solutions", "services", "consulting", "recruitment", "recruiting", "partners",
    "management", "systems", "technologies", "technology", "tech", "digital"
}
for _t in ("hub", "one"):
    if _t in GENERIC_TOKENS:
        GENERIC_TOKENS.remove(_t)

ISO2_TO_GL_HL = {
    "FR": ("fr", "fr"), "BE": ("be", "fr"), "CH": ("ch", "fr"), "CA": ("ca", "en"),
    "US": ("us", "en"), "GB": ("gb", "en"), "IE": ("ie", "en"), "AU": ("au", "en"), "NZ": ("nz", "en"),
    "DE": ("de", "de"), "AT": ("at", "de"), "CH-DE": ("ch", "de"),
    "ES": ("es", "es"), "MX": ("mx", "es"), "AR": ("ar", "es"),
    "IT": ("it", "it"), "NL": ("nl", "nl"), "SE": ("se", "sv"), "NO": ("no", "no"), "DK": ("dk", "da"),
    "PT": ("pt", "pt"), "BR": ("br", "pt"), "PL": ("pl", "pl"), "CZ": ("cz", "cs"), "RO": ("ro", "ro"),
    "HU": ("hu", "hu"), "FI": ("fi", "fi"), "EE": ("ee", "et"), "LT": ("lt", "lt"), "LV": ("lv", "lv"),
    "AE": ("ae", "en"), "IN": ("in", "en"), "SG": ("sg", "en"), "JP": ("jp", "ja")
}

# OpenAI Prompt
SYSTEM_INSTRUCTION = (
    "You will receive one company name with optional context (country/city, industry/sector, description, LinkedIn hints) "
    "and a list of web-search candidate URLs.\n\n"
    "Choose the OFFICIAL domain using these rules:\n"
    "- Priority 1: The exact legal entity's domain.\n"
    "- Priority 2: Localized/country domains for the brand when relevant.\n"
    "- Priority 3: Global/parent domain when relevant.\n"
    "- If no candidate clearly matches but you can confidently identify the official website from your own knowledge or the context, OUTPUT that domain in 'found_domain'.\n"
    "- Use the description and context fields to ensure the domain aligns with the activity.\n"
    "- If still uncertain, set chosen_domain and found_domain to \"null\" and give a short reason.\n\n"
    "Return ONE JSON object with keys: {index, company, chosen_domain, chosen_from_url, found_domain, confidence ∈ [entity,country,group,null], reason}.\n"
    "Notes:\n"
    "- 'chosen_domain' must be from the provided candidates (normalize if needed). Fill 'chosen_from_url' with the URL actually chosen.\n"
    "- 'found_domain' is for a confident domain you know that is NOT in the candidates."
)

STRICT_RETURN_INSTR = (
    "Return ONLY a single JSON object (no prose, no code fences). "
    "Keys: index, company, chosen_domain, chosen_from_url, found_domain, confidence, reason. "
    "Confidence must be one of: entity, country, group, null. "
    "If unsure, set chosen_domain and found_domain to \"null\". Do not add extra keys."
)

# Subdomain and glue patterns
_SUBDOMAIN_STOP = {"www", "m", "en", "fr", "de", "es", "it", "nl", "pt", "pl", "jp"}
_GLUE_PARTS_PAT = re.compile(r"(.*?)(?:it|ai|data|group|groupe|sante|santé|labs)$")

# Brand aliases
BRAND_ALIASES = {
    "dassaultsystemes": {"3ds", "3dsexperience"},
    "reelit": {"reel", "it"},
    "lefigaroclassifieds": {"le", "figaro", "classifieds"},
}

# Legal page patterns
LEGAL_TEXT_PATTERNS = [
    "mentions légales", "mentions legales", "informations légales", "informations legales",
    "legal notice", "legal notices", "impressum", "imprint", "terms", "conditions", "cgu", "cgv",
    "conditions générales", "conditions generales", "informations juridiques", "legal"
]
COMMON_LEGAL_PATHS = [
    "/mentions-legales", "/mentions_legales", "/informations-legales", "/legal", "/legal-notice",
    "/legal-notices", "/impressum", "/imprint", "/cgu", "/cgv", "/terms", "/conditions"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]
HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8,de;q=0.7,nl;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
}

# Regex patterns for registration IDs
SPACE = r"[ \u00A0\u202F]*"
DIG = r"\d"
SIREN_CORE = rf"{DIG}{{3}}{SPACE}{DIG}{{3}}{SPACE}{DIG}{{3}}"
SIRET_CORE = rf"{DIG}{{3}}{SPACE}{DIG}{{3}}{SPACE}{DIG}{{3}}{SPACE}{DIG}{{5}}"
SIREN_RE = re.compile(rf"(?i)\b(?:siren|n°\s*siren|numero\s*siren|num\s*siren)\b[^0-9]{{0,20}}({SIREN_CORE})\b")
SIRET_RE = re.compile(rf"(?i)\b(?:siret|n°\s*siret|numero\s*siret|num\s*siret)\b[^0-9]{{0,20}}({SIRET_CORE})\b")
SIREN_FB = re.compile(rf"\b({SIREN_CORE})\b", re.IGNORECASE)
SIRET_FB = re.compile(rf"\b({SIRET_CORE})\b", re.IGNORECASE)
VAT_RE = re.compile(r"(?i)\b(?:VAT|TVA|USt-IdNr|Partita IVA|BTW|GST)\b[^A-Z0-9]{0,12}([A-Z0-9\-]{8,16})\b")
KVK_RE = re.compile(r"(?i)\b(?:KvK|Kamer van Koophandel)\b[^0-9]{0,12}(\d{6,12})\b")


# -------------------- Helper Functions --------------------
def rand_jitter():
    return random.uniform(*JITTER_RANGE)


def strip_to_domain(u: str) -> str:
    try:
        host = urlparse(u).netloc.lower() if "://" in u else u.lower()
        host = re.sub(r"^www\d*\.", "", host)
        return host.split("/", 1)[0]
    except Exception:
        return ""


def _ascii_lower(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower()


def domain_tokens(domain: str) -> List[str]:
    host = strip_to_domain(domain)
    ext = tldextract.extract(host)
    sld = ext.domain.lower()
    sub = ext.subdomain.lower() if ext.subdomain else ""
    toks = []
    toks += [t for t in re.split(r"[-_\.]", sld) if t]
    if sub:
        toks += [p for p in re.split(r"[-_\.]", sub) if p and p not in _SUBDOMAIN_STOP]
    expanded = []
    for t in toks:
        m = _GLUE_PARTS_PAT.match(t)
        if m and m.group(1):
            root = m.group(1)
            suffix = t[len(root):]
            if root:
                expanded.append(root)
            if suffix:
                expanded.append(suffix)
        else:
            expanded.append(t)
    toks = [x for x in expanded if x]
    return [t for t in toks if t not in GENERIC_TOKENS]


def name_tokens(name: str) -> List[str]:
    n = re.sub(r"[^a-z0-9]+", " ", _ascii_lower(name)).strip()
    toks = [t for t in n.split() if t]
    return [t for t in toks if t not in GENERIC_TOKENS]


def token_string_for_distance_company(company: str) -> str:
    return "".join(name_tokens(company))


def token_string_for_distance_domain(domain: str) -> str:
    return "".join(domain_tokens(domain))


def levenshtein_ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cb = b[j - 1]
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    dist = prev[lb]
    return max(0.0, 1.0 - dist / max(la, lb))


def alias_match(company: str, domain: str) -> bool:
    cname = "".join(name_tokens(company))
    dname_tokens = set(domain_tokens(domain))
    if not cname or not dname_tokens:
        return False
    for base, aliases in BRAND_ALIASES.items():
        if base in cname:
            if any(al in dname_tokens or al in "".join(dname_tokens) for al in aliases):
                return True
    return False


def strong_token_overlap(company: str, domain: str) -> bool:
    nt = set(name_tokens(company))
    dt = set(domain_tokens(domain))
    if not nt or not dt:
        return False
    if nt & dt:
        return True
    return nt.issubset(dt) or dt.issubset(nt)


def ambiguity_count(company: str, candidates: list, chosen_domain: str = None) -> int:
    a = token_string_for_distance_company(company)
    count = 0
    for c in candidates:
        dom = c.get("domain", "")
        if not dom:
            continue
        if chosen_domain and strip_to_domain(dom) == strip_to_domain(chosen_domain):
            continue
        b = token_string_for_distance_domain(dom)
        sim = levenshtein_ratio(a, b)
        overlap = strong_token_overlap(company, dom)
        if sim >= 0.80 or overlap:
            count += 1
    return count


def context_tokens(ctx: dict) -> set:
    want_tokens = set()
    for k, v in (ctx or {}).items():
        kl = str(k).lower()
        if kl in CTX_DESCRIPTION or kl in CTX_SECTOR or kl in CTX_LOCATION:
            for t in name_tokens(str(v)):
                if len(t) >= 3:
                    want_tokens.add(t)
    return want_tokens


def context_match_effect(company: str, ctx: dict, chosen: dict) -> int:
    if not chosen:
        return 0
    if strong_token_overlap(company, chosen.get("domain", "")):
        return 0
    title = (chosen.get("title", "") or "").lower()
    snippet = (chosen.get("snippet", "") or "").lower()
    hay = f"{title} {snippet}"
    want = context_tokens(ctx)
    if not want:
        return 0
    hits = sum(1 for t in want if t in hay)
    miss_ratio = 1.0 - (hits / max(1, len(want)))
    return int(round(min(12, 12 * miss_ratio)))


def context_positive_bonus(ctx: dict, chosen: dict) -> int:
    if not chosen:
        return 0
    title = (chosen.get("title", "") or "").lower()
    snippet = (chosen.get("snippet", "") or "").lower()
    hay = f"{title} {snippet}"
    want = context_tokens(ctx)
    if not want:
        return 0
    hits = sum(1 for t in want if t in hay)
    return 10 if hits >= 2 else (5 if hits == 1 else 0)


def homonym_guard(company: str, domain: str, confidence_label: str) -> bool:
    if confidence_label in ("group", "country"):
        return True
    if alias_match(company, domain):
        return True
    if strong_token_overlap(company, domain):
        return True
    nt = set(name_tokens(company))
    dt = set(domain_tokens(domain))
    a = "".join(nt)
    b = "".join(dt)
    if not a or not b:
        return False
    ratio = levenshtein_ratio(a, b)
    if len(nt) <= 2:
        return ratio >= 0.60
    return ratio >= 0.70


def safe_json(v):
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "null") else ""


def guess_gl_hl(ctx: dict):
    code = ""
    for k, v in (ctx or {}).items():
        kl = str(k).lower()
        if "country_code" in kl or kl == "iso2":
            code = str(v).strip().upper()
            break
        if kl == "country" or "pays" in kl:
            name = str(v).strip().lower()
            m = {
                "france": "FR", "belgium": "BE", "switzerland": "CH", "canada": "CA", "united states": "US", "usa": "US",
                "united kingdom": "GB", "uk": "GB", "ireland": "IE", "australia": "AU", "new zealand": "NZ",
                "germany": "DE", "austria": "AT", "spain": "ES", "mexico": "MX", "argentina": "AR",
                "italy": "IT", "netherlands": "NL", "sweden": "SE", "norway": "NO", "denmark": "DK",
                "portugal": "PT", "brazil": "BR", "poland": "PL", "czech republic": "CZ", "romania": "RO",
                "hungary": "HU", "finland": "FI", "estonia": "EE", "lithuania": "LT", "latvia": "LV",
                "united arab emirates": "AE", "india": "IN", "singapore": "SG", "japan": "JP", "switzerland (de)": "CH-DE"
            }
            code = m.get(name, "")
            break
    if code and code in ISO2_TO_GL_HL:
        return ISO2_TO_GL_HL[code]
    return (None, None)


def extract_first_json(txt: str):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.DOTALL).strip()
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    return m.group(0) if m else t


def filter_candidates(results):
    seen = set()
    out = []
    for it in results:
        link = it.get("link") or it.get("url") or it.get("formattedUrl") or ""
        title = (it.get("title", "") or "")[:TITLE_LIMIT]
        snippet = (it.get("snippet", "") or it.get("description", "") or "")[:SNIPPET_LIMIT]
        host = strip_to_domain(link)
        if not host:
            continue
        if any(bad in host for bad in BLOCK_HOST_PARTS):
            continue
        if host in seen:
            continue
        seen.add(host)
        out.append({"url": link, "domain": host, "title": title, "snippet": snippet})
    return out


def dns_ok(domain: str, timeout=None) -> bool:
    if not settings.ENABLE_DNS_CHECK:
        return True
    try:
        timeout = timeout or settings.DNS_TIMEOUT_SEC
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(strip_to_domain(domain))
        return True
    except Exception:
        return False


# -------------------- Legal Pages & Registration --------------------
def _random_headers():
    h = dict(HEADERS_BASE)
    h["User-Agent"] = random.choice(USER_AGENTS)
    return h


def _decode_response(resp: requests.Response) -> str:
    enc = resp.encoding or chardet.detect(resp.content).get("encoding") or "utf-8"
    return resp.content.decode(enc, errors="replace")


def fetch_get(url: str, timeout: int = 10) -> tuple:
    try:
        r = requests.get(url, headers=_random_headers(), timeout=timeout, allow_redirects=True)
        if "text/html" in (r.headers.get("Content-Type", "").lower()):
            return r.status_code, _decode_response(r)
    except Exception:
        pass
    return 0, ""


def find_legal_links_in_html(html_text: str, base_url: str) -> List[str]:
    out = []
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = (a.get_text() or "").strip().lower()
            href = (a["href"] or "").strip()
            if any(p in text for p in LEGAL_TEXT_PATTERNS) or any(
                    p in href.lower() for p in ["legal", "impressum", "mentions", "conditions", "terms"]):
                out.append(urljoin(base_url, href))
    except Exception:
        pass
    try:
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        for p in COMMON_LEGAL_PATHS:
            out.append(base + p)
            out.append(base + p + "/")
    except Exception:
        pass
    uniq, seen = [], set()
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq[:12]


def _digits_only(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def luhn_check(number_str: str) -> bool:
    digits = [int(d) for d in number_str if d.isdigit()]
    if not digits:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d2 = d * 2
            if d2 > 9:
                d2 -= 9
            checksum += d2
        else:
            checksum += d
    return (checksum % 10) == 0


def extract_reg_ids(text: str) -> dict:
    out = {"siren": set(), "siret": set(), "vat": set(), "kvk": set()}
    if not text:
        return out
    tnorm = text.replace("\u00A0", " ").replace("\u202F", " ")
    for m in SIRET_RE.findall(tnorm) + SIRET_FB.findall(tnorm):
        d = _digits_only(m)
        if len(d) == 14 and luhn_check(d[:9]):
            out["siret"].add(d)
    for m in SIREN_RE.findall(tnorm) + SIREN_FB.findall(tnorm):
        d = _digits_only(m)
        if len(d) == 9 and luhn_check(d):
            out["siren"].add(d)
    if out["siret"] and not out["siren"]:
        for siret in out["siret"]:
            s9 = siret[:9]
            if luhn_check(s9):
                out["siren"].add(s9)
    for m in VAT_RE.findall(tnorm):
        out["vat"].add(m.strip().upper())
    for m in KVK_RE.findall(tnorm):
        out["kvk"].add(_digits_only(m))
    return out


def crawl_registration_for_domain(domain: str, timeout_per_req=10, hard_cap_pages=12) -> dict:
    res = {"domain": domain, "found": {"siren": set(), "siret": set(), "vat": set(), "kvk": set()}, "legal_urls": []}
    base = f"https://{strip_to_domain(domain)}"
    status, html_home = fetch_get(base, timeout=timeout_per_req)
    cand_urls = []
    if html_home:
        cand_urls += find_legal_links_in_html(html_home, base)
    for p in COMMON_LEGAL_PATHS:
        cand_urls.append(base + p)
        cand_urls.append(base + p + "/")
    seen, uniq = set(), []
    for u in cand_urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
        if len(uniq) >= hard_cap_pages:
            break
    res["legal_urls"] = uniq
    if base not in uniq:
        uniq.append(base)
    for u in uniq:
        st, html = fetch_get(u, timeout=timeout_per_req)
        if not html:
            continue
        ids = extract_reg_ids(html)
        for k in res["found"].keys():
            res["found"][k].update(ids.get(k, set()))
    return res


def normalize_reg_context(ctx: dict) -> dict:
    exp = {"siren": set(), "siret": set(), "vat": set(), "kvk": set()}
    for k, v in (ctx or {}).items():
        kl = str(k).lower()
        vs = str(v).strip()
        if not vs:
            continue
        if kl in ("siren",):
            d = _digits_only(vs)
            if len(d) == 9:
                exp["siren"].add(d)
        elif kl in ("siret",):
            d = _digits_only(vs)
            if len(d) == 14:
                exp["siret"].add(d)
            if len(d) >= 9:
                exp["siren"].add(d[:9])
        elif kl in ("vat", "vat id"):
            exp["vat"].add(vs.upper())
        elif kl in ("kvk", "kvk number"):
            d = _digits_only(vs)
            if len(d) >= 6:
                exp["kvk"].add(d)
    return exp


def registration_match_found(expected: dict, found: dict) -> bool:
    if expected["siren"] & found["siren"]:
        return True
    if expected["siret"] & found["siret"]:
        return True
    for s in expected["siren"]:
        for siret in found["siret"]:
            if s == siret[:9]:
                return True
    for siret in expected["siret"]:
        for s2 in found["siren"]:
            if s2 == siret[:9]:
                return True
    for v in expected["vat"]:
        if len(v) >= 8 and any(v in f or f in v for f in found["vat"]):
            return True
    for k in expected["kvk"]:
        if any((k in f or f in k) for f in found["kvk"]):
            return True
    return False


# -------------------- Async HTTP Helpers --------------------
def should_retry(status):
    return status in (429, 500, 502, 503, 504)


async def post_json_with_retries(session: aiohttp.ClientSession, url, headers, body, tag="req"):
    last_payload = None
    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            async with async_timeout.timeout(settings.HTTP_CONNECT_TIMEOUT + settings.HTTP_READ_TIMEOUT):
                async with session.post(
                        url, headers=headers, json=body,
                        timeout=aiohttp.ClientTimeout(
                            total=settings.HTTP_CONNECT_TIMEOUT + settings.HTTP_READ_TIMEOUT,
                            connect=settings.HTTP_CONNECT_TIMEOUT,
                            sock_read=settings.HTTP_READ_TIMEOUT
                        )
                ) as resp:
                    status = resp.status
                    try:
                        payload = await resp.json()
                    except Exception:
                        payload = await resp.text()
                    if isinstance(payload, dict):
                        last_payload = payload
                    if status == 200 or not should_retry(status):
                        return status, payload
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError, aiohttp.ClientPayloadError):
            pass
        await asyncio.sleep((settings.BACKOFF_BASE ** (attempt - 1)) + rand_jitter())
    return None, last_payload


# RPS Limiter
class RPSLimiter:
    def __init__(self, rps: int):
        self.rps = max(1, int(rps))
        self.window = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            while self.window and now - self.window[0] >= 1.0:
                self.window.popleft()
            if len(self.window) >= self.rps:
                delay = 1.0 - (now - self.window[0])
                await asyncio.sleep(max(0.0, delay))
                now = time.monotonic()
                while self.window and now - self.window[0] >= 1.0:
                    self.window.popleft()
            self.window.append(time.monotonic())


# -------------------- OpenAI & SERP Calls --------------------
def openai_headers():
    h = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
    if settings.OPENAI_ORG_ID:
        h["OpenAI-Organization"] = settings.OPENAI_ORG_ID
    return h


async def openai_preflight(session: aiohttp.ClientSession) -> bool:
    body = {
        "model": settings.OPENAI_MODEL, "temperature": 0,
        "messages": [
            {"role": "system", "content": "Reply with only this JSON: {\"ok\":true}"},
            {"role": "user", "content": "ping"}
        ]
    }
    status, data = await post_json_with_retries(session, settings.OPENAI_URL, openai_headers(), body,
                                                 tag="openai-preflight")
    if status != 200 or not isinstance(data, dict) or "choices" not in data or not data["choices"]:
        return False
    return True


def build_user_prompt(index: int, company: str, context: dict, candidates: list) -> str:
    lines = [f"index={index}", f'name="{company}"']
    if context:
        ctx_bits = []
        for k, v in context.items():
            vs = safe_json(v)
            if vs:
                ctx_bits.append(f'{k}="{vs}"')
        if ctx_bits:
            lines.append("context: " + " ; ".join(ctx_bits))
    lines.append("\nCandidates:")
    for i, c in enumerate(candidates[:settings.MAX_CANDIDATES_PER_COMPANY]):
        title = (c.get("title", "") or "")[:TITLE_LIMIT]
        snip = (c.get("snippet", "") or "")[:SNIPPET_LIMIT]
        lines.append(f'[{i}] url="{c.get("url", "")}" title="{title}" snippet="{snip}"')
    return "\n".join(lines)


async def openai_choose(session: aiohttp.ClientSession, index: int, company: str, context: dict, candidates: list):
    body = {
        "model": settings.OPENAI_MODEL, "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION + "\n" + STRICT_RETURN_INSTR},
            {"role": "user", "content": build_user_prompt(index, company, context, candidates)}
        ]
    }
    status, data = await post_json_with_retries(session, settings.OPENAI_URL, openai_headers(), body,
                                                 tag="openai-choose")
    if status != 200 or not isinstance(data, dict) or "choices" not in data or not data["choices"]:
        raise RuntimeError(f"OpenAI choose failed — HTTP {status} / {str(data)[:800]}")
    txt = (data["choices"][0]["message"]["content"] or "").strip()
    try:
        obj = json.loads(extract_first_json(txt))
        return {
            "chosen_domain": str(obj.get("chosen_domain") or "null"),
            "chosen_from_url": str(obj.get("chosen_from_url") or obj.get("chosen_url") or ""),
            "found_domain": str(obj.get("found_domain") or "null"),
            "confidence": str(obj.get("confidence") or "null").lower(),
            "reason": str(obj.get("reason") or "")
        }
    except Exception:
        return {"chosen_domain": "null", "chosen_from_url": "", "found_domain": "null", "confidence": "null",
                "reason": "openai-parse-fail"}


async def serper_search(session: aiohttp.ClientSession, limiter: RPSLimiter, query: str, ctx: dict, num: int = 10):
    await limiter.acquire()
    gl, hl = guess_gl_hl(ctx)
    body = {"q": query, "num": max(1, min(100, int(num)))}
    if gl:
        body["gl"] = gl
    if hl:
        body["hl"] = hl
    headers = {"Content-Type": "application/json", "X-API-KEY": settings.SERPER_API_KEY}
    status, data = await post_json_with_retries(session, settings.SERPER_SEARCH_URL, headers, body, tag="serper-search")
    if status != 200 or data is None:
        return []
    if isinstance(data, dict):
        results = data.get("organic") or []
        return results if isinstance(results, list) else []
    return []


# -------------------- CSV & Data Helpers --------------------
def find_company_col(df: pd.DataFrame) -> str:
    low = {c.lower(): c for c in df.columns}
    for cand in COMPANY_COL_CANDIDATES:
        if cand in low:
            return low[cand]
    for c in df.columns:
        lc = c.lower()
        if "company" in lc or "entreprise" in lc or "raison" in lc:
            return c
    raise ValueError("No 'company name' column found.")


def detect_context_columns(df: pd.DataFrame):
    cols = []
    for c in df.columns:
        cl = c.lower().strip()
        for k in CONTEXT_KEYWORDS:
            if k in cl:
                cols.append(c)
                break
    return cols


def init_output(df):
    if "URL" not in df.columns:
        df["URL"] = ""
    # Add debug columns
    add_cols = ("URL_confidence_score", "URL_ambiguity", "URL_cand_count",
                "URL_reg_match", "URL_reg_ids_found", "URL_debug", "URL_found_domain")
    for col in add_cols:
        if col not in df.columns:
            df[col] = ""
    return df


# -------------------- Main Enrichment Class --------------------
class EnrichmentEngine:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.search_cache = {}
        self.llm_cache = {}
        self.openai_unhealthy = asyncio.Event()

    async def update_progress(self, current: int, total: int, message: str = ""):
        if self.progress_callback:
            await self.progress_callback(current, total, message)

    async def legal_check_for_candidates(self, candidates: list, reg_expected: dict):
        loop = asyncio.get_running_loop()
        results = {}
        tasks = []
        for c in candidates[:settings.MAX_CANDIDATES_PER_COMPANY]:
            dom = c.get("domain", "")
            if not dom:
                continue
            tasks.append(loop.run_in_executor(None, crawl_registration_for_domain, dom))
        done = await asyncio.gather(*tasks, return_exceptions=True)
        for item in done:
            try:
                if isinstance(item, dict) and "domain" in item:
                    results[item["domain"]] = item
            except Exception:
                pass
        best = None
        for dom, data in results.items():
            if registration_match_found(reg_expected, data.get("found",
                                                                {"siren": set(), "siret": set(), "vat": set(),
                                                                 "kvk": set()})):
                best = (dom, data)
                break
        return results, best

    async def process_row(self, idx, row, session_serp, session_oa, serp_limiter, sem_serp, sem_oa,
                          out_df, company_col, context_cols, processed_count, total_count):
        # Check if URL already exists (avoid Series ambiguity)
        if pd.notna(row.get("URL")) and str(row["URL"]).strip():
            return

        company = str(row[company_col]).strip() if pd.notna(row[company_col]) else ""
        if not company:
            out_df.at[idx, "URL"] = ""
            return

        if self.openai_unhealthy.is_set():
            return

        ctx = {c: row[c] for c in context_cols if pd.notna(row.get(c, ""))}
        non_reg_ctx_bits = []
        for k, v in ctx.items():
            kl = str(k).lower()
            if kl in CTX_REG:
                continue
            vs = safe_json(v)
            if vs:
                non_reg_ctx_bits.append(vs)
        q = company + " official website"
        if non_reg_ctx_bits:
            q = company + " " + " ".join(non_reg_ctx_bits[:3]) + " official website"

        def search_cache_key(q, ctx, num, page):
            gl, hl = guess_gl_hl(ctx)
            return (q, gl, hl, num, page)

        # SERP candidates
        candidates = []
        try:
            tried = set()
            queries = [
                q,
                company + " website",
                f'"{company}" website',
                f'"{company}" official website',
                f"{company} site web",
                f"{company} site officiel",
            ]
            for qtry in queries:
                key = search_cache_key(qtry, ctx, settings.SEARCH_RESULTS_PER_CALL, 1)
                if key in tried:
                    continue
                tried.add(key)

                if key in self.search_cache:
                    cand = self.search_cache[key]
                else:
                    async with sem_serp:
                        results = await serper_search(session_serp, serp_limiter, qtry, ctx,
                                                      num=settings.SEARCH_RESULTS_PER_CALL)
                    cand = filter_candidates(results)
                    self.search_cache[key] = cand

                if cand:
                    have = {c["domain"] for c in candidates}
                    for c in cand:
                        if c["domain"] not in have:
                            candidates.append(c)
                            have.add(c["domain"])

                if len(candidates) >= settings.MAX_CANDIDATES_PER_COMPANY:
                    candidates = candidates[:settings.MAX_CANDIDATES_PER_COMPANY]
                    break
        except Exception:
            candidates = []

        # LLM choose
        try:
            lkey = (company, tuple(sorted((str(k), str(ctx[k])) for k in ctx)),
                    tuple((c.get("url", ""), c.get("domain", "")) for c in candidates[:settings.MAX_CANDIDATES_PER_COMPANY]))
            if lkey in self.llm_cache:
                g = self.llm_cache[lkey]
            else:
                async with sem_oa:
                    g = await openai_choose(session_oa, idx, company, ctx, candidates)
                self.llm_cache[lkey] = g
        except Exception as e:
            self.openai_unhealthy.set()
            raise RuntimeError(f"OpenAI error: {str(e)[:1200]}")

        dom_raw = (g.get("chosen_domain") or "null").strip().lower()
        conf_label = (g.get("confidence") or "null").strip().lower()
        reason = (g.get("reason") or "").strip()
        src_url = (g.get("chosen_from_url") or "").strip()
        found_dom = (g.get("found_domain") or "null").strip().lower()

        # Recovery
        if (dom_raw in ("null", "none", "") or not strip_to_domain(dom_raw)) and src_url:
            dom_raw = strip_to_domain(src_url)
        if (dom_raw in ("null", "none", "") or not strip_to_domain(dom_raw)) and reason:
            m = re.search(r'https?://[^\s"\'\)]+', reason)
            if m:
                src_url = src_url or m.group(0)
                dom_raw = strip_to_domain(src_url)

        # Accept LLM-provided found_domain
        used_llm_found = False
        if (dom_raw in ("null", "none", "") or not strip_to_domain(dom_raw)) and found_dom not in ("null", "", "none"):
            if strip_to_domain(found_dom):
                dom_raw = strip_to_domain(found_dom)
                conf_label = "entity"
                used_llm_found = True
                if reason:
                    reason = (reason + " | LLM-direct-found").strip(" |")
                else:
                    reason = "LLM-direct-found"

        # Decide acceptance + score
        if dom_raw in ("null", "none", ""):
            final_domain = ""
            numeric_score = ""
            ambiguity = 0
            chosen_obj = {}
        else:
            d = strip_to_domain(dom_raw)
            chosen_obj = next((c for c in candidates if strip_to_domain(c.get("domain", "")) == d),
                              {}) if candidates else {}
            if (not d) or (settings.ENABLE_DNS_CHECK and not dns_ok(d)) or (
                    not homonym_guard(company, d, conf_label)):
                final_domain = ""
                numeric_score = ""
                ambiguity = 0
            else:
                final_domain = d
                base_map = {"entity": 95, "country": 78, "group": 65, "null": 50}
                base_score = base_map.get(conf_label, 50)
                ambiguity = ambiguity_count(company, candidates, chosen_domain=d)
                total_considered = max(1, min(len(candidates), settings.MAX_CANDIDATES_PER_COMPANY))
                amb_ratio = min(1.0, ambiguity / total_considered)
                brand_tokens = len(name_tokens(company))
                amb_cap = 12 if brand_tokens <= 2 else 20
                amb_penalty = int(round(amb_cap * amb_ratio))
                ctx_pen = context_match_effect(company, ctx, chosen_obj)
                ctx_bonus = context_positive_bonus(ctx, chosen_obj)
                numeric_score = max(1, min(100, base_score - amb_penalty - ctx_pen + ctx_bonus))
                if used_llm_found and numeric_score < 75:
                    numeric_score = 75

        # Registration legal check
        reg_expected = normalize_reg_context({k: v for k, v in ctx.items() if str(k).lower() in CTX_REG})
        best_reg_match_domain = ""
        found_ids_str = ""
        if any(reg_expected.values()) and (candidates or final_domain not in ("", "")):
            to_check = candidates.copy()
            if final_domain not in ("", ""):
                if not any(strip_to_domain(c.get("domain", "")) == final_domain for c in to_check):
                    to_check.append({"domain": final_domain, "url": f"https://{final_domain}"})
            reg_results, best = await self.legal_check_for_candidates(to_check, reg_expected)
            if best:
                best_reg_match_domain = strip_to_domain(best[0])
                final_domain = best_reg_match_domain
                numeric_score = 100
                found = best[1].get("found", {})
                found_ids_str = ";".join(sorted(list(
                    found.get("siren", set()) | found.get("siret", set()) | found.get("vat", set()) | found.get("kvk",
                                                                                                                 set())
                )))
                if not reason:
                    reason = "registration-match"
                conf_label = "entity"

        # Write row
        out_df.at[idx, "URL"] = final_domain
        out_df.at[idx, "URL_confidence_score"] = numeric_score if final_domain != "" else ""
        out_df.at[idx, "URL_ambiguity"] = ambiguity
        out_df.at[idx, "URL_cand_count"] = len(candidates)
        out_df.at[idx, "URL_reg_match"] = "yes" if best_reg_match_domain else "no"
        out_df.at[idx, "URL_reg_ids_found"] = found_ids_str
        out_df.at[idx, "URL_debug"] = json.dumps(
            {"chosen_obj_title": chosen_obj.get("title", ""), "chosen_obj_snippet": chosen_obj.get("snippet", "")},
            ensure_ascii=False)
        out_df.at[idx, "URL_found_domain"] = found_dom if found_dom not in ("null", "none") else ""

        # Update progress
        await self.update_progress(processed_count[0] + 1, total_count,
                                   f"Processing: {company[:30]}{'...' if len(company) > 30 else ''}")
        processed_count[0] += 1

    async def enrich_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main enrichment method"""
        company_col = find_company_col(df)
        context_cols = detect_context_columns(df)

        out_df = init_output(df.copy())

        # Preflight OpenAI
        async with aiohttp.ClientSession() as s_pre:
            ok = await openai_preflight(s_pre)
            if not ok:
                raise RuntimeError("OpenAI preflight failed")

        # Find rows without URLs (avoid Series ambiguity)
        pending_indices = [i for i, r in out_df.iterrows() if
                           not (pd.notna(r.get("URL")) and str(r["URL"]).strip())]
        total_count = len(pending_indices)

        await self.update_progress(0, total_count, "Starting enrichment...")

        serp_limiter = RPSLimiter(settings.SERP_MAX_RPS)
        sem_serp = asyncio.Semaphore(settings.SERP_CONCURRENCY)
        sem_oa = asyncio.Semaphore(settings.OPENAI_CONCURRENCY)

        connector_serp = aiohttp.TCPConnector(limit=settings.SERP_CONCURRENCY * 2, ssl=False)
        connector_oa = aiohttp.TCPConnector(limit=settings.OPENAI_CONCURRENCY * 2, ssl=False)

        processed_count = [0]

        async with aiohttp.ClientSession(connector=connector_serp) as session_serp, \
                aiohttp.ClientSession(connector=connector_oa) as session_oa:

            tasks = []
            for idx in pending_indices:
                if self.openai_unhealthy.is_set():
                    break
                row = out_df.loc[idx]
                tasks.append(asyncio.create_task(self.process_row(
                    idx, row, session_serp, session_oa, serp_limiter, sem_serp, sem_oa,
                    out_df, company_col, context_cols, processed_count, total_count
                )))

            try:
                for fut in asyncio.as_completed(tasks):
                    await fut
                    if self.openai_unhealthy.is_set():
                        for t in tasks:
                            if not t.done():
                                t.cancel()
                        break
            except asyncio.CancelledError:
                pass

        await self.update_progress(total_count, total_count, "Enrichment complete!")
        return out_df
