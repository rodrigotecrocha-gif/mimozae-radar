import json
import re
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from services.affiliate import identify_store, clean_product_url

# Catálogo Curado de Produtos Altamente Virais e com Grande Recorrência de Compra
VIRAL_CATALOG = {
    "🌸 Beleza & Skincare (Alta Recorrência)": [
        "lola cosmetics",
        "cerave",
        "principia",
        "escova secadora",
        "oleo extraordinario elseve",
        "morte subita lola",
        "protetor solar neutrogena",
        "darrow actine",
        "boca rosa po",
        "truss uso obrigatorio",
        "curvex eletrico"
    ],
    "🏠 Casa, Cozinha & Gadgets (Achadinhos)": [
        "mini processador eletrico",
        "tapete silicone airfryer",
        "garrafa termica 2l",
        "copo termico",
        "dispenser detergente",
        "potes hermeticos",
        "mop giratorio",
        "organizador acrilico giratorio",
        "luminaria sensor presenca",
        "aspirador portatil sem fio"
    ],
    "👗 Moda & Acessórios (TikTok Trends)": [
        "meia calca termica peluciada",
        "conjunto canelado fitness",
        "bolsa transversal nylon",
        "body modelador afina cintura",
        "tenis feminino casual branco",
        "sutia invisivel adesivo",
        "oculos sol retangular"
    ]
}

NICHES = {
    "Todos os Nichos": [],
    "🌸 Beleza & Skincare": ["beleza", "cabelo", "pele", "perfume", "maquiagem", "lola", "cerave", "principia", "protetor", "shampoo", "creme", "oleo", "batom"],
    "🏠 Casa, Cozinha & Gadgets": ["casa", "cozinha", "panela", "cafeteira", "airfryer", "aspirador", "ventilador", "processador", "garrafa", "copo", "potes", "mop", "organizador"],
    "👗 Moda & Acessórios": ["moda", "vestido", "calçado", "tênis", "bolsa", "meia-calça", "conjunto", "body", "cinto", "óculos"],
    "🎮 Tecnologia & Setup": ["teclado", "mouse", "gamer", "headset", "monitor", "notebook", "ssd", "alexa", "fone bluetooth", "smartwatch"]
}

# Sessão HTTP reutilizável com pool de conexões
_SESSION = None
def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
        _SESSION.mount("https://", adapter)
        _SESSION.mount("http://", adapter)
    return _SESSION

def sanitize_img_url(img_url: str, source: str = "") -> str:
    """Higieniza URLs de imagens para garantir protocolo absoluto https:// e evitar MediaFileStorageError."""
    if not img_url:
        return ""
    s = str(img_url).strip()
    if s.startswith("//"):
        return f"https:{s}"
    if s.startswith("http://") or s.startswith("https://"):
        return s
        
    clean_path = s.lstrip('/')
    if s.startswith('/static/'):
        return f"https://www.promobit.com.br{s}"
    if s.startswith('/fotos/') or "gatry" in source.lower():
        return f"https://gatry.com/{clean_path}"
    if re.match(r'^\d+\.(?:png|jpe?g|webp)$', clean_path, re.IGNORECASE) or "promobit" in source.lower():
        return f"https://i.promobit.com.br/{clean_path}"
    if s.startswith('/'):
        return f"https://i.promobit.com.br/{clean_path}"
    return f"https://{clean_path}"

def robust_parse_money(txt: str) -> float:
    """Extrai com segurança valores numéricos em Reais, ignorando frações de unidade (ex: /ml, /g)."""
    if not txt:
        return 0.0
    s = str(txt).strip()
    if "/" in s:
        s = s.split("/")[0]
        
    m = re.search(r'R\$\s*([\d\.,]+)', s)
    if not m:
        m = re.search(r'([\d\.,]+)', s)
        
    if m:
        raw_num = m.group(1).strip().rstrip('.,')
        if ',' in raw_num and '.' in raw_num:
            if raw_num.rfind(',') > raw_num.rfind('.'):
                raw_num = raw_num.replace('.', '').replace(',', '.')
            else:
                raw_num = raw_num.replace(',', '')
        elif ',' in raw_num:
            raw_num = raw_num.replace(',', '.')
        try:
            return float(raw_num)
        except:
            pass
    return 0.0

