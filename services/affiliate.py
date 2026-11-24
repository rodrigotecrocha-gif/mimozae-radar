import hashlib
import html as html_lib
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

_PROMOBIT_LOCK = threading.Lock()
_PROMOBIT_COOLDOWN_UNTIL = 0.0
_RESOLVED_URL_CACHE = {}
_DISK_CACHE_LOADED = False
_CACHE_LOCK = threading.Lock()
_DISK_CACHE_PATH = os.path.join(os.path.expanduser("~"), ".mimozae_radar", "resolved_links.json")


def _ensure_disk_cache_loaded():
    global _DISK_CACHE_LOADED
    if _DISK_CACHE_LOADED:
        return
    _DISK_CACHE_LOADED = True
    try:
        if os.path.exists(_DISK_CACHE_PATH):
            with open(_DISK_CACHE_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                _RESOLVED_URL_CACHE.update(saved)
    except Exception:
        pass


def _save_disk_cache():
    try:
        os.makedirs(os.path.dirname(_DISK_CACHE_PATH), exist_ok=True)
        trimmed = dict(list(_RESOLVED_URL_CACHE.items())[-3000:])
        with open(_DISK_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False)
    except Exception:
        pass

_AFF_SESSION = None
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
}

REDIRECT_DOMAINS = (
    "promobit.com",
    "pelando.com",
    "pechinchou.com",
    "meli.la",
    "s.shopee.com",
    "shp.ee",
    "shope.ee",
    "click.linksynergy.com",
    "awin1.com",
    "lomadee.com",
    "onelink.shein.com",
    "onelink.me",
    "bit.ly",
    "t.co",
    "tinyurl",
    "tidd.ly",
)


def _get_aff_session() -> requests.Session:
    global _AFF_SESSION
    if _AFF_SESSION is None:
        _AFF_SESSION = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=1)
        _AFF_SESSION.mount("https://", adapter)
        _AFF_SESSION.mount("http://", adapter)
    return _AFF_SESSION


def identify_store(url: str) -> str:
    url_lower = (url or "").lower()
    if any(k in url_lower for k in ("mercadolivre.com", "mercadolibre.com", "meli.la")):
        return "Mercado Livre"
    if any(k in url_lower for k in ("shopee.com", "s.shopee.com", "shp.ee", "shope.ee")):
        return "Shopee"
    if "shein.com" in url_lower:
        return "Shein"
    if any(k in url_lower for k in ("amazon.com", "link.amazon", "amzn.to")):
        return "Amazon Brasil"
    if any(k in url_lower for k in ("magazineluiza.com", "magazinevoce.com")):
        return "Magazine Luiza"
    if "casasbahia.com" in url_lower:
        return "Casas Bahia"
    if "aliexpress.com" in url_lower:
        return "AliExpress"
    if "dafiti.com" in url_lower:
        return "Dafiti"
    return "Loja Parceira"


def _unwrap_deeplink_wrappers(url: str) -> str:
    """Extrai o link real embutido em wrappers de afiliados/challenge (LinkSynergy, Awin, Shein risk/challenge)."""
    if not url:
        return ""
    current = html_lib.unescape(url.strip())
    for _ in range(3):
        parsed = urlparse(current)
        qs = parse_qs(parsed.query)
        extracted = None

        if "click.linksynergy.com" in parsed.netloc.lower() and "murl" in qs:
            extracted = qs["murl"][0]
        elif "shein.com" in parsed.netloc.lower() and "/risk/challenge" in parsed.path and "redirection" in qs:
            extracted = qs["redirection"][0]
        elif any(d in parsed.netloc.lower() for d in ("awin1.com", "lomadee.com", "admitad", "redirect")):
            for key in ("ued", "murl", "url", "dest", "u"):
                if key in qs and qs[key][0].startswith("http"):
                    extracted = qs[key][0]
                    break

        if not extracted:
            break
        decoded = unquote(extracted)
        # Shein ocasionalmente aplica double encoding (%252C -> %2C)
        if "%3A%2F%2F" in decoded or "%2F" in decoded[:25]:
            decoded = unquote(decoded)
        current = decoded
    return current


