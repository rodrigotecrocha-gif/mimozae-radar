from PIL import Image, ImageDraw, ImageFont
import io
import requests
import textwrap

THEMES = {
    "Rosa Mimozae": {
        "header_bg": (235, 75, 110),
        "header_text": (255, 255, 255),
        "bg_color": (253, 248, 249),
        "card_bg": (255, 255, 255),
        "card_border": (245, 215, 225),
        "badge_bg": (225, 29, 72),
        "badge_text": (255, 255, 255),
        "title_color": (30, 30, 35),
        "price_color": (225, 29, 72),
        "accent": (235, 75, 110)
    },
    "Preto VIP / Tech": {
        "header_bg": (24, 24, 30),
        "header_text": (255, 215, 0),
        "bg_color": (245, 245, 247),
        "card_bg": (255, 255, 255),
        "card_border": (220, 220, 230),
        "badge_bg": (234, 88, 12),
        "badge_text": (255, 255, 255),
        "title_color": (20, 20, 25),
        "price_color": (16, 149, 78),
        "accent": (24, 24, 30)
    },
    "Vermelho Oferta": {
        "header_bg": (220, 38, 38),
        "header_text": (255, 255, 255),
        "bg_color": (254, 242, 242),
        "card_bg": (255, 255, 255),
        "card_border": (254, 202, 202),
        "badge_bg": (220, 38, 38),
        "badge_text": (255, 255, 255),
        "title_color": (30, 30, 35),
        "price_color": (220, 38, 38),
        "accent": (220, 38, 38)
    },
    "Verde Economia": {
        "header_bg": (13, 148, 136),
        "header_text": (255, 255, 255),
        "bg_color": (240, 253, 250),
        "card_bg": (255, 255, 255),
        "card_border": (204, 251, 241),
        "badge_bg": (15, 118, 110),
        "badge_text": (255, 255, 255),
        "title_color": (30, 30, 35),
        "price_color": (13, 148, 136),
        "accent": (13, 148, 136)
    }
}

def load_system_font(name: str, size: int):
    try:
        return ImageFont.truetype(name, size)
    except:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()