def validate_and_sanitize_prices(price: float, old_price: float, discount_pct: int = 0):
    """
    Higienização rigorosa contra bugs de preços:
    - Impede que 'De' seja menor ou igual a 'Por'
    - Descarta valores dummy como 0.01 ou 0 do Promobit
    - Calcula o desconto real matematicamente
    """
    if price < 1.0:
        if old_price and old_price > 10.0:
            price = old_price
            old_price = None
        else:
            return 0.0, None, 0
            
    # Preço antigo inválido (ex: 0.01, menor que preço atual, ou igual)
    if old_price is not None:
        if old_price <= 1.0 or old_price <= (price * 1.05) or old_price > (price * 6.0):
            old_price = None
            
    real_disc = 0
    if old_price and old_price > price > 0:
        real_disc = int(round(((old_price - price) / old_price) * 100))
    elif discount_pct and 0 < discount_pct < 95:
        real_disc = int(discount_pct)
        if not old_price and real_disc >= 10:
            estimated_old = price / (1.0 - (real_disc / 100.0))
            if estimated_old > price:
                old_price = round(estimated_old, 2)
        
    return round(price, 2), round(old_price, 2) if old_price else None, real_disc

def normalize_store_name(raw: str, url: str = "") -> str:
    combined = (str(raw or "") + " " + str(url or "")).lower()
    if "amazon" in combined:
        return "Amazon Brasil"
    elif "mercado" in combined or "livre" in combined or "meli" in combined:
        return "Mercado Livre"
    elif "shopee" in combined:
        return "Shopee"
    elif "magalu" in combined or "magazine" in combined:
        return "Magazine Luiza"
    elif "casas" in combined or "bahia" in combined:
        return "Casas Bahia"
    elif "shein" in combined:
        return "Shein"
    elif "aliexpress" in combined:
        return "AliExpress"
    elif "dafiti" in combined:
        return "Dafiti"
    elif raw:
        return str(raw).strip()
    return "Loja Parceira"

def is_viral_item(title: str) -> bool:
    title_lower = title.lower()
    for cat_items in VIRAL_CATALOG.values():
        for kw in cat_items:
            parts = kw.split()
            if all(p in title_lower for p in parts):
                return True
    return False

def fetch_amazon_direct(query="ofertas", min_discount=0, max_items=12):
    deals = []
    try:
        rh_filter = "&rh=p_8%3A2253952011" if min_discount >= 30 else ("&rh=p_8%3A2253951011" if min_discount >= 15 else "")
        url = f"https://www.amazon.com.br/s?k={query.replace(' ', '+')}{rh_filter}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        r = cffi_requests.get(url, headers=headers, impersonate="chrome124", timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.select('div[data-asin]')
            for c in cards:
                asin = c.get('data-asin')
                if not asin or len(asin) != 10:
                    continue
                title_el = c.select_one('h2 span')
                price_el = c.select_one('.a-price .a-offscreen')
                old_p_el = c.select_one('.a-price.a-text-price:not(.a-size-mini) .a-offscreen')
                img_el = c.select_one('img.s-image')
                
                if title_el and price_el:
                    title = title_el.get_text(strip=True)
                    price_raw = price_el.get_text(strip=True)
                    old_p_raw = old_p_el.get_text(strip=True) if old_p_el else ""
                    
                    p_val = robust_parse_money(price_raw)
                    op_val = robust_parse_money(old_p_raw) if old_p_raw else None
                    
                    clean_p, clean_op, disc = validate_and_sanitize_prices(p_val, op_val)
                    if clean_p <= 0:
                        continue
                        
                    raw_img = img_el.get('src', '') if img_el else ''
                    clean_img = sanitize_img_url(raw_img, 'amazon')
                    
                    deals.append({
                        'title': title,
                        'price': clean_p,
                        'price_str': f"R$ {clean_p:.2f}".replace('.', ','),
                        'old_price': clean_op,
                        'old_price_str': f"R$ {clean_op:.2f}".replace('.', ',') if clean_op else "",
                        'discount_pct': disc,
                        'store': 'Amazon Brasil',
                        'url': f"https://www.amazon.com.br/dp/{asin}",
                        'image': clean_img,
                        'coupon': None,
                        'is_viral': is_viral_item(title),
                        'category': '',
                        'source': 'Amazon Direto'
                    })
                    if len(deals) >= max_items:
                        break
    except Exception as e:
        pass
    return deals

