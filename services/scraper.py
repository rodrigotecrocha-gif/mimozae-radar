import hashlib
import html as html_lib
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from services.affiliate import identify_store, clean_product_url


def strip_accents(text: str) -> str:
    """Remove acentos e converte para minúsculas para comparação flexível."""
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    ).lower()


# Catálogo Curado de Produtos Altamente Virais e Top Mais Vendidos (Shopee, ML, Shein, TikTok)
VIRAL_CATALOG = {
    "🔥 Top 50 Virais (Shopee, ML & TikTok)": [
        "kit calca", "calca sarja", "conjunto infantil", "kit infantil",
        "capinha", "multimidia", "pc gamer", "notebook", "projetor",
        "mini processador", "tapete airfryer", "garrafa termica",
        "copo termico", "potes hermeticos", "mop giratorio", "meia calca",
        "smartwatch", "fone bluetooth", "escova secadora", "air fryer",
        "aspirador", "parafusadeira", "creatina"
    ],
    "🌸 Beleza & Skincare (Alta Recorrência)": [
        "lola cosmetics", "cerave", "principia", "escova secadora",
        "oleo extraordinario", "elseve", "protetor solar", "neutrogena",
        "darrow actine", "cicaplast", "agua micelar", "nivea", "perfume",
        "hidratante", "serum", "maquiagem"
    ],
    "🏠 Casa, Cozinha & Gadgets (Achadinhos)": [
        "mini processador", "airfryer", "fritadeira", "garrafa termica",
        "copo termico", "potes hermeticos", "mop giratorio", "aspirador",
        "panela", "cafeteira", "cadeira", "sofa", "micro-ondas", "organizador"
    ],
    "👗 Moda & Acessórios (Shein, Shopee & ML)": [
        "vestido", "kit calca", "conjunto", "tenis", "chinelo", "havaianas",
        "calca jeans", "camiseta", "bolsa", "relogio", "oculos", "sarja",
        "legging", "pantalona", "infantil"
    ],
    "📱 Celulares, Tech & Setup Gamer": [
        "capinha", "multimidia", "pc gamer", "notebook", "projetor",
        "fone", "bluetooth", "smartwatch", "alexa", "galaxy", "iphone",
        "xiaomi", "monitor", "teclado", "headset", "playstation"
    ],
}

VIRAL_KEYWORDS_FLAT = sorted({kw for kws in VIRAL_CATALOG.values() for kw in kws})

# Mapeamento rico de Nichos -> Slugs diretos nas plataformas + keywords flexíveis
NICHES = {
    "Todos os Nichos": {
        "keywords": [],
        "ml_cats": ["calcados-roupas-e-bolsas", "beleza-e-cuidado-pessoal", "casa-moveis-e-decoracao", "eletrodomesticos", "celulares-e-telefones", "informatica"],
        "pb_cats": ["beleza-e-saude", "moda-feminina", "casa-e-cozinha"],
        "pelando_cats": ["para-elas", "para-meu-lar", "tech-lover"],
        "amz_cats": ["beauty", "kitchen", "electronics"],
        "shopee_kws": ["oferta", "mais vendidos"],
    },
    "🌸 Beleza & Skincare": {
        "keywords": [
            "beleza", "cabelo", "pele", "perfume", "maquiagem", "skincare", "lola",
            "cerave", "principia", "protetor", "shampoo", "condicionador", "creme",
            "oleo", "batom", "hidratante", "serum", "desodorante", "escova",
            "chapinha", "secador", "sabonete", "micelar", "cicaplast", "colonia",
            "eudora", "boticario", "natura", "nivea", "elseve", "karseell"
        ],
        "ml_cats": ["beleza-e-cuidado-pessoal"],
        "pb_cats": ["beleza-e-saude"],
        "pelando_cats": ["para-elas"],
        "amz_cats": ["beauty"],
        "shopee_kws": ["skincare hidratante", "perfume maquiagem cabelo"],
    },
    "👗 Moda & Acessórios": {
        "keywords": [
            "moda", "vestido", "blusa", "calca", "calcado", "tenis", "chinelo",
            "bolsa", "conjunto feminino", "conjunto masculino", "conjunto moletom",
            "conjunto pijama", "pijama", "meia-calca", "body", "cinto", "oculos",
            "camiseta", "camisa", "jaqueta", "short", "saia", "feminina",
            "masculino", "masculina", "havaianas", "relogio", "mochila",
            "sapato", "sandalia", "cropped", "legging", "sarja", "jeans",
            "moletom", "cueca", "calcinha", "sutia", "polo", "bermuda", "lingerie"
        ],
        "ml_cats": ["calcados-roupas-e-bolsas"],
        "pb_cats": ["moda-feminina", "moda-masculina"],
        "pelando_cats": ["para-elas", "para-eles"],
        "amz_cats": ["fashion"],
        "shopee_kws": ["vestido conjunto feminino", "kit calcas camiseta tenis"],
    },
    "🏠 Casa, Cozinha & Eletro": {
        "keywords": [
            "casa", "cozinha", "panela", "cafeteira", "airfryer", "fritadeira",
            "aspirador", "ventilador", "processador", "garrafa", "copo", "potes",
            "mop", "organizador", "cadeira", "sofa", "mesa", "cama", "colchao",
            "micro-ondas", "microondas", "geladeira", "liquidificador", "lampada",
            "lixeira", "edredom", "toalha", "utensilio", "lencol", "travesseiro",
            "ar-condicionado", "ferro", "batedeira", "fogao", "lavadora", "armario",
            "guarda-roupa", "refil", "purificador", "parafusadeira", "ferramenta"
        ],
        "ml_cats": ["casa-moveis-e-decoracao", "eletrodomesticos"],
        "pb_cats": ["casa-e-cozinha", "eletrodomesticos"],
        "pelando_cats": ["para-meu-lar"],
        "amz_cats": ["kitchen", "home"],
        "shopee_kws": ["cozinha airfryer organizador", "casa decoracao panela"],
    },
    "📱 Celulares, Tech & Setup Gamer": {
        "keywords": [
            "teclado", "mouse", "gamer", "headset", "monitor", "notebook", "ssd",
            "alexa", "fone", "bluetooth", "smartwatch", "multimidia", "projetor",
            "celular", "smartphone", "samsung", "iphone", "xiaomi", "capinha",
            "capa", "carregador", "power bank", "tv", "smart tv", "controle",
            "playstation", "ps5", "xbox", "nintendo", "gabinete", "placa de video",
            "tablet", "pc", "webcam", "microfone", "caixa de som", "kindle", "cabo"
        ],
        "ml_cats": ["celulares-e-telefones", "informatica", "eletronicos-audio-e-video", "games"],
        "pb_cats": ["celulares-e-smartphones", "informatica"],
        "pelando_cats": ["tech-lover", "mundo-gamer"],
        "amz_cats": ["electronics", "computers"],
        "shopee_kws": ["fone smartwatch capinha", "gamer teclado mouse celular"],
    },
    "👶 Bebês & Infantil": {
        "keywords": [
            "bebe", "infantil", "crianca", "menina", "menino", "fralda", "carrinho",
            "brinquedo", "kit infantil", "conjunto infantil", "mamadeira", "boneca",
            "lego", "berco", "pampers", "huggies", "lenço umedecido"
        ],
        "ml_cats": ["bebes"],
        "pb_cats": ["bebe-e-infantil"],
        "pelando_cats": ["para-minha-familia"],
        "amz_cats": ["baby-products", "toys-and-games"],
        "shopee_kws": ["conjunto infantil", "fralda bebe brinquedo"],
    },
    "💪 Esportes & Saúde": {
        "keywords": [
            "creatina", "whey", "suplemento", "fitness", "esporte", "academia",
            "bicicleta", "garrafa", "haltere", "corrida", "camisa", "bola",
            "colageno", "vitamina", "omega", "growth", "integralmedica"
        ],
        "ml_cats": ["esportes-e-fitness"],
        "pb_cats": ["esporte-e-lazer"],
        "pelando_cats": ["esporte-e-vida"],
        "amz_cats": ["hpc", "sports"],
        "shopee_kws": ["creatina whey fitness", "academia esporte"],
    },
}