def generate_social_image(
    title: str,
    price_str: str,
    old_price_str: str = "",
    discount_pct: int = 0,
    store: str = "Loja Oficial",
    image_url: str = "",
    uploaded_image: Image.Image = None,
    format_type: str = "feed", # "feed" (1080x1080) or "story" (1080x1920)
    instagram_handle: str = "@mimozae.of",
    theme_name: str = "Rosa Mimozae"
) -> Image.Image:
    theme = THEMES.get(theme_name, THEMES["Rosa Mimozae"])
    width, height = (1080, 1080) if format_type == "feed" else (1080, 1920)
    
    img = Image.new("RGBA", (width, height), theme["bg_color"])
    draw = ImageDraw.Draw(img)
    
    # Fonts
    font_header = load_system_font("arialbd.ttf", 46)
    font_sub = load_system_font("arial.ttf", 34)
    font_tag = load_system_font("arialbd.ttf", 32)
    font_title = load_system_font("arialbd.ttf", 42)
    font_price_old = load_system_font("arial.ttf", 36)
    font_price = load_system_font("arialbd.ttf", 74)
    font_badge = load_system_font("arialbd.ttf", 42)
    font_footer = load_system_font("arialbd.ttf", 36)
    
    # 1. Header Banner
    header_h = 140
    draw.rectangle([0, 0, width, header_h], fill=theme["header_bg"])
    draw.text((width // 2, 70), "✨ ACHADINHO IMPERDÍVEL ✨", font=font_header, fill=theme["header_text"], anchor="mm")
    
    # 2. Store Pill Tag
    pill_text = f"📍 {store.upper()}"
    pill_w = 360
    pill_x1 = (width - pill_w) // 2
    draw.rounded_rectangle([pill_x1, 160, pill_x1 + pill_w, 215], radius=25, fill=(255, 255, 255), outline=theme["card_border"], width=2)
    draw.text((width // 2, 187), pill_text, font=font_tag, fill=theme["accent"], anchor="mm")
    
    # 3. Product Image Processing
    prod_img = None
    if uploaded_image:
        prod_img = uploaded_image.convert("RGBA")
    elif image_url:
        try:
            resp = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
            if resp.status_code == 200:
                prod_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        except Exception as e:
            print("Erro ao carregar imagem para o post:", e)
            
    # Draw product image box
    img_box_size = 460 if format_type == "feed" else 620
    box_y = 235 if format_type == "feed" else 280
    box_x = (width - img_box_size) // 2
    
    draw.rounded_rectangle(
        [box_x, box_y, box_x + img_box_size, box_y + img_box_size],
        radius=25,
        fill=theme["card_bg"],
        outline=theme["card_border"],
        width=2
    )
    
    if prod_img:
        # Resize thumbnail maintaining aspect ratio
        pad = 24
        inner_max = img_box_size - (pad * 2)
        prod_img.thumbnail((inner_max, inner_max), Image.Resampling.LANCZOS)
        
        # Center inside box
        px = box_x + (img_box_size - prod_img.width) // 2
        py = box_y + (img_box_size - prod_img.height) // 2
        img.paste(prod_img, (px, py), prod_img)
        
    # 4. Discount Badge
    if discount_pct and discount_pct > 0:
        badge_w, badge_h = 240, 75
        bx1 = box_x - 15
        by1 = box_y - 15
        draw.rounded_rectangle([bx1, by1, bx1 + badge_w, by1 + badge_h], radius=20, fill=theme["badge_bg"])
        draw.text((bx1 + badge_w // 2, by1 + badge_h // 2), f"-{discount_pct}% OFF", font=font_badge, fill=theme["badge_text"], anchor="mm")
        
    # 5. Product Title (Wrapped)
    content_y = box_y + img_box_size + 45
    wrapper = textwrap.TextWrapper(width=44 if format_type == "feed" else 40)
    title_lines = wrapper.wrap(title)
    if len(title_lines) > 2:
        title_lines = title_lines[:2]
        title_lines[-1] += "..."
        
    for line in title_lines:
        draw.text((width // 2, content_y), line, font=font_title, fill=theme["title_color"], anchor="mm")
        content_y += 48
        
    content_y += 15
    
    # 6. Price Section
    if old_price_str and old_price_str != price_str:
        old_txt = f"De: R$ {old_price_str.replace('R$', '').strip()}"
        draw.text((width // 2, content_y), old_txt, font=font_price_old, fill=(130, 130, 130), anchor="mm")
        
        # Riscar preço anterior
        bbox = draw.textbbox((width // 2, content_y), old_txt, font=font_price_old, anchor="mm")
        draw.line([(bbox[0] - 6, content_y), (bbox[2] + 6, content_y)], fill=(220, 50, 50), width=3)
        content_y += 50
    else:
        content_y += 20
        
    # Promo Price
    clean_p = price_str if "R$" in price_str else f"R$ {price_str}"
    draw.text((width // 2, content_y), f"POR: {clean_p}", font=font_price, fill=theme["price_color"], anchor="mm")
    
    # 7. Format specific footer & CTA
    if format_type == "feed":
        footer_y = height - 120
        draw.rounded_rectangle([70, footer_y - 20, width - 70, height - 35], radius=25, fill=theme["accent"])
        draw.text((width // 2, footer_y + 35), f"💬 Comente 'QUERO' ou link na Bio | {instagram_handle}", font=font_footer, fill=(255, 255, 255), anchor="mm")
    else: # Story 1080x1920
        # Dedicated interactive sticker placeholder for Instagram Link
        sticker_y = height - 480
        draw.rounded_rectangle([140, sticker_y, width - 140, sticker_y + 130], radius=35, fill=(255, 255, 255), outline=theme["accent"], width=4)
        draw.text((width // 2, sticker_y + 65), "🔗 COLOQUE A FIGURINHA DE LINK AQUI 🔗", font=font_sub, fill=theme["accent"], anchor="mm")
        
        # Bottom branding bar
        footer_y = height - 180
        draw.rounded_rectangle([70, footer_y, width - 70, footer_y + 100], radius=25, fill=theme["accent"])
        draw.text((width // 2, footer_y + 50), f"Siga {instagram_handle} para mais ofertas!", font=font_footer, fill=(255, 255, 255), anchor="mm")
        
    return img