def fetch_gatry_url(url: str):
    deals = []
    session = get_session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = session.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for art in soup.find_all('article'):
                desc = art.select_one('.description')
                if not desc:
                    continue
                title_a = desc.select_one('h3 a')
                if not title_a:
                    continue
                title = title_a.get_text(strip=True)
                
                store_el = desc.select_one('.option-store a')
                store_url = store_el.get('href', '') if store_el else ''
                title_url = title_a.get('href', '')
                
                product_url = ""
                if store_url and store_url.startswith("http"):
                    product_url = store_url
                elif title_url and title_url.startswith("http"):
                    product_url = title_url
                else:
                    product_url = f"https://gatry.com{title_url}"
                    
                img_el = art.select_one('.image img')
                raw_img = img_el.get('src', '') if img_el else ''
                clean_img = sanitize_img_url(raw_img, 'gatry')
                
                price_el = desc.select_one('.price')
                price_text = price_el.get_text(strip=True) if price_el else ''
                price_val = robust_parse_money(price_text)
                
                store_raw = store_el.get_text(strip=True).replace('Ir para', '').strip() if store_el else ''
                detected_store = normalize_store_name(store_raw, product_url)
                
                comment_el = desc.select_one('.comment')
                coupon = None
                if comment_el:
                    m = re.search(r'(?:cupom|código|cupom:)\s*[:=]?\s*([A-Z0-9_\-]+)', comment_el.get_text(), re.I)
                    if m:
                        coupon = m.group(1).upper()
                        
                disc = 0
                m_disc = re.search(r'(\d+)%\s*off', title.lower())
                if m_disc:
                    disc = int(m_disc.group(1))
                    
                clean_p, clean_op, real_disc = validate_and_sanitize_prices(price_val, None, disc)
                if clean_p <= 0:
                    continue
                    
                deals.append({
                    'title': title,
                    'price': clean_p,
                    'price_str': f"R$ {clean_p:.2f}".replace('.', ','),
                    'old_price': None,
                    'old_price_str': "",
                    'discount_pct': real_disc,
                    'store': detected_store,
                    'url': product_url,
                    'image': clean_img,
                    'coupon': coupon,
                    'is_viral': is_viral_item(title),
                    'category': "",
                    'source': 'Gatry'
                })
    except Exception as e:
        pass
    return deals