# Mapeamento do título da seção do Mercado Livre /mais-vendidos para nossas chaves de nicho
ML_MV_SECTION_MAP = {
    "beleza": "🌸 Beleza & Skincare",
    "calcados": "👗 Moda & Acessórios",
    "roupas": "👗 Moda & Acessórios",
    "eletrodomesticos": "🏠 Casa, Cozinha & Eletro",
    "casa": "🏠 Casa, Cozinha & Eletro",
    "ferramentas": "🏠 Casa, Cozinha & Eletro",
    "celulares": "📱 Celulares, Tech & Setup Gamer",
    "informatica": "📱 Celulares, Tech & Setup Gamer",
    "eletronicos": "📱 Celulares, Tech & Setup Gamer",
    "games": "📱 Celulares, Tech & Setup Gamer",
    "esportes": "💪 Esportes & Saúde",
    "bebes": "👶 Bebês & Infantil",
}

ALLOWED_STORES = ("Mercado Livre", "Shopee", "Shein")

PROMOBIT_STORE_SLUGS = {
    "mercado": "mercado-livre",
    "shopee": "shopee",
    "shein": "shein",
}

SPAM_OFFER_PATTERNS = (
    "lista de cupons ativos",
    "entre no novo grupo",
    "entre no grupo",
    "grupo do telegram",
    "grupo do whatsapp",
    "cupom exclusivo:",
    "frete gratis em compras",
)

_SESSION = None
_HTML_CACHE = {}
_CACHE_TTL_SECONDS = 240

try:
    import lxml  # noqa: F401
    _BS_PARSER = "lxml"
except ImportError:
    _BS_PARSER = "html.parser"


def _make_soup(html_text: str):
    return BeautifulSoup(html_text, _BS_PARSER)


def _safe_count(val) -> int:
    if isinstance(val, (list, tuple, set)):
        return len(val)
    try:
        return int(val or 0)
    except Exception:
        return 0


def _cache_get(key: str):
    import time
    entry = _HTML_CACHE.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _cache_set(key: str, value):
    import time
    _HTML_CACHE[key] = (time.time(), value)


def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=1)
        _SESSION.mount("https://", adapter)
        _SESSION.mount("http://", adapter)
    return _SESSION


def sanitize_img_url(img_url: str, source: str = "") -> str:
    """Higieniza URLs de imagens para garantir protocolo absoluto https://."""
    if not img_url:
        return ""
    s = str(img_url).strip()
    if s.startswith("//"):
        return f"https:{s}"
    if s.startswith("http://") or s.startswith("https://"):
        return s

    clean_path = s.lstrip("/")
    if s.startswith("/static/"):
        return f"https://www.promobit.com.br{s}"
    if "promobit" in source.lower() or re.match(r"^(?:\d+/)?\d+", clean_path):
        return f"https://i.promobit.com.br/{clean_path}"
    if s.startswith("/"):
        return f"https://i.promobit.com.br/{clean_path}"
    return f"https://{clean_path}"


def robust_parse_money(txt: str) -> float:
    """Extrai valores numéricos em Reais com segurança."""
    if not txt:
        return 0.0
    s = str(txt).strip()
    if "/" in s:
        s = s.split("/")[0]
    m = re.search(r"R\$\s*([\d\.,]+)", s) or re.search(r"([\d\.,]+)", s)
    if m:
        raw_num = m.group(1).strip().rstrip(".,")
        if "," in raw_num and "." in raw_num:
            if raw_num.rfind(",") > raw_num.rfind("."):
                raw_num = raw_num.replace(".", "").replace(",", ".")
            else:
                raw_num = raw_num.replace(",", "")
        elif "," in raw_num:
            raw_num = raw_num.replace(",", ".")
        try:
            return float(raw_num)
        except Exception:
            pass
    return 0.0


def validate_and_sanitize_prices(price: float, old_price: float = None, discount_pct: int = 0):
    """
    Higieniza preços e calcula apenas descontos REAIS (sem inflar ou fabricar % OFF falso).
    """
    if price < 1.5:
        if old_price and old_price > 10.0:
            price = old_price
            old_price = None
        else:
            return 0.0, None, 0

    if old_price is not None:
        if old_price <= 1.5 or old_price <= (price * 1.03) or old_price > (price * 7.0):
            old_price = None

    real_disc = 0
    if old_price and old_price > price > 0:
        real_disc = int(round(((old_price - price) / old_price) * 100))
    elif discount_pct and 0 < discount_pct < 95:
        real_disc = int(discount_pct)
        if not old_price and real_disc >= 5:
            estimated_old = price / (1.0 - (real_disc / 100.0))
            if estimated_old > price:
                old_price = round(estimated_old, 2)

    return round(price, 2), round(old_price, 2) if old_price else None, real_disc


def normalize_store_name(raw: str, url: str = "") -> str:
    combined = (str(raw or "") + " " + str(url or "")).lower()
    if "amazon" in combined:
        return "Amazon Brasil"
    if "mercado" in combined or "meli" in combined:
        return "Mercado Livre"
    if "shopee" in combined:
        return "Shopee"
    if "shein" in combined:
        return "Shein"
    if "magalu" in combined or "magazine" in combined:
        return "Magazine Luiza"
    if "casas" in combined or "bahia" in combined:
        return "Casas Bahia"
    if "aliexpress" in combined:
        return "AliExpress"
    if "dafiti" in combined:
        return "Dafiti"
    if raw:
        return str(raw).strip()
    return "Loja Parceira"


