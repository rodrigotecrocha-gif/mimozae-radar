import streamlit as st
import io
import time
from PIL import Image

from config import load_config, save_config, load_full_config, get_profile, save_profile, create_new_profile
from services.scraper import search_deals, analyze_single_url, sanitize_img_url, NICHES, VIRAL_CATALOG
from services.affiliate import convert_to_affiliate, identify_store, clean_product_url
from services.copywriter import generate_whatsapp_copy, generate_instagram_caption
from services.image_generator import generate_social_image, THEMES
from services.whatsapp_sender import generate_wa_link, send_whatsapp_media_api, generate_batch_super_message

def render_deal_image(img_source, caption=None, width=None, use_container_width=True):
    """Renderiza imagem com proteção completa contra MediaFileStorageError, URLs relativas ou falhas de rede."""
    if not img_source:
        st.write("📦 *Sem imagem disponível*")
        return
        
    if isinstance(img_source, str):
        clean_url = sanitize_img_url(img_source)
        if clean_url and (clean_url.startswith("http://") or clean_url.startswith("https://")):
            try:
                if width:
                    st.image(clean_url, caption=caption, width=width)
                else:
                    st.image(clean_url, caption=caption, use_container_width=use_container_width)
            except Exception:
                st.write("📦 *Imagem indisponível*")
        else:
            st.write("📦 *Imagem indisponível*")
    else:
        try:
            if width:
                st.image(img_source, caption=caption, width=width)
            else:
                st.image(img_source, caption=caption, use_container_width=use_container_width)
        except Exception:
            st.write("📦 *Arte indisponível*")