def fetch_promobit_live(query: str = ""):
    deals = []
    session = get_session()
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://www.promobit.com.br/busca/?q={query.replace(' ', '+')}" if query else "https://www.promobit.com.br"
    try:
        r = session.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                data = json.loads(script.string)
                page_props = data.get('props', {}).get('pageProps', {})
                offers = page_props.get('serverOffers', {}).get('offers', [])
                if not offers:
                    offers = page_props.get('serverTimeline', {}).get('data', [])
                    
                for o in offers:
                    title = o.get('offerTitle', '')
                    price = float(o.get('offerPrice', 0) or 0)
                    raw_old_price = o.get('offerOldPrice')
                    old_price = float(raw_old_price) if raw_old_price and float(raw_old_price) > 1.0 else None
                    disc = int(float(o.get('offerDiscontPercentage', 0) or 0))
                    
                    clean_p, clean_op, real_disc = validate_and_sanitize_prices(price, old_price, disc)
                    if clean_p <= 0:
                        continue
                        
                    store = o.get('storeName', 'Outra')
                    offer_id = o.get('offerId')
                    if offer_id:
                        item_url = f"https://www.promobit.com.br/Redirect/to/{offer_id}/"
                    else:
                        slug = o.get('offerSlug', '')
                        item_url = f"https://www.promobit.com.br/oferta/{slug}/"
                        
                    raw_photo = o.get('offerPhoto', '')
                    clean_photo = sanitize_img_url(raw_photo, 'promobit')
                    
                    deals.append({
                        'title': title,
                        'price': clean_p,
                        'price_str': f"R$ {clean_p:.2f}".replace('.', ','),
                        'old_price': clean_op,
                        'old_price_str': f"R$ {clean_op:.2f}".replace('.', ',') if clean_op else "",
                        'discount_pct': real_disc,
                        'store': normalize_store_name(store, item_url),
                        'url': item_url,
                        'image': clean_photo,
                        'coupon': o.get('offerCoupon'),
                        'is_viral': is_viral_item(title),
                        'category': o.get('categoryName', ''),
                        'source': 'Promobit'
                    })
    except Exception as e:
        pass
    return deals

def search_deals(
    selected_stores=None,
    niche="Todos os Nichos",
    min_discount=0,
    price_min=0,
    price_max=10000,
    search_keyword="",
    viral_mode=False,
    viral_category=""
):
    raw_deals = []
    tasks = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        if viral_mode:
            keywords_to_query = []
            if viral_category and viral_category in VIRAL_CATALOG:
                keywords_to_query = VIRAL_CATALOG[viral_category]
            else:
                keywords_to_query = [
                    "lola cosmetics", "cerave", "mini processador", "garrafa termica",
                    "potes hermeticos", "copo termico", "tapete airfryer", "escova secadora",
                    "meia calca termica", "principia", "dispenser detergente"
                ]
                
            for kw in keywords_to_query[:8]:
                tasks.append(executor.submit(fetch_amazon_direct, kw, min_discount, 4))
                tasks.append(executor.submit(fetch_gatry_url, f"https://gatry.com/?q={kw.replace(' ', '+')}"))
                
        elif search_keyword:
            tasks.append(executor.submit(fetch_amazon_direct, search_keyword, min_discount, 12))
            tasks.append(executor.submit(fetch_gatry_url, f"https://gatry.com/?q={search_keyword.replace(' ', '+')}"))
            tasks.append(executor.submit(fetch_gatry_url, f"https://gatry.com/?q={search_keyword.replace(' ', '+')}&page=2"))
            tasks.append(executor.submit(fetch_promobit_live, search_keyword))
            
        else:
            stores = selected_stores if (selected_stores and "Todas as Lojas" not in selected_stores) else []
            if not stores:
                tasks.append(executor.submit(fetch_amazon_direct, "ofertas", min_discount, 15))
                tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com"))
                tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/promocoes?page=2"))
                tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/promocoes?page=3"))
                tasks.append(executor.submit(fetch_promobit_live, ""))
                for s_term in ["shopee", "mercado livre", "casas bahia", "aliexpress"]:
                    tasks.append(executor.submit(fetch_gatry_url, f"https://gatry.com/?q={s_term}"))
            else:
                for s in stores:
                    s_lower = s.lower()
                    if "amazon" in s_lower:
                        tasks.append(executor.submit(fetch_amazon_direct, "ofertas", min_discount, 20))
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=amazon"))
                    elif "mercado" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=mercado+livre"))
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=mercado+livre&page=2"))
                    elif "shopee" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=shopee"))
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=shopee&page=2"))
                    elif "magalu" in s_lower or "magazine" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=magalu"))
                    elif "casas" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=casas+bahia"))
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=casas+bahia&page=2"))
                    elif "shein" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=shein"))
                    elif "aliexpress" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=aliexpress"))
                    elif "dafiti" in s_lower:
                        tasks.append(executor.submit(fetch_gatry_url, "https://gatry.com/?q=dafiti"))
                        
        for f in as_completed(tasks):
            try:
                res = f.result()
                if res:
                    raw_deals.extend(res)
            except Exception:
                pass

    filtered = []
    seen_titles = set()
    niche_keywords = NICHES.get(niche, [])
    
    for d in raw_deals:
        norm_title = re.sub(r'[^a-zA-Z0-9]', '', d['title'].lower()[:32])
        if norm_title in seen_titles:
            continue
        seen_titles.add(norm_title)
        
        if selected_stores and "Todas as Lojas" not in selected_stores and not viral_mode:
            store_match = any(s.lower() in d['store'].lower() for s in selected_stores)
            if not store_match:
                continue
                
        if niche_keywords and not viral_mode:
            text_to_check = (d['title'] + " " + d.get('category', '')).lower()
            if not any(k in text_to_check for k in niche_keywords):
                continue
                
        if min_discount > 0:
            disc = d.get('discount_pct', 0)
            if disc > 0 and disc < min_discount:
                continue
            elif disc == 0 and min_discount >= 35:
                continue
                
        p = d.get('price', 0)
        if p > 0:
            if p < price_min or p > price_max:
                continue
                
        d['image'] = sanitize_img_url(d.get('image', ''), d.get('store', ''))
        filtered.append(d)
        
    filtered.sort(key=lambda x: (x.get('is_viral', False), x.get('discount_pct', 0) or 0), reverse=True)
    return filtered