def is_viral_item(title: str) -> bool:
    norm = strip_accents(title)
    return any(kw in norm for kw in VIRAL_KEYWORDS_FLAT)


def is_spam_offer(title: str, price: float) -> bool:
    if price <= 1.5:
        return True
    norm = strip_accents(title)
    return any(p in norm for p in SPAM_OFFER_PATTERNS)


def compute_quality_score(deal: dict) -> float:
    """Pontua ofertas priorizando: Desconto Acentuado + Relâmpago + +Vendidos + Bem Avaliados + Viral."""
    score = 0.0
    disc = deal.get("discount_pct") or 0
    score += min(disc, 85) * 1.8
    if deal.get("is_flash"):
        score += 32.0
    if deal.get("is_bestseller"):
        score += 30.0
    rating = deal.get("rating") or 0.0
    if rating >= 4.5:
        score += 24.0 + (rating - 4.0) * 10
    elif rating > 0:
        score += rating * 4.0
    sales = deal.get("sales_count") or 0
    if sales >= 500:
        score += 25.0
    elif sales >= 50:
        score += 15.0
    likes = deal.get("likes") or 0
    clicks = deal.get("clicks") or 0
    score += min(likes, 50) * 0.5 + min(clicks, 500) * 0.04
    if deal.get("is_viral"):
        score += 18.0
    if deal.get("image"):
        score += 8.0
    url_low = (deal.get("url") or "").lower()
    if url_low and "promobit.com" not in url_low:
        score += 120.0
    return round(score, 2)


def _finalize_deal(deal: dict) -> dict:
    """Garante campos de qualidade e imagem padronizados."""
    deal["image"] = sanitize_img_url(deal.get("image", ""), deal.get("store", ""))
    deal["is_viral"] = deal.get("is_viral") or is_viral_item(deal.get("title", ""))
    deal["quality_score"] = compute_quality_score(deal)
    return deal


# ==============================================================================
# 1. PROMOBIT LIVE JSON API (LOJAS + FEED + BUSCA + CATEGORIAS)
# ==============================================================================

def _parse_promobit_json_offer(o: dict) -> dict | None:
    title = (o.get("offer_title") or o.get("offerTitle") or "").strip()
    price = float(o.get("offer_price") or o.get("offerPrice") or 0)
    if not title or is_spam_offer(title, price):
        return None

    raw_old = o.get("offer_old_price") or o.get("offerOldPrice")
    old_price = float(raw_old) if raw_old and float(raw_old) > 1.5 else None
    disc = int(float(o.get("offer_discont_percentage") or o.get("offerDiscontPercentage") or 0))
    clean_p, clean_op, real_disc = validate_and_sanitize_prices(price, old_price, disc)
    if clean_p <= 0:
        return None

    offer_id = o.get("offer_id") or o.get("offerId")
    slug = o.get("offer_slug") or o.get("offerSlug") or ""
    item_url = (
        f"https://www.promobit.com.br/Redirect/to/{offer_id}/"
        if offer_id else f"https://www.promobit.com.br/oferta/{slug}/"
    )

    store_raw = o.get("store_name") or o.get("storeName") or "Loja Parceira"
    likes = int(o.get("offer_likes") or o.get("offerLikes") or 0)
    clicks = int(o.get("offer_clicks") or o.get("offerClicks") or 0)
    engagement = int(o.get("offer_engagement_score") or o.get("offerEngagementScore") or 0)
    is_highlight = bool(o.get("offer_is_highlight") or o.get("offerIsHighlight"))
    cat = o.get("category_name") or o.get("categoryName") or o.get("category_slug") or ""

    sales_label = ""
    if is_highlight or engagement >= 200:
        sales_label = f"⚡ Destaque • {clicks} cliques" if clicks >= 20 else "⚡ Oferta em Alta"
    elif clicks >= 50:
        sales_label = f"🔥 {clicks} cliques recentes"
    elif likes >= 3:
        sales_label = f"👍 {likes} aprovações"

    return _finalize_deal({
        "title": title,
        "price": clean_p,
        "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
        "old_price": clean_op,
        "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
        "discount_pct": real_disc,
        "store": normalize_store_name(store_raw, item_url),
        "url": item_url,
        "image": sanitize_img_url(o.get("offer_photo") or o.get("offerPhoto") or "", "promobit"),
        "coupon": o.get("offer_coupon") or o.get("offerCoupon"),
        "category": cat,
        "source": "Promobit API",
        "is_flash": is_highlight or real_disc >= 40,
        "is_bestseller": engagement >= 300 or likes >= 10,
        "likes": likes,
        "clicks": clicks,
        "sales_count": clicks,
        "sales_label": sales_label,
        "rating": 4.8 if likes >= 5 else 0.0,
    })


def fetch_promobit_store_api(store_slug: str, max_pages: int = 2) -> list:
    """Busca até 50x(max_pages) ofertas diretamente do endpoint oficial da loja no Promobit."""
    deals = []
    session = get_session()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    after = None
    for _ in range(max_pages):
        base = (
            f"https://api.promobit.com.br/stores/{store_slug}/offers?limit=50"
            if store_slug else "https://api.promobit.com.br/offers?limit=50"
        )
        url = f"{base}&after={after}" if after else base
        try:
            r = session.get(url, headers=headers, timeout=5)
            if r.status_code != 200:
                break
            data = r.json()
            offs = data.get("offers", [])
            if not offs:
                break
            for o in offs:
                parsed = _parse_promobit_json_offer(o)
                if parsed:
                    deals.append(parsed)
            next_after = data.get("after")
            if not next_after or next_after == after:
                break
            after = next_after
        except Exception:
            break
    return deals