# Page Config
st.set_page_config(
    page_title="Mimozae Deals Hub | Achadinhos Virais & Afiliados",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark & Light Mode Friendly + Ultra Modern)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF007A 0%, #7928CA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .sub-title {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-top: -5px;
        margin-bottom: 25px;
    }
    
    /* Card Container & Hover Effects */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(255, 0, 122, 0.45) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.07) !important;
    }

    /* Image Uniformization & Anti-Blowout */
    .product-image-container {
        width: 100%;
        height: 185px;
        background: #ffffff;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 8px;
        margin: 6px 0 10px 0;
        box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06);
    }
    .product-image {
        max-height: 165px;
        max-width: 100%;
        width: auto;
        height: auto;
        object-fit: contain;
        display: block;
        margin: 0 auto;
        transition: transform 0.25s ease;
    }
    .product-image-container:hover .product-image {
        transform: scale(1.06);
    }
    .no-image-box {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        width: 100%;
    }

    /* Fallback para imagens Streamlit que estiverem dentro de cards */
    [data-testid="stVerticalBlockBorderWrapper"] img {
        max-height: 185px !important;
        object-fit: contain !important;
    }

    /* Badges */
    .badge-viral {
        background: linear-gradient(135deg, #FF007A 0%, #FF4B2B 100%);
        color: white !important;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.72rem;
        display: inline-block;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 6px rgba(255, 0, 122, 0.35);
    }
    .badge-discount {
        background-color: #EF4444;
        color: white !important;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-store {
        background-color: #1E293B;
        color: #F8FAFC !important;
        border: 1px solid #334155;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        white-space: nowrap;
    }

    /* Tipografia e Alinhamento Perfeito dos Cards */
    .product-title {
        font-size: 0.95rem;
        font-weight: 700;
        line-height: 1.35;
        height: 42px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        text-overflow: ellipsis;
        margin-bottom: 6px;
        color: inherit;
    }
    .product-pricing {
        min-height: 46px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        margin-bottom: 8px;
    }
    .price-promo {
        color: #10B981 !important;
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1.1;
    }
    .price-old {
        color: #94A3B8;
        font-size: 0.85rem;
        text-decoration: line-through;
        margin-bottom: 2px;
    }
    .coupon-tag {
        background-color: #FEF3C7;
        color: #92400E !important;
        border: 1px dashed #F59E0B;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 5px;
        font-size: 0.72rem;
        display: inline-block;
        margin-top: 3px;
        width: fit-content;
    }
    
    .batch-highlight {
        background: rgba(255, 0, 122, 0.05);
        border: 1px solid rgba(255, 0, 122, 0.3);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Multi-Profile & Config Init
full_cfg = load_full_config()
available_profiles = list(full_cfg.get("profiles", {}).keys())

if "active_profile_name" not in st.session_state:
    st.session_state.active_profile_name = full_cfg.get("active_profile", available_profiles[0])
    
if st.session_state.active_profile_name not in available_profiles:
    st.session_state.active_profile_name = available_profiles[0]

# Carrega a configuração do perfil ativo da sessão!
config = get_profile(st.session_state.active_profile_name)
wa_mode = config.get("whatsapp", {}).get("mode", "web") # 'web', 'app' or 'universal'

# Caching de Alto Desempenho
@st.cache_data(ttl=180, show_spinner=False)
def get_cached_deals(stores_tuple, niche, min_discount, price_max, keyword, viral_mode, viral_cat):
    return search_deals(
        selected_stores=list(stores_tuple) if stores_tuple else None,
        niche=niche,
        min_discount=min_discount,
        price_max=price_max,
        search_keyword=keyword,
        viral_mode=viral_mode,
        viral_category=viral_cat
    )

# Session State Init
if "deals_list" not in st.session_state:
    st.session_state.deals_list = []
if "selected_deal" not in st.session_state:
    st.session_state.selected_deal = None
if "last_search_time" not in st.session_state:
    st.session_state.last_search_time = 0.0
if "selected_indices" not in st.session_state:
    st.session_state.selected_indices = set()

# Header
col_logo, col_profile, col_info = st.columns([2.6, 1.4, 1.0])
with col_logo:
    st.markdown('<p class="main-title">🛍️ Mimozae Deals Hub</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-title">Radar de Achadinhos Virais & Criador de Conteúdo para <b>{config.get("instagram", {}).get("handle", "@mimozae.of")}</b></p>', unsafe_allow_html=True)
with col_profile:
    selected_prof = st.selectbox(
        "👤 Operador(a) Ativo(a):",
        options=available_profiles,
        index=available_profiles.index(st.session_state.active_profile_name),
        key="header_prof_selector",
        help="Cada operador possui suas próprias tags e número/grupo de WhatsApp"
    )
    if selected_prof != st.session_state.active_profile_name:
        st.session_state.active_profile_name = selected_prof
        st.rerun()
with col_info:
    tags_count = sum(1 for v in config.get("affiliate_tags", {}).values() if v.strip())
    st.info(f"🏷️ **{tags_count}/8** Lojas | ⚡ WhatsApp Ativo")

# Tabs
tab_radar, tab_analyzer, tab_studio, tab_settings = st.tabs([
    "🔥 Radar de Ofertas & Virais",
    "🔗 Analisador de Link Avulso",
    "📸 Estúdio Instagram (@mimozae.of)",
    "⚙️ Configurações & Afiliados"
])

# ==========================================
# ABA 1: RADAR DE OFERTAS & VIRAIS
# ==========================================
with tab_radar:
    mode_selection = st.radio(
        "Modo de Operação:",
        options=["✨ Achadinhos Virais (Moda, Beleza, Casa & Gadgets)", "🔍 Busca Manual / Filtro por Lojas"],
        horizontal=True
    )
    is_viral_mode = "Achadinhos Virais" in mode_selection
    
    with st.container(border=True):
        if is_viral_mode:
            st.markdown("### 🔥 Achadinhos Virais de Alta Recorrência")
            st.caption("Foco nos itens mais comprados do TikTok, Reels e canais de promoções:")
            
            col_v1, col_v2, col_v3 = st.columns([1.5, 1.2, 1.2])
            with col_v1:
                viral_cat = st.selectbox(
                    "Nicho Viral:",
                    options=["✨ Todos os Achadinhos Virais"] + list(VIRAL_CATALOG.keys()),
                    index=0
                )
            with col_v2:
                viral_discount = st.select_slider(
                    "Desconto Mínimo:",
                    options=[0, 15, 25, 35, 50],
                    value=0,
                    format_func=lambda x: "Todas as Ofertas" if x == 0 else f"{x}%+ OFF 🔥"
                )
            with col_v3:
                btn_search = st.button("🚀 Rastrear Achadinhos Virais Agora", type="primary", use_container_width=True)
                
            selected_stores_param = ("Todas as Lojas",)
            niche_param = "Todos os Nichos"
            search_term_param = ""
            actual_cat_param = "" if "Todos" in viral_cat else viral_cat
            
        else:
            st.markdown("### 🔍 Busca Geral & Filtro por Loja")
            col_f1, col_f2, col_f3 = st.columns([1.5, 1.2, 1.2])
            
            with col_f1:
                all_stores = [
                    "Todas as Lojas",
                    "Amazon Brasil",
                    "Mercado Livre",
                    "Shopee",
                    "Magazine Luiza",
                    "Casas Bahia",
                    "Shein",
                    "AliExpress",
                    "Dafiti"
                ]
                selected_stores = st.multiselect(
                    "Lojas:",
                    options=all_stores,
                    default=["Todas as Lojas"]
                )
                selected_stores_param = tuple(selected_stores)
                
                niche_param = st.selectbox(
                    "Nicho:",
                    options=list(NICHES.keys()),
                    index=0
                )
                
            with col_f2:
                viral_discount = st.select_slider(
                    "Desconto Mínimo:",
                    options=[0, 15, 25, 35, 50],
                    value=0,
                    format_func=lambda x: "Todas as Ofertas" if x == 0 else f"{x}%+ OFF 🔥"
                )
                search_term_param = st.text_input(
                    "Termo Específico (opcional):",
                    placeholder="Ex: perfume, airfryer, fone...",
                )
                
            with col_f3:
                price_limit = st.slider(
                    "Preço Máximo (R$):",
                    min_value=20,
                    max_value=2000,
                    value=1000,
                    step=50,
                    format="R$ %d"
                )
                btn_search = st.button("🚀 Rastrear Ofertas com Desconto", type="primary", use_container_width=True)
                
            actual_cat_param = ""
            
    # Execução Paralela Rápida
    if btn_search:
        t_start = time.time()
        with st.spinner("⚡ Varrendo lojas simultaneamente em paralelo..."):
            found = get_cached_deals(
                stores_tuple=selected_stores_param,
                niche=niche_param,
                min_discount=viral_discount,
                price_max=1000 if is_viral_mode else price_limit,
                keyword=search_term_param,
                viral_mode=is_viral_mode,
                viral_cat=actual_cat_param
            )
            st.session_state.deals_list = found
            st.session_state.last_search_time = time.time() - t_start
            st.session_state.selected_indices = set()
            
    deals = st.session_state.deals_list
    
    if deals:
        for d in deals:
            if d.get("image") and not str(d["image"]).startswith("http"):
                d["image"] = sanitize_img_url(d["image"], d.get("store", ""))
            if "aff_res" not in d:
                d["aff_res"] = convert_to_affiliate(d.get("url", ""), d.get("store", ""), config)
                
        speed_msg = f"⚡ Busca realizada em apenas **{st.session_state.last_search_time:.2f}s**!" if st.session_state.last_search_time > 0 else ""
        st.success(f"✨ Encontradas **{len(deals)}** promoções no radar! {speed_msg}")
        
        # ========================================================
        # BARRA DE DISPARO EM LOTE (ATÉ 5 LINKS DE UMA VEZ)
        # ========================================================
        selected_deals = [deals[i] for i in sorted(list(st.session_state.selected_indices)) if i < len(deals)][:5]
        
        with st.container(border=True):
            b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1.8, 1.8, 1])
            with b_col1:
                st.markdown(f"#### 📦 Fila de Envio: **{len(selected_deals)}/5**")
                st.caption("Marque a caixa no topo dos cards para adicionar.")
                
            with b_col2:
                # Disparo Direto no WhatsApp Web (Super Mensagem 5 em 1)
                super_msg_text = generate_batch_super_message(selected_deals, config) if selected_deals else ""
                # Usa modo 'web' para ir direto ao web.whatsapp.com sem tela intermediária!
                super_wa_link = generate_wa_link(super_msg_text, target_mode=wa_mode) if selected_deals else ""
                st.link_button("📲 Abrir Super Mensagem (5 em 1)", super_wa_link, disabled=(len(selected_deals) == 0), type="primary", use_container_width=True)
                
            with b_col3:
                # Disparo via API Automática (Foto + Legenda em segundo plano)
                btn_auto_api = st.button("🚀 Disparar via WhatsApp API", disabled=(len(selected_deals) == 0), use_container_width=True)
                
            with b_col4:
                if st.button("🧹 Limpar Fila", use_container_width=True):
                    st.session_state.selected_indices = set()
                    st.rerun()
                    
            if selected_deals:
                with st.expander("📋 Ver Texto da Super Mensagem (5 em 1)"):
                    st.text_area("Texto pronto para colar:", super_msg_text, height=180)
                    
            if btn_auto_api and selected_deals:
                endpoint = config.get("whatsapp", {}).get("api_endpoint") or config.get("whatsapp", {}).get("webhook_url")
                if not endpoint:
                    st.error("⚠️ Você ainda não configurou o Endpoint da WhatsApp API na aba 'Configurações & Afiliados'. Preencha a URL da sua Evolution API ou Z-API.")
                else:
                    progress_bar = st.progress(0)
                    success_count = 0
                    for s_idx, d in enumerate(selected_deals):
                        aff = convert_to_affiliate(d.get("url", ""), d.get("store", ""), config)
                        caption = generate_whatsapp_copy(d, aff["url"], config.get("whatsapp", {}).get("group_link", ""))
                        img_url = d.get("image", "")
                        
                        res = send_whatsapp_media_api(config, image_url=img_url, caption=caption)
                        if res.get("success"):
                            success_count += 1
                        time.sleep(1)
                        progress_bar.progress((s_idx + 1) / len(selected_deals))
                        
                    st.success(f"🎉 **{success_count} de {len(selected_deals)}** ofertas disparadas com foto e legenda para o grupo!")

        # Grid de Cards (Renderização Leve e Instantânea)
        cols_per_row = 3
        for i in range(0, len(deals), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(deals):
                    deal = deals[idx]
                    with cols[j]:
                        with st.container(border=True):
                            store_name = deal.get("store", "Loja")
                            disc = deal.get("discount_pct", 0)
                            is_viral = deal.get("is_viral", False)
                            
                            # 1. Topo: Seleção e Badges
                            col_chk, col_badges = st.columns([1.3, 1.7])
                            with col_chk:
                                currently_selected = idx in st.session_state.selected_indices
                                is_checked = st.checkbox("Fila (5 máx)", value=currently_selected, key=f"chk_{idx}")
                                if is_checked != currently_selected:
                                    if is_checked:
                                        if len(st.session_state.selected_indices) < 5:
                                            st.session_state.selected_indices.add(idx)
                                        else:
                                            st.toast("⚠️ Limite de 5 ofertas por lote atingido!")
                                            st.session_state[f"chk_{idx}"] = False
                                    else:
                                        st.session_state.selected_indices.discard(idx)
                                    st.rerun()
                                    
                            with col_badges:
                                b_html = '<div style="text-align: right; display: flex; justify-content: flex-end; gap: 4px; flex-wrap: wrap;">'
                                b_html += f'<span class="badge-store">{store_name}</span>'
                                if is_viral:
                                    b_html += '<span class="badge-viral">✨ VIRAL</span>'
                                elif disc and disc > 0:
                                    b_html += f'<span class="badge-discount">-{disc}%</span>'
                                b_html += '</div>'
                                st.markdown(b_html, unsafe_allow_html=True)
                                    
                            # 2. Imagem Padronizada com Altura Fixa (Sem Estourar)
                            raw_img = deal.get("image", "")
                            clean_img = sanitize_img_url(raw_img, store_name) if raw_img else ""
                            if clean_img and (clean_img.startswith("http://") or clean_img.startswith("https://")):
                                st.markdown(f'''
                                <div class="product-image-container">
                                    <img src="{clean_img}" class="product-image" alt="Produto" loading="lazy" onerror="this.onerror=null;this.parentElement.innerHTML='<div class=\\'no-image-box\\'>📦 Imagem indisponível</div>';" />
                                </div>
                                ''', unsafe_allow_html=True)
                            else:
                                st.markdown('''
                                <div class="product-image-container">
                                    <div class="no-image-box">📦 Sem imagem</div>
                                </div>
                                ''', unsafe_allow_html=True)
                                
                            # 3. Título Padronizado (2 linhas)
                            title = deal.get("title", "Produto sem título")
                            st.markdown(f'<div class="product-title" title="{title}">{title}</div>', unsafe_allow_html=True)
                            
                            # 4. Preços Formatados & Cupons
                            p_val = deal.get("price", 0.0)
                            op_val = deal.get("old_price")
                            p_str = f"R$ {p_val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.') if p_val else deal.get("price_str", "Confira")
                            op_str = f"R$ {op_val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.') if (op_val and op_val > p_val) else ""
                            
                            pricing_html = f'''
                            <div class="product-pricing">
                                {f'<span class="price-old">{op_str}</span>' if op_str else ''}
                                <span class="price-promo">{p_str}</span>
                                {f'<span class="coupon-tag">🎟️ Cupom: {deal.get("coupon")}</span>' if deal.get("coupon") else ''}
                            </div>
                            '''
                            st.markdown(pricing_html, unsafe_allow_html=True)
                            
                            # 5. Link de Afiliado
                            aff_res = deal.get("aff_res") or convert_to_affiliate(deal.get("url", ""), store_name, config)
                            final_aff_link = aff_res["url"]
                            
                            # 6. Botão de Envio Rápido no WhatsApp Web
                            wa_copy = generate_whatsapp_copy(deal, final_aff_link, config.get("whatsapp", {}).get("group_link", ""))
                            wa_direct_link = generate_wa_link(wa_copy, target_mode=wa_mode)
                            st.link_button("📲 Enviar WhatsApp Web", wa_direct_link, type="primary", use_container_width=True)
                            
                            # 7. Gavetas Auxiliares (Instagram & Detalhes)
                            with st.expander("📸 Post Instagram (@mimozae.of)"):
                                ig_fmt = st.radio("Formato:", ["Feed (1:1)", "Story (9:16)"], key=f"fmt_{idx}", horizontal=True)
                                fmt_slug = "feed" if "Feed" in ig_fmt else "story"
                                ig_theme = st.selectbox("Tema visual:", options=list(THEMES.keys()), index=0, key=f"thm_{idx}")
                                
                                if st.button("🎨 Gerar Arte Agora", key=f"gen_{idx}", use_container_width=True):
                                    with st.spinner("Desenhando arte em alta resolução..."):
                                        safe_disc = int(disc) if disc else 0
                                        card_img = generate_social_image(
                                            title=title,
                                            price_str=p_str.replace("R$", "").strip(),
                                            old_price_str=op_str.replace("R$", "").strip() if op_str else "",
                                            discount_pct=safe_disc,
                                            store=store_name,
                                            image_url=clean_img,
                                            format_type=fmt_slug,
                                            instagram_handle=config.get("instagram", {}).get("handle", "@mimozae.of"),
                                            theme_name=ig_theme
                                        )
                                        st.session_state[f"cached_art_{idx}"] = card_img
                                        
                                if f"cached_art_{idx}" in st.session_state:
                                    img_to_show = st.session_state[f"cached_art_{idx}"]
                                    render_deal_image(img_to_show, caption=f"Arte {ig_fmt}", width=280)
                                    
                                    buf = io.BytesIO()
                                    img_to_show.save(buf, format="PNG")
                                    byte_im = buf.getvalue()
                                    
                                    st.download_button(
                                        label=f"⬇️ Baixar Imagem {ig_fmt.split()[0]} (PNG)",
                                        data=byte_im,
                                        file_name=f"mimozae_{fmt_slug}_{idx}_{int(time.time())}.png",
                                        mime="image/png",
                                        key=f"dl_{idx}",
                                        use_container_width=True
                                    )
                                    
                                ig_caption = generate_instagram_caption(deal, final_aff_link, config)
                                st.text_area("Legenda pronta:", ig_caption, height=110, key=f"cap_{idx}")
                                
                            with st.expander("🔗 Link de Afiliado & Copy"):
                                st.text_input("Link Oficial Gerado:", value=final_aff_link, key=f"link_{idx}")
                                st.caption(f"Status: *{aff_res['status']}*")
                                st.text_area("Texto formatado WhatsApp:", wa_copy, height=120, key=f"wa_txt_{idx}")
    else:
        st.info("💡 Clique no botão **'🚀 Rastrear'** acima para iniciar a busca instantânea com os novos filtros.")


# ==========================================
# ABA 2: ANALISADOR DE LINK AVULSO
# ==========================================
with tab_analyzer:
    st.subheader("🔗 Cole qualquer link de produto para gerar o link e posts")
    st.write("Achou uma oferta navegando na Amazon, Mercado Livre, Shopee, Magalu, Casas Bahia, Shein, AliExpress ou Dafiti? Cole o link abaixo:")
    
    input_url = st.text_input("Cole o link aqui:", placeholder="https://www.mercadolivre.com.br/... ou https://www.amazon.com.br/...", key="manual_url")
    
    if st.button("⚡ Processar Link & Gerar Afiliado", type="primary"):
        if input_url:
            with st.spinner("Analisando página do produto e aplicando tag de afiliado..."):
                parsed = analyze_single_url(input_url)
                if parsed.get("success"):
                    st.success("✅ Produto identificado com sucesso!")
                    
                    with st.container(border=True):
                        col_p1, col_p2 = st.columns([1, 2])
                        with col_p1:
                            raw_p_img = parsed.get("image", "")
                            clean_p_img = sanitize_img_url(raw_p_img, parsed.get("store", "")) if raw_p_img else ""
                            if clean_p_img and (clean_p_img.startswith("http://") or clean_p_img.startswith("https://")):
                                st.markdown(f'''
                                <div class="product-image-container" style="height: 220px;">
                                    <img src="{clean_p_img}" class="product-image" style="max-height: 200px;" alt="Produto" loading="lazy" onerror="this.onerror=null;this.parentElement.innerHTML='<div class=\\'no-image-box\\'>📦 Imagem indisponível</div>';" />
                                </div>
                                ''', unsafe_allow_html=True)
                            else:
                                st.markdown('''
                                <div class="product-image-container" style="height: 220px;">
                                    <div class="no-image-box">📦 Sem imagem</div>
                                </div>
                                ''', unsafe_allow_html=True)
                                
                        with col_p2:
                            st.markdown(f"### {parsed['title']}")
                            st.markdown(f"**Loja Detectada:** {parsed['store']}")
                            if parsed.get("old_price_str"):
                                st.markdown(f"**De:** ~{parsed['old_price_str']}~")
                            st.markdown(f"**Por:** <span class='price-promo'>{parsed['price_str']}</span>", unsafe_allow_html=True)
                            if parsed.get("discount_pct"):
                                st.markdown(f"<span class='badge-discount'>-{parsed['discount_pct']}% OFF</span>", unsafe_allow_html=True)
                            if parsed.get("is_viral"):
                                st.markdown('<span class="badge-viral">✨ PRODUTO VIRAL</span>', unsafe_allow_html=True)
                                
                            aff = convert_to_affiliate(input_url, parsed["store"], config)
                            st.text_input("🔗 Link Oficial de Afiliado Gerado:", value=aff["url"])
                            st.caption(f"Status: {aff['status']}")
                            
                            wa_text = generate_whatsapp_copy(parsed, aff["url"], config.get("whatsapp", {}).get("group_link", ""))
                            st.text_area("Copy formatada para WhatsApp:", wa_text, height=140)
                            
                            wa_open = generate_wa_link(wa_text, target_mode=wa_mode)
                            st.link_button("📲 Abrir WhatsApp Web Direto", wa_open, type="primary", use_container_width=True)
                else:
                    st.error(f"Não foi possível extrair automaticamente: {parsed.get('error')}. Tente novamente ou use o link direto.")
        else:
            st.warning("Insira uma URL antes de clicar.")


# ==========================================
# ABA 3: ESTÚDIO INSTAGRAM (@mimozae.of)
# ==========================================
with tab_studio:
    st.subheader(f"📸 Gerador de Post & Story Customizado para {config.get('instagram', {}).get('handle', '@mimozae.of')}")
    st.write("Crie imagens sob demanda prontas para postar no Feed e nos Stories do seu perfil.")
    
    col_st_left, col_st_right = st.columns([1.2, 1.8])
    
    with col_st_left:
        with st.container(border=True):
            st.markdown("#### ✏️ Detalhes da Oferta")
            
            post_title = st.text_input("Título do Produto:", value="Mini Processador Elétrico Portátil USB", key="studio_title")
            
            col_pr1, col_pr2, col_pr3 = st.columns(3)
            with col_pr1:
                post_old_price = st.text_input("Preço DE (R$):", value="49,90", key="studio_old_p")
            with col_pr2:
                post_price = st.text_input("Preço POR (R$):", value="24,90", key="studio_p")
            with col_pr3:
                post_disc = st.number_input("% Desconto:", min_value=0, max_value=99, value=50, key="studio_disc")
                
            post_store = st.text_input("Nome da Loja:", value="Amazon Brasil", key="studio_store")
            post_theme = st.selectbox("Paleta de Cores:", options=list(THEMES.keys()), index=0, key="studio_theme")
            post_format = st.radio("Formato da Imagem:", options=["Feed (1:1 / 1080x1080)", "Story (9:16 / 1080x1920)"], index=0, key="studio_fmt")
            format_slug = "feed" if "Feed" in post_format else "story"
            
            st.markdown("#### 🖼️ Imagem do Produto")
            img_option = st.radio("Origem da Imagem:", ["URL da Imagem", "Fazer Upload"], horizontal=True, key="studio_img_opt")
            
            post_img_url = ""
            uploaded_file = None
            if img_option == "URL da Imagem":
                post_img_url = st.text_input("Link da imagem:", value="https://m.media-amazon.com/images/I/81hcM4X43PL._AC_SY300_SX300_QL70_ML2_.jpg", key="studio_img_url")
            else:
                uploaded_file = st.file_uploader("Selecione foto do produto (PNG/JPG):", type=["png", "jpg", "jpeg", "webp"], key="studio_upload")
            
    with col_st_right:
        with st.container(border=True):
            st.markdown("#### 👁️ Pré-visualização em Tempo Real")
            
            pil_uploaded = None
            if uploaded_file:
                pil_uploaded = Image.open(uploaded_file)
                
            final_img = generate_social_image(
                title=post_title,
                price_str=post_price,
                old_price_str=post_old_price,
                discount_pct=post_disc,
                store=post_store,
                image_url=post_img_url,
                uploaded_image=pil_uploaded,
                format_type=format_slug,
                instagram_handle=config.get("instagram", {}).get("handle", "@mimozae.of"),
                theme_name=post_theme
            )
            
            render_deal_image(final_img, caption=f"Card Gerado - {post_format}", width=440 if format_slug == "feed" else 330)
            
            buf = io.BytesIO()
            final_img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label=f"⬇️ Baixar Imagem {post_format.split()[0]} (PNG Alta Resolução)",
                data=byte_im,
                file_name=f"mimozae_{format_slug}_{int(time.time())}.png",
                mime="image/png",
                type="primary",
                key="studio_dl_btn",
                use_container_width=True
            )
            
            mock_item = {
                "title": post_title,
                "price_str": f"R$ {post_price}",
                "old_price_str": f"R$ {post_old_price}" if post_old_price else "",
                "discount_pct": post_disc,
                "store": post_store,
                "is_viral": True
            }
            caption = generate_instagram_caption(mock_item, "link_afiliado", config)
            st.text_area("Copie a legenda abaixo para sua postagem:", caption, height=140, key="studio_caption")


# ==========================================
# ABA 4: CONFIGURAÇÕES & AFILIADOS
# ==========================================
with tab_settings:
    curr_prof = st.session_state.active_profile_name
    st.subheader(f"⚙️ Configurações & Afiliados — Perfil: {curr_prof}")
    st.write(f"Você está editando as credenciais de **{curr_prof}**. Cada operador tem seu próprio link de grupo de WhatsApp, tags de afiliado e credenciais de disparo.")
    
    with st.expander("➕ Adicionar Novo Perfil de Operador(a)"):
        new_col1, new_col2 = st.columns([2, 1])
        with new_col1:
            new_p_name = st.text_input("Nome do novo operador (ex: Mariana, Suporte, Equipe B):", key="new_prof_input")
        with new_col2:
            st.write("")
            st.write("")
            if st.button("Criar Perfil", key="btn_create_prof", use_container_width=True):
                if new_p_name.strip():
                    create_new_profile(new_p_name.strip())
                    st.session_state.active_profile_name = new_p_name.strip()
                    st.success(f"Perfil '{new_p_name.strip()}' criado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                    
    with st.form("settings_form"):
        st.markdown(f"### 🛒 Tags de Afiliado — {curr_prof}")
        tags = config.get("affiliate_tags", {})
        
        col_tag1, col_tag2 = st.columns(2)
        with col_tag1:
            amz = st.text_input("Amazon Brasil (Associate Tag):", value=tags.get("amazon", ""), help="Ex: mimozae-20")
            ml = st.text_input("Mercado Livre (ID / Matt Tool):", value=tags.get("mercadolivre", ""), help="Ex: seu código de afiliado Mercado Livre")
            shp = st.text_input("Shopee (Sub_ID ou Tracking):", value=tags.get("shopee", ""), help="Ex: mimozae_promo")
            mgl = st.text_input("Magazine Luiza (Magazine Você Loja):", value=tags.get("magalu", ""), help="Ex: magazinemimozae (nome da sua loja do Magazine Você)")
            
        with col_tag2:
            cb = st.text_input("Casas Bahia (Lomadee / Awin ID):", value=tags.get("casasbahia", ""), help="Ex: seu ID de afiliado Lomadee/Awin")
            shn = st.text_input("Shein (Affiliate Tag / ID):", value=tags.get("shein", ""))
            ali = st.text_input("AliExpress (Portals Tag / Tracking ID):", value=tags.get("aliexpress", ""))
            daf = st.text_input("Dafiti (Awin Publisher ID):", value=tags.get("dafiti", ""))
            
        st.markdown("---")
        st.markdown(f"### 📲 Configurações do WhatsApp — {curr_prof}")
        st.caption("Personalize como este operador envia mensagens para seus grupos ou contatos:")
        
        wa_cfg = config.get("whatsapp", {})
        current_mode = wa_cfg.get("mode", "web")
        
        mode_idx = 0 if current_mode == "web" else (1 if current_mode == "app" else 2)
        selected_wa_mode = st.radio(
            "Destino do Clique de Envio:",
            options=[
                "🌐 WhatsApp Web Direto (web.whatsapp.com - Sem tela intermediária!) [RECOMENDADO]",
                "💻 Aplicativo WhatsApp Desktop (Windows App nativo)",
                "📱 WhatsApp Universal (api.whatsapp.com)"
            ],
            index=mode_idx
        )
        mode_slug = "web" if "web.whatsapp.com" in selected_wa_mode else ("app" if "Desktop" in selected_wa_mode else "universal")
        
        wa_grp_link = st.text_input(
            "Link de Convite do Grupo VIP deste Operador (aparece no rodapé das copies):",
            value=wa_cfg.get("group_link", ""),
            help="Ex: https://chat.whatsapp.com/..."
        )
        
        st.markdown("---")
        st.markdown("### 🤖 Automação via API do WhatsApp (Opcional - Disparo 100% Silencioso)")
        st.caption("Para quem usa Evolution API ou Z-API para postar com foto e legenda sem abrir abas:")
        
        col_wa1, col_wa2 = st.columns(2)
        with col_wa1:
            wa_api_type = st.selectbox(
                "Tipo de Integração / API:",
                options=["Evolution API (v1 / v2)", "Z-API", "Webhook Genérico"],
                index=0
            )
            wa_endpoint = st.text_input(
                "URL do Endpoint da API:",
                value=wa_cfg.get("api_endpoint", wa_cfg.get("webhook_url", "")),
                help="Ex: http://localhost:8080/message/sendMedia/instancia ou https://api.z-api.io/instances/.../token/.../send-image"
            )
            
        with col_wa2:
            wa_token = st.text_input(
                "API Key / Token de Acesso:",
                value=wa_cfg.get("api_token", ""),
                type="password",
                help="Sua chave secreta da API do WhatsApp"
            )
            wa_group_id = st.text_input(
                "ID do Grupo de Destino ou Telefone:",
                value=wa_cfg.get("target_group", ""),
                help="Ex: 1203630248293@g.us (ID do grupo) ou 5511999999999"
            )
            
        st.markdown("---")
        st.markdown("### 📸 Instagram (@mimozae.of)")
        col_net1, col_net2 = st.columns(2)
        with col_net1:
            ig_handle = st.text_input("Usuário do Instagram:", value=config.get("instagram", {}).get("handle", "@mimozae.of"))
        with col_net2:
            ig_cta = st.text_input("Chamada (CTA) Padrão:", value=config.get("instagram", {}).get("default_cta", "Comente 'EU QUERO' para receber o link no direct!"))
            
        submitted = st.form_submit_button(f"💾 Salvar Configurações no Perfil '{curr_prof}'", type="primary")
        
        if submitted:
            new_conf = {
                "instagram": {
                    "handle": ig_handle.strip(),
                    "default_cta": ig_cta.strip(),
                    "hashtags": config.get("instagram", {}).get("hashtags", "")
                },
                "whatsapp": {
                    "mode": mode_slug,
                    "api_type": "evolution" if "Evolution" in wa_api_type else ("z-api" if "Z-API" in wa_api_type else "webhook"),
                    "api_endpoint": wa_endpoint.strip(),
                    "api_token": wa_token.strip(),
                    "target_group": wa_group_id.strip(),
                    "group_link": wa_grp_link.strip(),
                    "webhook_url": wa_endpoint.strip()
                },
                "affiliate_tags": {
                    "amazon": amz.strip(),
                    "mercadolivre": ml.strip(),
                    "shopee": shp.strip(),
                    "magalu": mgl.strip(),
                    "casasbahia": cb.strip(),
                    "shein": shn.strip(),
                    "aliexpress": ali.strip(),
                    "dafiti": daf.strip()
                }
            }
            if save_profile(curr_prof, new_conf):
                st.success(f"✅ Configurações salvas com sucesso no perfil de **{curr_prof}**!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Erro ao salvar configurações.")
