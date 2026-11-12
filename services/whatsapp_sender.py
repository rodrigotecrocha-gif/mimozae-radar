import urllib.parse
import requests
import time

def generate_wa_link(message: str, phone: str = "", target_mode: str = "web") -> str:
    """
    Gera link direto para envio no WhatsApp.
    target_mode:
      - 'web': Abre DIRETAMENTE no WhatsApp Web (https://web.whatsapp.com/send?text=...), 
               eliminando 100% da tela intermediária 'Compartilhe no WhatsApp' / 'Abrir app'!
      - 'app': Abre direto o aplicativo instalado no Windows (whatsapp://send?text=...)
      - 'universal': Link padrão (https://api.whatsapp.com/send?text=...)
    """
    encoded_text = urllib.parse.quote(message)
    clean_phone = "".join(filter(str.isdigit, phone)) if phone else ""
    
    if target_mode == "app":
        phone_param = f"&phone={clean_phone}" if clean_phone else ""
        return f"whatsapp://send?text={encoded_text}{phone_param}"
        
    elif target_mode == "web":
        if clean_phone:
            return f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
        return f"https://web.whatsapp.com/send?text={encoded_text}"
        
    else: # universal api.whatsapp.com
        if clean_phone:
            return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
        return f"https://api.whatsapp.com/send?text={encoded_text}"

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
        
    headers = {
        "Content-Type": "application/json"
    }
    if api_token:
        headers["apikey"] = api_token
        headers["Authorization"] = f"Bearer {api_token}"
        
    payload = {}
    if "evolution" in api_type or "evolution" in endpoint:
        payload = {
            "number": target_group,
            "media": image_url,
            "mediatype": "image",
            "caption": caption
        }
    elif "z-api" in api_type or "z-api" in endpoint:
        payload = {
            "phone": target_group,
            "image": image_url,
            "caption": caption
        }
    else:
        payload = {
            "to": target_group,
            "image_url": image_url,
            "caption": caption,
            "text": caption
        }
        
    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=12)
        return {
            "success": r.status_code in [200, 201],
            "status_code": r.status_code,
            "response": r.text[:200]
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
        ""
    ]
    
    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for idx, d in enumerate(deals[:10]):
        title = d.get("title", "").strip()
        price = d.get("price_str") or f"R$ {d.get('price', 0):.2f}".replace('.', ',')
        old_price = d.get("old_price_str") or ""
        disc = d.get("discount_pct", 0)
        store = d.get("store", "Loja Oficial")
        coupon = d.get("coupon")
        
        aff_res = convert_to_affiliate(d.get("url", ""), store, config)
        link = aff_res["url"]
        
        disc_txt = f" (-{disc}% OFF)" if disc else ""
        num_icon = num_emojis[idx] if idx < len(num_emojis) else f"*{idx+1}.*"
        lines.append(f"{num_icon} *{title}*")
        if old_price and old_price != price:
            lines.append(f"❌ De: ~{old_price}~ 👉 *Por: {price}*{disc_txt}")
        else:
            lines.append(f"🔥 *Por: {price}*{disc_txt}")
            
        lines.append(f"🏬 Loja: {store}")
        if coupon:
            lines.append(f"🎟️ Cupom: *{coupon}*")
        lines.append(f"🛒 *Link Seguro:* {link}")
        lines.append("")
        
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚠️ _Atenção: Os preços e estoques podem esgotar rapidamente!_")
    if group_link:
        lines.append(f"👥 _Entre no nosso Grupo VIP de Achadinhos:_ {group_link}")
        
    return "\n".join(lines)
