import base64
import io
import urllib.parse
from functools import lru_cache

import requests
from PIL import Image

_IMG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/jpeg,image/*,*/*;q=0.8",
}


def generate_wa_link(message: str, phone: str = "", target_mode: str = "web") -> str:
    """
    Gera link direto para envio no WhatsApp.
    target_mode:
      - 'web': Abre DIRETAMENTE no WhatsApp Web (https://web.whatsapp.com/send?text=...)
      - 'app': Abre direto o aplicativo instalado no Windows (whatsapp://send?text=...)
      - 'universal': Link padrão (https://api.whatsapp.com/send?text=...)
    """
    encoded_text = urllib.parse.quote(message)
    clean_phone = "".join(filter(str.isdigit, phone)) if phone else ""

    if target_mode == "app":
        phone_param = f"&phone={clean_phone}" if clean_phone else ""
        return f"whatsapp://send?text={encoded_text}{phone_param}"

    if target_mode == "web":
        if clean_phone:
            return f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
        return f"https://web.whatsapp.com/send?text={encoded_text}"

    if clean_phone:
        return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
    return f"https://api.whatsapp.com/send?text={encoded_text}"


@lru_cache(maxsize=64)
def download_jpeg_bytes_cached(image_url: str) -> bytes | None:
    """Baixa imagem (inclusive WebP do Pelando/ML ou bloqueada por UA) e converte para JPEG real para o WhatsApp."""
    if not image_url or not str(image_url).startswith("http"):
        return None
    raw_bytes = None
    try:
        r = requests.get(image_url, headers=_IMG_HEADERS, timeout=6)
        if r.status_code == 200 and r.content and not r.headers.get("Content-Type", "").startswith("text/html"):
            raw_bytes = r.content
    except Exception:
        pass

    if not raw_bytes:
        try:
            from curl_cffi import requests as cffi_requests
            r2 = cffi_requests.get(image_url, impersonate="chrome124", timeout=7)
            if r2.status_code == 200 and r2.content and not r2.headers.get("Content-Type", "").startswith("text/html"):
                raw_bytes = r2.content
        except Exception:
            pass

    if not raw_bytes:
        return None

    try:
        im = Image.open(io.BytesIO(raw_bytes))
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "P":
                im = im.convert("RGBA")
            if im.mode in ("RGBA", "LA"):
                bg.paste(im, mask=im.split()[-1])
            else:
                bg.paste(im)
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        return None


def _build_media_payload(api_type: str, endpoint: str, target_group: str, media_value: str, caption: str) -> dict:
    if "evolution" in api_type or "evolution" in endpoint:
        return {
            "number": target_group,
            "media": media_value,
            "mediatype": "image",
            "mimetype": "image/jpeg",
            "fileName": "oferta.jpg",
            "caption": caption,
        }
    if "z-api" in api_type or "z-api" in endpoint:
        return {
            "phone": target_group,
            "image": media_value,
            "caption": caption,
        }
    return {
        "to": target_group,
        "image_url": media_value if media_value.startswith("http") else "",
        "image_base64": "" if media_value.startswith("http") else media_value,
        "caption": caption,
        "text": caption,
    }


def send_whatsapp_media_api(config: dict, image_url: str, caption: str, group_id: str = "") -> dict:
    from services.scraper import sanitize_img_url
    image_url = sanitize_img_url(image_url)

    wa_cfg = config.get("whatsapp", {})
    endpoint = wa_cfg.get("api_endpoint", "").strip() or wa_cfg.get("webhook_url", "").strip()
    api_token = wa_cfg.get("api_token", "").strip()
    target_group = group_id.strip() or wa_cfg.get("target_group", "").strip()
    api_type = wa_cfg.get("api_type", "evolution").lower()

    if not endpoint:
        return {"success": False, "error": "Endpoint da API do WhatsApp não configurado nas Configurações."}
    if not target_group:
        return {"success": False, "error": "ID do Grupo / Telefone de destino não configurado."}

    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["apikey"] = api_token
        headers["Authorization"] = f"Bearer {api_token}"

    # Converte WebP/Pelando/imagens protegidas para JPEG Base64 (resolve falha de foto/sticker no WhatsApp)
    jpeg_bytes = download_jpeg_bytes_cached(image_url) if image_url else None
    is_evolution = ("evolution" in api_type or "evolution" in endpoint)
    is_zapi = ("z-api" in api_type or "z-api" in endpoint)

    if jpeg_bytes and (is_evolution or is_zapi):
        b64_raw = base64.b64encode(jpeg_bytes).decode("ascii")
        media_val = b64_raw if is_evolution else f"data:image/jpeg;base64,{b64_raw}"
    else:
        media_val = image_url

    payload = _build_media_payload(api_type, endpoint, target_group, media_val, caption)

    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=14)
        # Fallback caso servidor antigo espere URL direta em vez de base64
        if r.status_code not in (200, 201) and image_url and media_val != image_url:
            fallback_payload = _build_media_payload(api_type, endpoint, target_group, image_url, caption)
            r = requests.post(endpoint, json=fallback_payload, headers=headers, timeout=14)
        return {
            "success": r.status_code in [200, 201],
            "status_code": r.status_code,
            "response": r.text[:250],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_batch_super_message(deals: list, config: dict) -> str:
    from services.affiliate import convert_to_affiliate

    handle = config.get("instagram", {}).get("handle", "@mimozae.of")
    group_link = config.get("whatsapp", {}).get("group_link", "")

    count = min(len(deals), 10)
    lines = [
        f"🔥 *TOP {count} ACHADINHOS IMPERDÍVEIS DO DIA!* 🔥",
        f"⚡ _Promoções selecionadas a dedo para você ({handle})_",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for idx, d in enumerate(deals[:10]):
        title = d.get("title", "").strip()
        price = d.get("price_str") or f"R$ {d.get('price', 0):.2f}".replace(".", ",")
        old_price = d.get("old_price_str") or ""
        disc = d.get("discount_pct", 0)
        store = d.get("store", "Loja Oficial")
        coupon = d.get("coupon")

        aff_res = convert_to_affiliate(
            d.get("url", ""),
            store,
            config,
            resolve_redirects=True,
            is_own_shopee_api_link=(d.get("source") == "Shopee API Oficial"),
        )
        link = aff_res["url"]

        disc_txt = f" (-{disc}% OFF)" if disc else ""
        num_icon = num_emojis[idx] if idx < len(num_emojis) else f"*{idx+1}.*"
        lines.append(f"{num_icon} *{title}*")
        if old_price and old_price != price:
            lines.append(f"❌ De: ~{old_price}~ 👉 *Por: {price}*{disc_txt}")
        else:
            lines.append(f"🔥 *Por: {price}*{disc_txt}")

        if coupon:
            lines.append(f"🎟️ Cupom: *{coupon}*")
        lines.append(f"🛒 *Link Seguro:* {link}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    if group_link:
        lines.append(f"👥 _Entre no nosso Grupo VIP de Achadinhos:_ {group_link}")

    return "\n".join(lines)