def analyze_single_url(url: str) -> dict:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        clean_url = clean_product_url(url)
        target_url = clean_url if clean_url else url
        
        r = cffi_requests.get(target_url, headers=headers, impersonate="chrome124", timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        store_name = identify_store(target_url)
        
        title = ""
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content']
        if not title and soup.find(id='productTitle'):
            title = soup.find(id='productTitle').get_text(strip=True)
        if not title and soup.title:
            title = soup.title.string.strip()
            
        img_url = ""
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            img_url = og_img['content']
        if not img_url and soup.find(id='landingImage'):
            img_url = soup.find(id='landingImage').get('src', '')
            
        price_val = 0.0
        old_price_val = None
        
        amz_whole = soup.find(class_='a-price-whole')
        if amz_whole:
            whole = amz_whole.get_text(strip=True)
            amz_frac = soup.find(class_='a-price-fraction')
            frac = amz_frac.get_text(strip=True) if amz_frac else "00"
            price_val = robust_parse_money(f"R$ {whole}{frac}")
            
            amz_basis = soup.select_one('.a-price.a-text-price:not(.a-size-mini) .a-offscreen')
            if amz_basis:
                old_price_val = robust_parse_money(amz_basis.get_text(strip=True))
                
        if not price_val:
            ml_curr = soup.select_one('.poly-price__current .andes-money-amount__fraction, .ui-pdp-price__second-line .andes-money-amount__fraction')
            if ml_curr:
                price_val = robust_parse_money(ml_curr.get_text(strip=True))
                ml_old = soup.select_one('.andes-money-amount--previous .andes-money-amount__fraction')
                if ml_old:
                    old_price_val = robust_parse_money(ml_old.get_text(strip=True))
                    
        clean_p, clean_op, disc = validate_and_sanitize_prices(price_val, old_price_val)
        clean_img = sanitize_img_url(img_url, store_name)
        
        return {
            "success": True,
            "title": title or "Produto sem título",
            "price": clean_p,
            "price_str": f"R$ {clean_p:.2f}".replace('.', ',') if clean_p else "Confira",
            "old_price": clean_op,
            "old_price_str": f"R$ {clean_op:.2f}".replace('.', ',') if clean_op else "",
            "discount_pct": disc,
            "store": store_name,
            "image": clean_img,
            "url": target_url,
            "is_viral": is_viral_item(title),
            "coupon": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "store": identify_store(url),
            "url": url
        }
