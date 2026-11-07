import re

def generate_whatsapp_copy(item: dict, affiliate_url: str, custom_group_link: str = "") -> str:
    title = item.get("title", "").strip()
    price = item.get("price_str") or f"R$ {item.get('price', 0):.2f}".replace('.', ',')
    old_price = item.get("old_price_str") or (f"R$ {item.get('old_price', 0):.2f}".replace('.', ',') if item.get('old_price') else "")
    discount_pct = item.get("discount_pct")
    store = item.get("store", "Loja Online")
    coupon = item.get("coupon")
    is_viral = item.get("is_viral", False)
    
    discount_txt = f" (-{discount_pct}% OFF)" if discount_pct else ""
    
    header = "🔥 *ACHADINHO VIRAL DETECTADO!* 🔥" if is_viral else "🚨 *SUPER OFERTA DETECTADA!* 🚨"
    
    lines = [
        header,
        ""
    ]
    if is_viral:
        lines.append("⚡ _O queridinho do TikTok / Reels com super desconto:_")
        
    lines.append(f"📦 *{title}*")
    lines.append("")
    
    if old_price and old_price != price:
        lines.append(f"❌ De: ~{old_price}~")
        lines.append(f"🔥 *Por: {price}*{discount_txt}")
    else:
        lines.append(f"🔥 *Por apenas: {price}*{discount_txt}")
        
    lines.append("")
    lines.append(f"🏬 Loja: *{store}*")
    
    if coupon:
        lines.append(f"🎟️ Cupom: *{coupon}*")
        
    lines.append("")
    lines.append("🛒 *Compre com desconto pelo link seguro:*")
    lines.append(f"👉 {affiliate_url}")
    lines.append("")
    lines.append("⚠️ _Preço e estoque sujeitos a alteração a qualquer momento!_")
    
    if custom_group_link:
        lines.append("")
        lines.append(f"👥 _Entre no nosso grupo VIP de promoções:_ {custom_group_link}")
        
    return "\n".join(lines)


def generate_instagram_caption(item: dict, affiliate_url: str, config: dict) -> str:
    handle = config.get("instagram", {}).get("handle", "@mimozae.of")
    default_cta = config.get("instagram", {}).get("default_cta", "Comente 'EU QUERO' para receber o link no direct!")
    hashtags = config.get("instagram", {}).get("hashtags", "#achadinhos #promocao #desconto #ofertas #mimozae")
    
    title = item.get("title", "").strip()
    price = item.get("price_str") or f"R$ {item.get('price', 0):.2f}".replace('.', ',')
    old_price = item.get("old_price_str") or (f"R$ {item.get('old_price', 0):.2f}".replace('.', ',') if item.get('old_price') else "")
    discount_pct = item.get("discount_pct")
    store = item.get("store", "Loja Oficial")
    coupon = item.get("coupon")
    category = item.get("category", "")
    is_viral = item.get("is_viral", False)
    
    head_txt = "✨ ACHADINHO VIRAL DO MOMENTO! ✨" if is_viral else "✨ ACHADINHO IMPERDÍVEL! ✨"
    
    lines = [
        head_txt,
        ""
    ]
    if is_viral:
        lines.append("Aquele item que está bombando no TikTok e nas redes finalmente entrou em promoção! 😱💖")
        lines.append("")
        
    lines.append(f"{title}")
    lines.append("")
    
    if old_price and old_price != price:
        lines.append(f"❌ De ~{old_price}~")
        lines.append(f"🔥 Por apenas {price}! 😱" + (f" (-{discount_pct}% OFF)" if discount_pct else ""))
    else:
        lines.append(f"🔥 Por apenas {price}! 😱" + (f" (-{discount_pct}% OFF)" if discount_pct else ""))
        
    lines.append(f"📍 Disponível na {store}")
    
    if coupon:
        lines.append(f"🎟️ Use o cupom: {coupon}")
        
    lines.append("")
    lines.append(f"💬 {default_cta}")
    lines.append("📲 O link direto também está nos nossos STORIES e no link da bio!")
    lines.append("")
    lines.append(f"💖 Siga {handle} para receber achadinhos diários!")
    lines.append("")
    
    title_lower = title.lower() + " " + category.lower()
    custom_tags = ["#achadinhos", "#promocao", "#ofertas", "#desconto", "#comprinhas", "#mimozae", "#achadosshopee", "#achadosamazon", "#tiktokmademebuyit"]
    
    if any(k in title_lower for k in ["beleza", "cabelo", "pele", "óleo", "creme", "maquiagem", "perfume", "lola", "cerave"]):
        custom_tags.extend(["#skincarebrasil", "#dicasdebeleza", "#cabelossaudaveis", "#autocuidado", "#beleza"])
    elif any(k in title_lower for k in ["casa", "cozinha", "panela", "cafeteira", "limpeza", "airfryer", "processador", "garrafa"]):
        custom_tags.extend(["#casadecorada", "#utilidadesdomesticas", "#achadinhospracasa", "#cozinhaorganizada", "#donadecasa"])
    elif any(k in title_lower for k in ["vestido", "blusa", "calcado", "tenis", "meia-calca", "bolsa", "moda", "conjunto"]):
        custom_tags.extend(["#modafeminina", "#lookdodia", "#estilo", "#tendencia", "#fashiontiktok"])
        
    lines.append(" ".join(list(dict.fromkeys(custom_tags))))
    
    return "\n".join(lines)