def fetch_promobit_search_api(query: str) -> list:
    """Busca ofertas no Promobit Search API (inclui ativas e recentes)."""
    deals = []
    session = get_session()
    try:
        r = session.get(
            f"https://api.promobit.com.br/search?q={query.replace(' ', '+')}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        if r.status_code == 200:
            j = r.json()
            for o in (j.get("active_offers", []) + j.get("finished_offers", [])):
                parsed = _parse_promobit_json_offer(o)
                if parsed:
                    deals.append(parsed)
    except Exception:
        pass
    return deals


# ==============================================================================
# 2. MERCADO LIVRE DIRETO (MAIS VENDIDOS + OFERTAS POR NICHO)
# ==============================================================================

def _parse_ml_amount(el) -> float:
    if not el:
        return 0.0
    fr = el.select_one(".andes-money-amount__fraction")
    ce = el.select_one(".andes-money-amount__cents")
    if not fr:
        return robust_parse_money(el.get_text(" ", strip=True))
    f_txt = re.sub(r"[^\d]", "", fr.get_text(strip=True)) or "0"
    c_txt = re.sub(r"[^\d]", "", ce.get_text(strip=True)) if ce else "00"
    try:
        return float(f"{f_txt}.{c_txt.zfill(2)}")
    except Exception:
        return 0.0


def _parse_ml_poly_card(card, category_label: str = "", default_bestseller: bool = False) -> dict | None:
    title_el = card.select_one("a.poly-component__title, .poly-component__title")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    href = title_el.get("href", "")
    if not href:
        a_tag = card.select_one("a[href*='mercadolivre.com.br']")
        href = a_tag.get("href", "") if a_tag else ""
    if not href:
        return None
    clean_url = href.split("#")[0]

    curr_p = _parse_ml_amount(card.select_one(".poly-price__current"))
    old_p = _parse_ml_amount(card.select_one(".andes-money-amount--previous"))

    disc_el = card.select_one(".andes-money-amount__discount, .poly-price__disc_label")
    disc_pct = 0
    if disc_el:
        m_d = re.search(r"(\d+)\s*%", disc_el.get_text())
        if m_d:
            disc_pct = int(m_d.group(1))

    clean_p, clean_op, real_disc = validate_and_sanitize_prices(curr_p, old_p or None, disc_pct)
    if clean_p <= 0:
        return None

    lbl_el = card.select_one(".poly-component__poly-label span, .poly-component__highlight")
    badge_txt = lbl_el.get_text(" ", strip=True).upper() if lbl_el else ""
    is_flash = any(k in badge_txt for k in ("OFERTA DO DIA", "RELÂMPAGO", "RELAMPAGO", "BLACK FRIDAY"))
    is_best = default_bestseller or ("MAIS VENDIDO" in badge_txt)

    rating = 0.0
    rev_el = card.select_one(".poly-reviews__rating")
    if rev_el:
        try:
            rating = float(rev_el.get_text(strip=True).replace(",", "."))
        except Exception:
            pass

    tot_reviews = 0
    tot_el = card.select_one(".poly-reviews__total")
    if tot_el:
        digits = re.sub(r"[^\d]", "", tot_el.get_text())
        if digits:
            tot_reviews = int(digits)

    img_el = card.select_one("img.poly-component__picture, img")
    raw_img = ""
    if img_el:
        raw_img = img_el.get("data-src") or img_el.get("src") or ""
        if raw_img.startswith("data:"):
            raw_img = img_el.get("data-src") or ""

    sales_parts = []
    if is_flash:
        sales_parts.append("⚡ Oferta Relâmpago/Dia")
    if is_best:
        sales_parts.append("🏆 Mais Vendido ML")
    if rating > 0:
        sales_parts.append(f"⭐ {rating:.1f}" + (f" ({tot_reviews})" if tot_reviews else ""))

    return _finalize_deal({
        "title": title,
        "price": clean_p,
        "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
        "old_price": clean_op,
        "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
        "discount_pct": real_disc,
        "store": "Mercado Livre",
        "url": clean_url,
        "image": raw_img,
        "coupon": None,
        "category": category_label,
        "source": "Mercado Livre Direto",
        "is_flash": is_flash,
        "is_bestseller": is_best,
        "likes": tot_reviews,
        "clicks": 0,
        "sales_count": 500 if is_best else tot_reviews,
        "sales_label": " • ".join(sales_parts) if sales_parts else "🔥 Destaque Mercado Livre",
        "rating": rating if rating > 0 else (4.8 if is_best else 0.0),
    })


def fetch_mercadolivre_mais_vendidos(target_niche: str = "Todos os Nichos") -> list:
    """Extrai até ~198 produtos direto de mercadolivre.com.br/mais-vendidos (com cache em memória e filtro por nicho)."""
    cached_all = _cache_get("ml_mais_vendidos_all")
    if cached_all is None:
        cached_all = []
        try:
            r = cffi_requests.get("https://www.mercadolivre.com.br/mais-vendidos", impersonate="chrome124", timeout=8)
            if r.status_code == 200:
                soup = _make_soup(r.text)
                for sec in soup.select("section"):
                    cards = sec.select(".poly-card")
                    if not cards:
                        continue
                    parent_h = sec.parent.select_one("h2, h3") if sec.parent else None
                    heading_txt = parent_h.get_text(strip=True) if parent_h else ""
                    heading_norm = strip_accents(heading_txt)

                    mapped_niche = ""
                    for key_word, niche_name in ML_MV_SECTION_MAP.items():
                        if key_word in heading_norm:
                            mapped_niche = niche_name
                            break

                    for c in cards:
                        parsed = _parse_ml_poly_card(c, category_label=mapped_niche or heading_txt, default_bestseller=True)
                        if parsed:
                            parsed["_ml_niche"] = mapped_niche
                            cached_all.append(parsed)
                if cached_all:
                    _cache_set("ml_mais_vendidos_all", cached_all)
        except Exception:
            pass

    if target_niche == "Todos os Nichos":
        return list(cached_all)
    return [d for d in cached_all if not d.get("_ml_niche") or d.get("_ml_niche") == target_niche]


def fetch_mercadolivre_category(cat_slug: str) -> list:
    """Extrai dezenas de ofertas com desconto direto de mercadolivre.com.br/c/{cat_slug} com cache."""
    cache_key = f"ml_cat_{cat_slug}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return list(cached)
    deals = []
    try:
        r = cffi_requests.get(f"https://www.mercadolivre.com.br/c/{cat_slug}", impersonate="chrome124", timeout=8)
        if r.status_code != 200:
            return deals
        soup = _make_soup(r.text)
        for c in soup.select(".poly-card"):
            parsed = _parse_ml_poly_card(c, category_label=cat_slug, default_bestseller=False)
            if parsed:
                deals.append(parsed)
        if deals:
            _cache_set(cache_key, deals)
    except Exception:
        pass
    return deals


# ==============================================================================
# 3. PECHINCHOU JSON API (MAIS VENDIDOS, CURTIDOS & URGENTES)
# ==============================================================================

def _parse_pechinchou_items(items: list) -> list:
    deals = []
    for it in items:
        title = (it.get("title") or "").strip()
        p_raw = it.get("price")
        try:
            p_val = float(str(p_raw).replace(",", ".")) if p_raw else 0.0
        except Exception:
            p_val = robust_parse_money(str(p_raw or ""))
        if not title or is_spam_offer(title, p_val):
            continue

        op_raw = it.get("old_price")
        try:
            op_val = float(str(op_raw).replace(",", ".")) if op_raw else None
        except Exception:
            op_val = robust_parse_money(str(op_raw or "")) or None
        clean_p, clean_op, real_disc = validate_and_sanitize_prices(p_val, op_val)
        if clean_p <= 0:
            continue

        store_obj = it.get("store") or {}
        prod_url = it.get("long_url") or it.get("short_url") or ""
        if not prod_url:
            continue
        store_name = normalize_store_name(store_obj.get("name", ""), prod_url)
        if store_name not in ALLOWED_STORES:
            continue

        likes = _safe_count(it.get("likes"))
        sales = _safe_count(it.get("total_sales"))
        is_urgent = bool(it.get("urgent") or it.get("lowest_price"))
        subcat = (it.get("subcategory") or {}).get("name", "") if isinstance(it.get("subcategory"), dict) else ""

        parts = []
        if is_urgent:
            parts.append("⚡ Menor Preço / Relâmpago")
        if sales >= 50:
            parts.append(f"🔥 {sales} vendas")
        elif likes >= 2:
            parts.append(f"👍 {likes} curtidas")

        deals.append(_finalize_deal({
            "title": title,
            "price": clean_p,
            "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
            "old_price": clean_op,
            "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
            "discount_pct": real_disc,
            "store": store_name,
            "url": prod_url,
            "image": it.get("image") or "",
            "coupon": it.get("discount_coupon") or None,
            "category": subcat,
            "source": "Pechinchou API",
            "is_flash": is_urgent or real_disc >= 40,
            "is_bestseller": sales >= 100 or likes >= 10,
            "likes": likes,
            "clicks": 0,
            "sales_count": sales,
            "sales_label": " • ".join(parts),
            "rating": 4.7 if likes >= 5 else 0.0,
        }))
    return deals


def fetch_pechinchou_page(page_num: int = 1) -> list:
    session = get_session()
    url = f"http://admin2.pechinchou.com.br/api/v2/produto/listar_produtos_em_destaque/home/?hide_closed=false&page={page_num}"
    try:
        r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            return _parse_pechinchou_items(r.json().get("results", []))
    except Exception:
        pass
    return []


def fetch_pechinchou_catalog(page_num: int = 1) -> list:
    """Busca no catálogo completo da Pechinchou API (links diretos / meli.la sem Promobit)."""
    session = get_session()
    url = f"http://admin2.pechinchou.com.br/api/v2/produto/?page={page_num}"
    try:
        r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            return _parse_pechinchou_items(r.json().get("results", []))
    except Exception:
        pass
    return []


# ==============================================================================
# 4. PELANDO ASTRO JSON (SHOPEE, SHEIN, NICHOS POR TEMPERATURA)
# ==============================================================================

def _val_astro(v):
    if isinstance(v, list) and len(v) >= 2 and v[0] == 0:
        return v[1]
    return v


def fetch_pelando_feed(url_path: str) -> list:
    deals = []
    url = f"https://www.pelando.com.br{url_path}" if url_path.startswith("/") else url_path
    try:
        r = cffi_requests.get(url, impersonate="chrome124", timeout=7)
        if r.status_code != 200:
            return deals
        islands = re.findall(r'<astro-island[^>]*props="([^"]+)"', r.text)
        raw_nodes = []

        def walk(node):
            if isinstance(node, list):
                for x in node:
                    walk(x)
            elif isinstance(node, dict):
                if "title" in node and "sourceUrl" in node and "store" in node:
                    raw_nodes.append(node)
                else:
                    for val in node.values():
                        walk(val)

        for isl in islands:
            dec = html_lib.unescape(isl)
            if "sourceUrl" not in dec:
                continue
            try:
                walk(json.loads(dec))
            except Exception:
                pass

        for node in raw_nodes:
            kind = _val_astro(node.get("kind"))
            if kind != "promotion":
                continue
            title = str(_val_astro(node.get("title")) or "").strip()
            p_raw = _val_astro(node.get("price"))
            try:
                p_val = float(p_raw) if p_raw is not None else 0.0
            except Exception:
                p_val = 0.0
            if not title or is_spam_offer(title, p_val):
                continue

            disc_raw = _val_astro(node.get("discountPercentage"))
            disc_pct = int(float(disc_raw)) if disc_raw else 0
            clean_p, clean_op, real_disc = validate_and_sanitize_prices(p_val, None, disc_pct)
            if clean_p <= 0:
                continue

            store_obj = _val_astro(node.get("store"))
            store_name_raw = _val_astro(store_obj.get("name")) if isinstance(store_obj, dict) else ""
            source_url = str(_val_astro(node.get("sourceUrl")) or "")
            temp = int(_val_astro(node.get("temperature")) or 0)

            img_srcset = _val_astro(node.get("imageSrcset"))
            img = str(_val_astro(node.get("imageUrl")) or "")
            if isinstance(img_srcset, list) and img_srcset:
                last = _val_astro(img_srcset[-1])
                if isinstance(last, dict):
                    img = str(_val_astro(last.get("url")) or img)

            deals.append(_finalize_deal({
                "title": title,
                "price": clean_p,
                "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
                "old_price": clean_op,
                "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
                "discount_pct": real_disc,
                "store": normalize_store_name(store_name_raw, source_url),
                "url": source_url or f"https://www.pelando.com.br/d/{_val_astro(node.get('slug')) or ''}",
                "image": img,
                "coupon": None,
                "category": url_path,
                "source": "Pelando",
                "is_flash": temp >= 100 or real_disc >= 35,
                "is_bestseller": temp >= 150,
                "likes": temp,
                "clicks": 0,
                "sales_count": 0,
                "sales_label": f"🔥 {temp}° na comunidade" if temp >= 20 else "",
                "rating": 4.8 if temp >= 80 else 0.0,
            }))
    except Exception:
        pass
    return deals


# ==============================================================================
# 5. AMAZON BRASIL (MAIS VENDIDOS POR NICHO + BUSCA DIRETA COM AVALIAÇÕES)
# ==============================================================================

def fetch_amazon_bestsellers(cat_slug: str = "beauty") -> list:
    cache_key = f"amz_bs_{cat_slug}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return list(cached)
    deals = []
    try:
        r = cffi_requests.get(f"https://www.amazon.com.br/gp/bestsellers/{cat_slug}", impersonate="chrome124", timeout=7)
        if r.status_code != 200:
            return deals
        soup = _make_soup(r.text)
        for c in soup.select("#gridItemRoot")[:40]:
            link = c.select_one("a[href*='/dp/']")
            if not link:
                continue
            m_asin = re.search(r"/dp/([A-Z0-9]{10})", link.get("href", ""))
            if not m_asin:
                continue
            asin = m_asin.group(1)
            img_el = c.select_one("img")
            title = (img_el.get("alt") or "").strip() if img_el else ""
            if not title:
                t_el = c.select_one("a span div")
                title = t_el.get_text(strip=True) if t_el else ""
            price_el = c.select_one("._cDEzb_p13n-sc-price_3mJ9Z, .p13n-sc-price, span.a-color-price")
            p_val = robust_parse_money(price_el.get_text(strip=True)) if price_el else 0.0
            clean_p, clean_op, real_disc = validate_and_sanitize_prices(p_val)
            if not title or clean_p <= 0:
                continue

            rating = 0.0
            star_el = c.select_one(".a-icon-alt")
            if star_el:
                m_st = re.search(r"([\d,\.]+)", star_el.get_text())
                if m_st:
                    try:
                        rating = float(m_st.group(1).replace(",", "."))
                    except Exception:
                        pass

            deals.append(_finalize_deal({
                "title": title,
                "price": clean_p,
                "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
                "old_price": clean_op,
                "old_price_str": "",
                "discount_pct": real_disc,
                "store": "Amazon Brasil",
                "url": f"https://www.amazon.com.br/dp/{asin}",
                "image": img_el.get("src", "") if img_el else "",
                "coupon": None,
                "category": cat_slug,
                "source": "Amazon Mais Vendidos",
                "is_flash": False,
                "is_bestseller": True,
                "likes": 0,
                "clicks": 0,
                "sales_count": 500,
                "sales_label": f"🏆 Mais Vendido Amazon • ⭐ {rating:.1f}" if rating else "🏆 Mais Vendido Amazon",
                "rating": rating,
            }))
        if deals:
            _cache_set(cache_key, deals)
    except Exception:
        pass
    return deals


def fetch_amazon_direct(query: str = "ofertas", min_discount: int = 0, max_items: int = 18) -> list:
    deals = []
    try:
        rh_filter = "&rh=p_8%3A2253952011" if min_discount >= 30 else ("&rh=p_8%3A2253951011" if min_discount >= 15 else "")
        url = f"https://www.amazon.com.br/s?k={query.replace(' ', '+')}{rh_filter}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
        }
        r = cffi_requests.get(url, headers=headers, impersonate="chrome124", timeout=6)
        if r.status_code != 200:
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        for c in soup.select("div[data-asin]"):
            asin = c.get("data-asin")
            if not asin or len(asin) != 10:
                continue
            title_el = c.select_one("h2 span")
            price_el = c.select_one(".a-price .a-offscreen")
            old_p_el = c.select_one(".a-price.a-text-price:not(.a-size-mini) .a-offscreen")
            img_el = c.select_one("img.s-image")
            if not (title_el and price_el):
                continue

            p_val = robust_parse_money(price_el.get_text(strip=True))
            op_val = robust_parse_money(old_p_el.get_text(strip=True)) if old_p_el else None
            clean_p, clean_op, disc = validate_and_sanitize_prices(p_val, op_val)
            if clean_p <= 0:
                continue

            rating = 0.0
            star_el = c.select_one(".a-icon-alt")
            if star_el:
                m_st = re.search(r"([\d,\.]+)", star_el.get_text())
                if m_st:
                    try:
                        rating = float(m_st.group(1).replace(",", "."))
                    except Exception:
                        pass

            title = title_el.get_text(strip=True)
            deals.append(_finalize_deal({
                "title": title,
                "price": clean_p,
                "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
                "old_price": clean_op,
                "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
                "discount_pct": disc,
                "store": "Amazon Brasil",
                "url": f"https://www.amazon.com.br/dp/{asin}",
                "image": img_el.get("src", "") if img_el else "",
                "coupon": None,
                "category": "",
                "source": "Amazon Direto",
                "is_flash": disc >= 35,
                "is_bestseller": False,
                "likes": 0,
                "clicks": 0,
                "sales_count": 0,
                "sales_label": f"⭐ {rating:.1f} Amazon" if rating else "",
                "rating": rating,
            }))
            if len(deals) >= max_items:
                break
    except Exception:
        pass
    return deals