def _extract_ml_product_from_social(html_text: str) -> str:
    """Extrai o link limpo de produto (/p/MLB..., /up/MLBU..., /MLB-...) dentro de /social/promobit."""
    if not html_text:
        return ""
    # Preferir links diretos de produto do Mercado Livre, evitando /c/ categorias e scripts
    candidates = re.findall(
        r'https://(?:www|produto)\.mercadolivre\.com\.br/[^"\'<>\s\\]+?(?:/p/MLB\d+|/up/MLBU\d+|MLB-\d+-[^"\'<>\s\\?#]+)',
        html_text,
    )
    for c in candidates:
        c_clean = html_lib.unescape(c)
        if any(bad in c_clean for bad in ("/c/", "/assinaturas/", "/v3/", "/social/", "/security.js")):
            continue
        return c_clean

    soup = BeautifulSoup(html_text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(bad in href for bad in ("/c/", "/assinaturas/", "/social/")):
            continue
        if "/p/MLB" in href or "/up/MLBU" in href or "/MLB-" in href:
            return href.split("?")[0].split("#")[0]
    return ""


def resolve_unshorten_url(url: str, max_depth: int = 5) -> str:
    """Resolve redirecionadores (Promobit, meli.la, s.shopee, onelink.shein, wrappers) sem deletar ofertas em 429."""
    global _PROMOBIT_COOLDOWN_UNTIL
    if not url:
        return ""

    with _CACHE_LOCK:
        _ensure_disk_cache_loaded()
        if url in _RESOLVED_URL_CACHE:
            return _RESOLVED_URL_CACHE[url]

    sess = _get_aff_session()
    current = _unwrap_deeplink_wrappers(url)

    for _ in range(max_depth):
        low = current.lower()

        if "promobit.com" not in low and "pelando.com" not in low and "pechinchou.com" not in low:
            if "mercadolivre.com" in low and ("/p/mlb" in low or "/up/mlbu" in low or "/mlb-" in low):
                break
            if "shopee.com" in low and ("/product/" in low or "/opaanlp/" in low or re.search(r"-i\.\d+\.\d+", low)):
                break
            if "shein.com" in low and "/risk/" not in low and "onelink.shein" not in low and ("-p-" in low or ".html" in low):
                break

        try:
            # 1. Promobit /Redirect/to/{id}/ (com lock suave + proteção contra rate limit 429)
            if "promobit.com" in low and "/redirect/" in low:
                if time.time() < _PROMOBIT_COOLDOWN_UNTIL:
                    return current
                with _PROMOBIT_LOCK:
                    if time.time() < _PROMOBIT_COOLDOWN_UNTIL:
                        return current
                    time.sleep(0.15)
                    r = sess.get(current, headers=_DEFAULT_HEADERS, timeout=4, allow_redirects=False)

                if r.status_code == 429 or "Acesso Bloqueado" in r.text:
                    _PROMOBIT_COOLDOWN_UNTIL = time.time() + 120
                    return current

                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                    loc = r.headers["Location"]
                    if "/messenger/" in loc or "whatsapp" in loc.lower():
                        return "__SPAM__"
                    current = _unwrap_deeplink_wrappers(loc)
                    continue

                if r.status_code != 200:
                    return current

                m_js = re.search(r"l\s*=\s*['\"](https?://[^'\"]+)['\"]", r.text)
                m_href = re.search(r"<a[^>]+href=['\"](https?://[^'\"]+)['\"][^>]*>\s*clique aqui", r.text, re.I)
                target = (m_js.group(1) if m_js else (m_href.group(1) if m_href else "")).strip()
                if "/messenger/" in target or "whatsapp" in target.lower():
                    return "__SPAM__"
                if not target:
                    return current
                current = _unwrap_deeplink_wrappers(target)
                continue

            # 2. Mercado Livre meli.la e /social/promobit
            if "meli.la" in low:
                r = sess.get(current, headers=_DEFAULT_HEADERS, timeout=4, allow_redirects=False)
                loc = r.headers.get("Location", "")
                if not loc:
                    r2 = sess.get(current, headers=_DEFAULT_HEADERS, timeout=5, allow_redirects=True)
                    loc = r2.url
                    if "/social/" in loc:
                        extracted = _extract_ml_product_from_social(r2.text)
                        if extracted:
                            current = extracted
                            break
                if loc:
                    current = _unwrap_deeplink_wrappers(loc)
                    continue
                break

            if "mercadolivre.com" in low and "/social/" in low:
                r = sess.get(current, headers=_DEFAULT_HEADERS, timeout=5, allow_redirects=True)
                extracted = _extract_ml_product_from_social(r.text)
                if extracted:
                    current = extracted
                break

            # 3. Shein OneLink (ler só 302 Location antes de cair no challenge)
            if "onelink.shein.com" in low or "onelink.me" in low:
                r = sess.get(current, headers=_DEFAULT_HEADERS, timeout=4, allow_redirects=False)
                loc = r.headers.get("Location", "")
                if loc:
                    current = _unwrap_deeplink_wrappers(loc)
                    continue
                break

            # 4. Encurtadores Shopee e genéricos (s.shopee.com.br, shp.ee, shope.ee, bit.ly, etc.)
            if any(k in low for k in ("s.shopee.com", "shp.ee", "shope.ee", "bit.ly", "t.co", "tinyurl", "tidd.ly")):
                r = sess.get(current, headers=_DEFAULT_HEADERS, timeout=4, allow_redirects=False)
                loc = r.headers.get("Location", "")
                if loc and loc.startswith("http"):
                    current = _unwrap_deeplink_wrappers(loc)
                    continue
                r2 = sess.get(current, headers=_DEFAULT_HEADERS, timeout=4, allow_redirects=True)
                if r2.url and r2.url != current:
                    current = _unwrap_deeplink_wrappers(r2.url)
                    continue
                break

            break
        except Exception:
            break

    final = _unwrap_deeplink_wrappers(current)
    if final and "promobit.com" not in final.lower():
        with _CACHE_LOCK:
            if len(_RESOLVED_URL_CACHE) > 4096:
                _RESOLVED_URL_CACHE.clear()
            _RESOLVED_URL_CACHE[url] = final
            if "promobit.com" in url.lower() or "meli.la" in url.lower() or "s.shopee" in url.lower():
                _save_disk_cache()
    return final


def clean_product_url(url: str, resolve_redirects: bool = False) -> str:
    """Remove afiliados de terceiros, wrappers e parâmetros de rastreio mantendo apenas a URL limpa do produto."""
    if not url:
        return ""

    final_url = resolve_unshorten_url(url) if resolve_redirects else _unwrap_deeplink_wrappers(url)
    if final_url == "__SPAM__":
        return "__SPAM__"
    if not final_url:
        return ""

    low = final_url.lower()

    # Descartar URLs que não são produtos (ex: grupos /messenger/)
    if "/messenger/" in low:
        return ""

    # 1. Mercado Livre: Extrair /p/MLB..., /up/MLBU... ou /MLB-... sem lixo de terceiros
    if "mercadolivre.com" in low or "mercadolibre.com" in low:
        m = re.search(
            r'(https://(?:www|produto)\.mercadolivre\.com\.br/[^?#]+?(?:/p/MLB\d+|/up/MLBU\d+|MLB-\d+-[^?#]+))',
            final_url,
        )
        if m:
            return m.group(1)
        clean = re.sub(r'([?&])(?:matt_tool|matt_word|forceInApp|ref|reco_[^=]*|tracking_id|wid|sid|c_id|c_uid)=[^&]*', '', final_url)
        clean = clean.replace("?&", "?").rstrip("?&")
        return clean.split("#")[0]

    # 2. Shopee: Canonicalizar /opaanlp/{shop}/{item} -> /product/{shop}/{item} e remover an_... / utm_... / sub_id
    if "shopee.com" in low:
        parsed = urlparse(final_url)
        m_op = re.match(r'^/(?:opaanlp|product)/(\d+)/(\d+)', parsed.path)
        if m_op:
            return f"https://shopee.com.br/product/{m_op.group(1)}/{m_op.group(2)}"
        if re.search(r'-i\.\d+\.\d+', parsed.path):
            return f"https://shopee.com.br{parsed.path}"
        clean = re.sub(
            r'([?&])(?:af_sub_siteid|af_c_id|sub_id|universal-link|mmp_pid|uls_trackid|gads_t_sig|exp_group|__mobile__|sp_atk|xptdk|utm_[^=]*)=[^&]*',
            '',
            final_url,
        )
        clean = clean.replace("?&", "?").rstrip("?&")
        return clean.split("#")[0]

    # 3. Shein: Extrair URL limpa do produto (-p-{id}.html) sem onelink/rakuten/utm
    if "shein.com" in low:
        m_sh = re.search(r'(https?://(?:br|www|m)\.shein\.com/[^?#]+?-p-\d+(?:-cat-\d+)?\.html)', final_url)
        if m_sh:
            return m_sh.group(1).replace("http://", "https://", 1)
        m_gid = re.search(r'goods_id=(\d+)', final_url)
        if m_gid:
            return f"https://br.shein.com/product-p-{m_gid.group(1)}.html"
        parsed = urlparse(final_url)
        return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", "", ""))

    # 4. Outras lojas (caso usuário cole no Analisador Avulso)
    if "amazon.com" in low:
        m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', final_url)
        if m:
            return f"https://www.amazon.com.br/dp/{m.group(1)}"

    parsed = urlparse(final_url)
    if parsed.query:
        qs = parse_qs(parsed.query)
        cleaned_qs = {
            k: v for k, v in qs.items()
            if not k.startswith("utm_") and k not in ("tag", "aff_id", "subid", "ref", "ascsubtag", "linkCode", "linkId")
        }
        new_query = urlencode(cleaned_qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))

    return final_url.split("#")[0]


