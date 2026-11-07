import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from functools import lru_cache
import requests
from bs4 import BeautifulSoup

def identify_store(url: str) -> str:
    url_lower = url.lower()
    if any(k in url_lower for k in ["amazon.com", "link.amazon", "amzn.to"]):
        return "Amazon Brasil"
    elif any(k in url_lower for k in ["mercadolivre.com", "mercadolibre.com", "meli.la"]):
        return "Mercado Livre"
    elif "shopee.com" in url_lower:
        return "Shopee"
    elif any(k in url_lower for k in ["magazineluiza.com", "magazinevoce.com"]):
        return "Magazine Luiza"
    elif "casasbahia.com" in url_lower:
        return "Casas Bahia"
    elif "shein.com" in url_lower:
        return "Shein"
    elif "aliexpress.com" in url_lower:
        return "AliExpress"
    elif "dafiti.com" in url_lower:
        return "Dafiti"
    return "Loja Parceira"


@lru_cache(maxsize=2048)
def resolve_unshorten_url(url: str, max_depth: int = 3) -> str:
    """Resolve links encurtados (link.amazon, amzn.to, meli.la, s.shopee) para o link final real."""
    if not url:
        return ""
    
    current = url
    try:
        # Se for meli.la, segue e pega o produto real
        if "meli.la" in current:
            r = requests.get(current, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if "/social/" in r.url:
                # Na página de perfil social do ML, o link do produto está no HTML
                soup = BeautifulSoup(r.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    if '/MLB-' in a['href'] or '/p/MLB' in a['href']:
                        return a['href'].split('?')[0].split('#')[0]
            current = r.url
            
        elif any(k in current for k in ["link.amazon", "amzn.to", "s.shopee.com.br", "bit.ly", "t.co", "tinyurl"]):
            r = requests.get(current, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            current = r.url
    except Exception as e:
        pass
        
    return current


@lru_cache(maxsize=2048)
def clean_product_url(url: str, resolve_redirects: bool = False) -> str:
    """Limpa tags de terceiros, subids e parâmetros de tracking para manter a URL limpa do produto."""
    if not url:
        return ""
        
    # Resolver se for shortlink apenas quando explicitamente solicitado (ex: aba de link único)
    final_url = resolve_unshorten_url(url) if resolve_redirects else url
    
    # 1. Amazon: Extrair /dp/ASIN limpo
    if "amazon.com" in final_url:
        m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', final_url)
        if m:
            return f"https://www.amazon.com.br/dp/{m.group(1)}"
        # Se não achou ASIN, remove parâmetros de afiliados de terceiros
        clean = re.sub(r'([?&])(?:tag|ascsubtag|linkCode|linkId)=[^&]*', '', final_url)
        clean = clean.replace("?&", "?").rstrip("?&")
        return clean
        
    # 2. Mercado Livre: Extrair /p/MLB... ou /MLB-...
    if "mercadolivre.com" in final_url:
        # Se tiver /p/MLBxxxx ou /MLB-xxxx
        m = re.search(r'(https://www\.mercadolivre\.com\.br/[^?#]+(?:/p/MLB\d+|MLB-\d+-[^?#]+))', final_url)
        if m:
            return m.group(1)
        # Limpar parâmetros de terceiros
        clean = re.sub(r'([?&])(?:matt_tool|matt_word|forceInApp|ref)=[^&]*', '', final_url)
        clean = clean.replace("?&", "?").rstrip("?&")
        return clean.split('#')[0]
        
    # 3. Shopee: Manter caminho base limpo
    if "shopee.com" in final_url:
        clean = re.sub(r'([?&])(?:af_sub_siteid|af_c_id|sub_id|universal-link)=[^&]*', '', final_url)
        clean = clean.replace("?&", "?").rstrip("?&")
        return clean.split('?')[0] if '?' in clean and 'product/' in clean else clean
        
    # 4. Outras lojas: Limpar query invasivas
    parsed = urlparse(final_url)
    # Se tiver tracking conhecido (utm_, tag, aff, etc)
    if parsed.query:
        qs = parse_qs(parsed.query)
        cleaned_qs = {k: v for k, v in qs.items() if not k.startswith("utm_") and k not in ["tag", "aff_id", "subid", "ref"]}
        new_query = urlencode(cleaned_qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))
        
    return final_url


def convert_to_affiliate(url: str, store_name: str, config: dict) -> dict:
    """
    Converte qualquer URL em link de afiliado oficial do usuário ou link limpo direto.
    """
    clean_url = clean_product_url(url)
    detected_store = identify_store(clean_url if clean_url else url)
    final_store = detected_store if detected_store != "Loja Parceira" else store_name
    
    tags = config.get("affiliate_tags", {})
    store_lower = final_store.lower().replace(" ", "").replace("-", "")
    
    tag_key = None
    if "amazon" in store_lower:
        tag_key = "amazon"
    elif "mercado" in store_lower or "livre" in store_lower:
        tag_key = "mercadolivre"
    elif "shopee" in store_lower:
        tag_key = "shopee"
    elif "magalu" in store_lower or "magazine" in store_lower:
        tag_key = "magalu"
    elif "casas" in store_lower or "bahia" in store_lower:
        tag_key = "casasbahia"
    elif "shein" in store_lower:
        tag_key = "shein"
    elif "aliexpress" in store_lower:
        tag_key = "aliexpress"
    elif "dafiti" in store_lower:
        tag_key = "dafiti"
        
    tag_value = tags.get(tag_key, "").strip() if tag_key else ""
    
    # Se usuário ainda não cadastrou a tag para essa loja:
    if not tag_value:
        return {
            "url": clean_url,
            "clean_url": clean_url,
            "is_tagged": False,
            "store": final_store,
            "status": f"Link limpo direto (Sem tag cadastrada para {final_store})"
        }
        
    # 1. Amazon
    if tag_key == "amazon":
        sep = "&" if "?" in clean_url else "?"
        aff_url = f"{clean_url}{sep}tag={tag_value}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": final_store,
            "status": f"Tag Amazon aplicada: {tag_value}"
        }
        
    # 2. Magazine Luiza (Magazine Você)
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
            "status": f"Loja Magazine Você aplicada: {tag_value}"
        }
        
    # 3. Mercado Livre
    if tag_key == "mercadolivre":
        sep = "&" if "?" in clean_url else "?"
        aff_url = f"{clean_url}{sep}matt_tool={tag_value}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": final_store,
            "status": f"Código Mercado Livre aplicado: {tag_value}"
        }
        
    # 4. Shopee
    if tag_key == "shopee":
        sep = "&" if "?" in clean_url else "?"
        aff_url = f"{clean_url}{sep}universal-link=true&sub_id={tag_value}"
        return {
            "url": aff_url,
            "clean_url": clean_url,
            "is_tagged": True,
            "store": final_store,
            "status": f"Tag Shopee aplicada: {tag_value}"
        }
        
    # 5. Outras Lojas
    sep = "&" if "?" in clean_url else "?"
    aff_url = f"{clean_url}{sep}aff_id={tag_value}"
    return {
        "url": aff_url,
        "clean_url": clean_url,
        "is_tagged": True,
        "store": final_store,
        "status": f"Tag {final_store} aplicada: {tag_value}"
    }