# ==============================================================================
# 6. SHOPEE AFFILIATE OFFICIAL OPEN API (GRAPHQL - OPCIONAL COM APP ID/SECRET)
# ==============================================================================

def fetch_shopee_open_api(app_id: str, app_secret: str, keyword: str = "", sort_type: int = 2, limit: int = 50) -> list:
    """
    Consulta a API Oficial Aberta de Afiliados da Shopee Brasil (productOfferV2).
    sort_type: 2 = Mais Vendidos (ITEM_SOLD_DESC), 5 = Maior Comissão (COMMISSION_DESC).
    Retorna produtos reais com vendas, estrelas, % desconto e link oficial de afiliado.
    """
    if not app_id or not app_secret:
        return []
    import time
    deals = []
    kw_arg = f'keyword: "{keyword}", ' if keyword else ""
    query = (
        f'query {{ productOfferV2({kw_arg}listType: 1, sortType: {sort_type}, page: 1, limit: {limit}) {{ '
        "nodes { itemId productName productLink offerLink imageUrl priceMin priceDiscountRate sales ratingStar commissionRate } "
        "} }"
    )
    payload_str = json.dumps({"query": query}, separators=(",", ":"))
    ts = int(time.time())
    sig = hashlib.sha256(f"{app_id}{ts}{payload_str}{app_secret}".encode("utf-8")).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id},Timestamp={ts},Signature={sig}",
    }
    try:
        r = requests.post("https://open-api.affiliate.shopee.com.br/graphql", data=payload_str, headers=headers, timeout=6)
        if r.status_code != 200:
            return deals
        nodes = r.json().get("data", {}).get("productOfferV2", {}).get("nodes", []) or []
        for n in nodes:
            title = (n.get("productName") or "").strip()
            p_val = float(n.get("priceMin") or 0)
            disc_pct = int(float(n.get("priceDiscountRate") or 0))
            clean_p, clean_op, real_disc = validate_and_sanitize_prices(p_val, None, disc_pct)
            if not title or clean_p <= 0:
                continue

            sales = int(n.get("sales") or 0)
            rating = float(n.get("ratingStar") or 0.0)
            offer_link = n.get("offerLink") or n.get("productLink") or ""
            deals.append(_finalize_deal({
                "title": title,
                "price": clean_p,
                "price_str": f"R$ {clean_p:.2f}".replace(".", ","),
                "old_price": clean_op,
                "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
                "discount_pct": real_disc,
                "store": "Shopee",
                "url": offer_link,
                "image": n.get("imageUrl") or "",
                "coupon": None,
                "category": keyword or "Shopee Oficial",
                "source": "Shopee API Oficial",
                "is_flash": real_disc >= 25,
                "is_bestseller": sales >= 50,
                "likes": 0,
                "clicks": 0,
                "sales_count": sales,
                "sales_label": f"🔥 {sales}+ vendidos • ⭐ {rating:.1f}",
                "rating": rating,
            }))
    except Exception:
        pass
    return deals