@lru_cache(maxsize=2048)
def generate_shopee_shortlink(origin_url: str, app_id: str, app_secret: str, sub_id: str = "") -> str:
    """Converte qualquer URL limpa de produto da Shopee em link curto oficial do afiliado via Open API."""
    if not origin_url or not app_id or not app_secret:
        return ""
    try:
        sub_part = f', subIds: [{json.dumps(sub_id)}]' if sub_id else ""
        origin_escaped = json.dumps(origin_url)
        query = f'mutation {{ generateShortLink(input: {{ originUrl: {origin_escaped}{sub_part} }}) {{ shortLink }} }}'
        payload_str = json.dumps({"query": query}, separators=(",", ":"))
        ts = int(time.time())
        sig = hashlib.sha256(f"{app_id}{ts}{payload_str}{app_secret}".encode("utf-8")).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={app_id},Timestamp={ts},Signature={sig}",
        }
        r = _get_aff_session().post("https://open-api.affiliate.shopee.com.br/graphql", data=payload_str, headers=headers, timeout=5)
        if r.status_code == 200:
            short_link = r.json().get("data", {}).get("generateShortLink", {}).get("shortLink", "")
            return short_link or ""
    except Exception:
        pass
    return ""


def _needs_resolution(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    return any(dom in low for dom in REDIRECT_DOMAINS) or "/social/" in low


def resolve_deals_links_batch(deals: list, max_workers: int = 12, max_promobit: int = 15) -> list:
    """Resolve URLs diretas/encurtadas em paralelo e extrai links do Promobit com cache persistente."""
    with _CACHE_LOCK:
        _ensure_disk_cache_loaded()

    pending = [d for d in deals if _needs_resolution(d.get("url", "")) and not d.get("_url_resolved")]
    fast_list = []
    promobit_list = []
    for d in pending:
        raw_u = d.get("url", "")
        if "promobit.com" in raw_u.lower():
            if raw_u in _RESOLVED_URL_CACHE:
                fast_list.append(d)
            else:
                promobit_list.append(d)
        else:
            fast_list.append(d)

    def _resolve_one(deal: dict):
        raw_u = deal.get("url", "")
        clean_u = clean_product_url(raw_u, resolve_redirects=True)
        if clean_u == "__SPAM__":
            deal["_invalid_link"] = True
        elif clean_u:
            deal["url"] = clean_u
            if "promobit.com" not in clean_u.lower():
                deal["_url_resolved"] = True

    if fast_list:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(fast_list))) as ex:
            list(ex.map(_resolve_one, fast_list))

    # Promobit limita bursts paralelos (429); resolve suavemente novos links e para em caso de cooldown
    resolved_pb = 0
    for d in promobit_list:
        if resolved_pb >= max_promobit or time.time() < _PROMOBIT_COOLDOWN_UNTIL:
            break
        _resolve_one(d)
        resolved_pb += 1

    for d in deals:
        if not d.get("_url_resolved") and not d.get("_invalid_link") and d.get("url"):
            cleaned = clean_product_url(d["url"], resolve_redirects=False)
            if cleaned and cleaned != "__SPAM__":
                d["url"] = cleaned
                if "promobit.com" not in cleaned.lower():
                    d["_url_resolved"] = True

    return [d for d in deals if not d.get("_invalid_link")]