# ==============================================================================
# MOTOR PRINCIPAL ORQUESTRADO POR LOJA, NICHO E CRITÉRIOS DE QUALIDADE
# ==============================================================================

def _get_niche_cfg(niche_name: str) -> dict:
    if niche_name in NICHES:
        return NICHES[niche_name]
    # Mapeia títulos da aba Viral (VIRAL_CATALOG) para o nicho correspondente
    low = strip_accents(niche_name)
    if "beleza" in low:
        return NICHES["🌸 Beleza & Skincare"]
    if "casa" in low or "cozinha" in low:
        return NICHES["🏠 Casa, Cozinha & Eletro"]
    if "moda" in low:
        return NICHES["👗 Moda & Acessórios"]
    if "tecno" in low or "gamer" in low:
        return NICHES["📱 Celulares, Tech & Setup Gamer"]
    return NICHES["Todos os Nichos"]


def search_deals(
    selected_stores=None,
    niche="Todos os Nichos",
    min_discount=0,
    price_min=0,
    price_max=10000,
    search_keyword="",
    viral_mode=False,
    viral_category="",
    only_flash=False,
    only_discounted=False,
    sort_by="best",
    shopee_creds=None,
):
    """
    Motor Multi-Fonte em Paralelo alinhado com as páginas reais das lojas:
    - Mercado Livre Direto (/mais-vendidos + categorias /c/...)
    - Promobit API Oficial por Loja (/stores/{slug}/offers + /search) & Nicho HTML
    - Shopee Official Affiliate Open API (quando App ID + Secret configurados)
    - Pechinchou API JSON (+Vendas, +Curtidas, Urgentes)
    - Pelando Astro JSON (Comunidade Shopee, Shein e Nichos)
    - Amazon Brasil Mais Vendidos (/gp/bestsellers) & Ofertas Diretas
    """
    raw_deals = []
    tasks = []
    effective_niche = viral_category if (viral_mode and viral_category) else niche
    niche_cfg = _get_niche_cfg(effective_niche)
    niche_keywords = niche_cfg.get("keywords", [])
    stores = selected_stores if (selected_stores and "Todas as Lojas" not in selected_stores) else []
    kw_clean = search_keyword.strip()
    shp_id, shp_secret = shopee_creds if (shopee_creds and len(shopee_creds) == 2) else ("", "")

    with ThreadPoolExecutor(max_workers=16) as executor:
        # 0. Shopee Open API oficial se o usuário configurou App ID + Secret
        if shp_id and shp_secret and (not stores or any("shopee" in s.lower() for s in stores)):
            if kw_clean:
                tasks.append(executor.submit(fetch_shopee_open_api, shp_id, shp_secret, kw_clean, 2, 50))
            else:
                for skw in niche_cfg.get("shopee_kws", [""]):
                    tasks.append(executor.submit(fetch_shopee_open_api, shp_id, shp_secret, skw, 2, 50))

        # 1. Busca específica por Palavra-Chave digitada pelo usuário (Somente ML, Shopee e Shein)
        if kw_clean:
            tasks.append(executor.submit(fetch_promobit_search_api, kw_clean))
            tasks.append(executor.submit(fetch_pelando_feed, f"/busca/{kw_clean.replace(' ', '%20')}"))
            if not stores or any("mercado" in s.lower() for s in stores):
                tasks.append(executor.submit(fetch_mercadolivre_mais_vendidos, "Todos os Nichos"))
                for ml_cat in niche_cfg.get("ml_cats", [])[:2]:
                    tasks.append(executor.submit(fetch_mercadolivre_category, ml_cat))
                tasks.append(executor.submit(fetch_promobit_store_api, "mercado-livre", 2))
            if not stores or any("shopee" in s.lower() for s in stores):
                tasks.append(executor.submit(fetch_promobit_store_api, "shopee", 3))
                tasks.append(executor.submit(fetch_promobit_search_api, f"shopee {kw_clean}"))
            if not stores or any("shein" in s.lower() for s in stores):
                tasks.append(executor.submit(fetch_promobit_store_api, "shein", 2))
                tasks.append(executor.submit(fetch_promobit_search_api, f"shein {kw_clean}"))
            for p in range(1, 3):
                tasks.append(executor.submit(fetch_pechinchou_page, p))

        # 2. Busca por Lojas Específicas (Somente ML, Shopee e Shein)
        elif stores:
            for s in stores:
                sl = s.lower()
                if "shopee" in sl:
                    tasks.append(executor.submit(fetch_promobit_store_api, "shopee", 5))
                    tasks.append(executor.submit(fetch_pelando_feed, "/busca/shopee"))
                    tasks.append(executor.submit(fetch_pelando_feed, "/busca/shopee?page=2"))
                    tasks.append(executor.submit(fetch_pechinchou_page, 1))
                    if effective_niche != "Todos os Nichos":
                        niche_tokens = [tok for skw in niche_cfg.get("shopee_kws", []) for tok in skw.split()][:5]
                        for tok in niche_tokens:
                            tasks.append(executor.submit(fetch_promobit_search_api, f"shopee {tok}"))
                        for tok in niche_tokens[:2]:
                            tasks.append(executor.submit(fetch_pelando_feed, f"/busca/shopee%20{tok}"))
                elif "mercado" in sl:
                    tasks.append(executor.submit(fetch_mercadolivre_mais_vendidos, effective_niche))
                    ml_limit = 2 if effective_niche != "Todos os Nichos" else 1
                    for ml_cat in niche_cfg.get("ml_cats", [])[:ml_limit]:
                        tasks.append(executor.submit(fetch_mercadolivre_category, ml_cat))
                    tasks.append(executor.submit(fetch_promobit_store_api, "mercado-livre", 3))
                    for p in range(1, 3):
                        tasks.append(executor.submit(fetch_pechinchou_page, p))
                    for p in range(1, 5):
                        tasks.append(executor.submit(fetch_pechinchou_catalog, p))
                elif "shein" in sl:
                    tasks.append(executor.submit(fetch_promobit_store_api, "shein", 4))
                    tasks.append(executor.submit(fetch_promobit_search_api, "shein"))
                    tasks.append(executor.submit(fetch_pelando_feed, "/busca/shein"))
                    tasks.append(executor.submit(fetch_pelando_feed, "/busca/shein?page=2"))
                    if effective_niche != "Todos os Nichos":
                        shein_tokens = [tok for skw in niche_cfg.get("shopee_kws", []) for tok in skw.split()][:3]
                        for tok in shein_tokens:
                            tasks.append(executor.submit(fetch_promobit_search_api, f"shein {tok}"))

        # 3. Modo Viral ou "Todas as Lojas" (100% focado em Mercado Livre, Shopee e Shein)
        else:
            shopee_pages = 3 if effective_niche == "Todos os Nichos" else 4
            tasks.append(executor.submit(fetch_promobit_store_api, "shopee", shopee_pages))
            tasks.append(executor.submit(fetch_promobit_store_api, "mercado-livre", 2))
            tasks.append(executor.submit(fetch_promobit_store_api, "shein", 2))
            tasks.append(executor.submit(fetch_mercadolivre_mais_vendidos, effective_niche))
            tasks.append(executor.submit(fetch_pelando_feed, "/busca/shopee"))
            tasks.append(executor.submit(fetch_pelando_feed, "/busca/shein"))
            if effective_niche != "Todos os Nichos":
                for ml_cat in niche_cfg.get("ml_cats", [])[:1]:
                    tasks.append(executor.submit(fetch_mercadolivre_category, ml_cat))
                for skw in niche_cfg.get("shopee_kws", [])[:1]:
                    tok = skw.split()[0]
                    tasks.append(executor.submit(fetch_promobit_search_api, f"shopee {tok}"))
                    tasks.append(executor.submit(fetch_promobit_search_api, f"shein {tok}"))
            for pel_cat in niche_cfg.get("pelando_cats", ["recentes"])[:2]:
                tasks.append(executor.submit(fetch_pelando_feed, f"/c/{pel_cat}" if pel_cat != "recentes" else "/recentes"))
            for p in range(1, 3):
                tasks.append(executor.submit(fetch_pechinchou_page, p))
            for p in range(1, 5):
                tasks.append(executor.submit(fetch_pechinchou_catalog, p))

        for f in as_completed(tasks):
            try:
                res = f.result()
                if res:
                    raw_deals.extend(res)
            except Exception:
                pass

    filtered = []
    seen_titles = set()
    kw_norm = strip_accents(kw_clean)
    kw_tokens = [tok.rstrip("s") if len(tok) > 4 else tok for tok in kw_norm.split()]

    for d in raw_deals:
        # 0. Restringir estritamente às 3 lojas autorizadas: Mercado Livre, Shopee e Shein
        if d.get("store") not in ALLOWED_STORES:
            continue
        if "/messenger/" in (d.get("url") or "").lower():
            continue

        norm_title = strip_accents(d["title"])
        dedup_key = re.sub(r"[^a-z0-9]", "", norm_title[:30])
        if not dedup_key or dedup_key in seen_titles:
            continue

        # 1. Filtro por Loja (quando selecionada)
        if stores and not viral_mode:
            store_match = any(s.lower().split()[0] in d["store"].lower() for s in stores)
            if not store_match:
                continue

        # 2. Filtro por Palavra-Chave digitada (flexível a plural)
        if kw_tokens:
            text_to_check = f"{norm_title} {strip_accents(d.get('category', ''))} {strip_accents(d.get('store', ''))}"
            if not all(tok in text_to_check for tok in kw_tokens):
                continue

        # 3. Filtro por Nicho (usa tanto categoria real da loja quanto palavras-chave do título)
        if niche_keywords and not kw_norm:
            cat_norm = strip_accents(d.get("category", ""))
            niche_match = (
                cat_norm == strip_accents(effective_niche)
                or any(k in norm_title for k in niche_keywords)
                or any(slug.replace("-", " ") in cat_norm for slug in niche_cfg.get("pb_cats", []) + niche_cfg.get("ml_cats", []))
            )
            if not niche_match:
                continue

        # 4. Filtros de Desconto & Qualidade
        disc = d.get("discount_pct", 0) or 0
        if only_discounted and disc <= 0:
            continue
        if min_discount > 0 and disc < min_discount:
            continue
        if only_flash and not (d.get("is_flash") or d.get("is_bestseller") or disc >= 35):
            continue

        # 5. Filtro de Preço
        p = d.get("price", 0)
        if p > 0 and (p < price_min or p > price_max):
            continue

        seen_titles.add(dedup_key)
        filtered.append(d)

    # Ordenação inteligente pelos critérios selecionados
    if sort_by == "discount":
        filtered.sort(key=lambda x: (x.get("discount_pct", 0), x.get("quality_score", 0)), reverse=True)
    elif sort_by == "sales":
        filtered.sort(key=lambda x: (1 if x.get("is_bestseller") else 0, x.get("rating", 0.0), x.get("sales_count", 0), x.get("discount_pct", 0)), reverse=True)
    elif sort_by == "price_asc":
        filtered.sort(key=lambda x: x.get("price", 999999.0))
    else:
        filtered.sort(key=lambda x: (x.get("quality_score", 0), x.get("discount_pct", 0)), reverse=True)

    return filtered


def analyze_single_url(url: str) -> dict:
    """Analisa uma URL individual colada pelo usuário (com resolução de shortlinks)."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        clean_url = clean_product_url(url, resolve_redirects=True)
        target_url = clean_url if clean_url else url

        r = cffi_requests.get(target_url, headers=headers, impersonate="chrome124", timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        store_name = identify_store(target_url)

        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
        if not title and soup.find(id="productTitle"):
            title = soup.find(id="productTitle").get_text(strip=True)
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()

        img_url = ""
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img_url = og_img["content"]
        if not img_url and soup.find(id="landingImage"):
            img_url = soup.find(id="landingImage").get("src", "")

        price_val = 0.0
        old_price_val = None
        amz_whole = soup.find(class_="a-price-whole")
        if amz_whole:
            whole = amz_whole.get_text(strip=True)
            amz_frac = soup.find(class_="a-price-fraction")
            frac = amz_frac.get_text(strip=True) if amz_frac else "00"
            price_val = robust_parse_money(f"R$ {whole}{frac}")
            amz_basis = soup.select_one(".a-price.a-text-price:not(.a-size-mini) .a-offscreen")
            if amz_basis:
                old_price_val = robust_parse_money(amz_basis.get_text(strip=True))

        if not price_val:
            ml_curr = soup.select_one(".poly-price__current")
            if ml_curr:
                price_val = _parse_ml_amount(ml_curr)
                ml_old = soup.select_one(".andes-money-amount--previous")
                if ml_old:
                    old_price_val = _parse_ml_amount(ml_old)

        clean_p, clean_op, disc = validate_and_sanitize_prices(price_val, old_price_val)
        clean_img = sanitize_img_url(img_url, store_name)

        return {
            "success": True,
            "title": title or "Produto sem título",
            "price": clean_p,
            "price_str": f"R$ {clean_p:.2f}".replace(".", ",") if clean_p else "Confira",
            "old_price": clean_op,
            "old_price_str": f"R$ {clean_op:.2f}".replace(".", ",") if clean_op else "",
            "discount_pct": disc,
            "store": store_name,
            "image": clean_img,
            "url": target_url,
            "is_viral": is_viral_item(title),
            "coupon": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "store": identify_store(url),
            "url": url,
        }