def convert_to_affiliate(
    url: str,
    store_name: str,
    config: dict,
    resolve_redirects: bool = True,
    is_own_shopee_api_link: bool = False,
) -> dict:
    """
    Converte a URL para link direto do produto com a tag/link oficial pertencente ao usuário.
    """
    tags = config.get("affiliate_tags", {})
    shp_app_id = tags.get("shopee_app_id", "").strip()
    shp_app_secret = tags.get("shopee_app_secret", "").strip()

    if is_own_shopee_api_link and url and "s.shopee.com.br/" in url and shp_app_id:
        return {
            "url": url,
            "clean_url": url,
            "is_tagged": True,
            "store": "Shopee",
            "status": "Link Oficial Shopee API Afiliados (Sua Conta)",
        }

    clean_url = clean_product_url(url, resolve_redirects=resolve_redirects)
    if not clean_url or clean_url == "__SPAM__":
        clean_url = url

    detected_store = identify_store(clean_url if clean_url else url)
    final_store = detected_store if detected_store != "Loja Parceira" else store_name

    # Nunca anexar tag de loja em cima de redirecionador não resolvido do Promobit
    if "promobit.com" in (clean_url or "").lower():
        return {
            "url": clean_url,
            "clean_url": clean_url,
            "is_tagged": False,
            "store": final_store,
            "status": "⚠️ Limite temporário Promobit ao extrair link direto (use cards diretos ou aguarde 2 min)",
        }

    store_lower = final_store.lower().replace(" ", "").replace("-", "")

    tag_key = None
    if "mercado" in store_lower or "livre" in store_lower:
        tag_key = "mercadolivre"
    elif "shopee" in store_lower:
        tag_key = "shopee"
    elif "shein" in store_lower:
        tag_key = "shein"
    elif "amazon" in store_lower:
        tag_key = "amazon"
    elif "magalu" in store_lower or "magazine" in store_lower:
        tag_key = "magalu"

    tag_value = tags.get(tag_key, "").strip() if tag_key else ""

    # 1. Shopee: Prioridade total para Shopee Open API (gera s.shopee.com.br da conta do usuário!)
    if tag_key == "shopee":
        if shp_app_id and shp_app_secret and "shopee.com" in clean_url:
            short_own = generate_shopee_shortlink(clean_url, shp_app_id, shp_app_secret, sub_id=tag_value)
            if short_own:
                return {
                    "url": short_own,
                    "clean_url": clean_url,
                    "is_tagged": True,
                    "store": "Shopee",
                    "status": "Link Curto Shopee Gerado na Sua Conta (Open API)",
                }
        if not tag_value:
            return {
                "url": clean_url,
                "clean_url": clean_url,
                "is_tagged": False,
                "store": "Shopee",
                "status": "Link direto Shopee limpo (Configure App ID/Secret ou ID Shopee nas Configs)",
            }
        sep = "&" if "?" in clean_url else "?"
        if tag_value.startswith("an_") or (tag_value.isdigit() and len(tag_value) >= 8):
            pid = tag_value if tag_value.startswith("an_") else f"an_{tag_value}"
            aff_url = f"{clean_url}{sep}utm_source={pid}&utm_medium=affiliates&mmp_pid={pid}"
            return {
                "url": aff_url,
                "clean_url": clean_url,
                "is_tagged": True,
                "store": "Shopee",
                "status": f"ID Shopee Afiliado aplicado: {pid}",
            }
        aff_url = f"{clean_url}{sep}universal-link=true&sub_id={tag_value}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": "Shopee",
            "status": f"Sub_ID Shopee aplicado: {tag_value}",
        }

    if not tag_value:
        return {
            "url": clean_url,
            "clean_url": clean_url,
            "is_tagged": False,
            "store": final_store,
            "status": f"Link direto do produto limpo (Sem tag cadastrada para {final_store})",
        }

    # 2. Mercado Livre
    if tag_key == "mercadolivre":
        sep = "&" if "?" in clean_url else "?"
        param = tag_value if "=" in tag_value else f"matt_tool={tag_value}"
        aff_url = f"{clean_url}{sep}{param}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": "Mercado Livre",
            "status": f"Tag Mercado Livre aplicada: {tag_value}",
        }

    # 3. Shein
    if tag_key == "shein":
        sep = "&" if "?" in clean_url else "?"
        param = tag_value if "=" in tag_value else f"aff_id={tag_value}"
        aff_url = f"{clean_url}{sep}{param}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": "Shein",
            "status": f"Tag Shein aplicada: {tag_value}",
        }

    # 4. Amazon / Magalu fallback (apenas se usuário colar no Analisador Avulso)
    if tag_key == "amazon":
        sep = "&" if "?" in clean_url else "?"
        return {
            "url": f"{clean_url}{sep}tag={tag_value}",
            "clean_url": clean_url,
            "is_tagged": True,
            "store": final_store,
            "status": f"Tag Amazon aplicada: {tag_value}",
        }
    if tag_key == "magalu":
        if "magazineluiza.com.br" in clean_url:
            aff_url = clean_url.replace("www.magazineluiza.com.br", f"www.magazinevoce.com.br/{tag_value}")
        else:
            sep = "&" if "?" in clean_url else "?"
            aff_url = f"{clean_url}{sep}partner_id={tag_value}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": final_store,
            "status": f"Loja Magazine Você aplicada: {tag_value}",
        }

    sep = "&" if "?" in clean_url else "?"
    return {
        "url": f"{clean_url}{sep}aff_id={tag_value}",
        "clean_url": clean_url,
        "is_tagged": True,
        "store": final_store,
        "status": f"Tag {final_store} aplicada: {tag_value}",
    }
