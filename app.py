import importlib
import io
import os
import sys
import time
import streamlit as st
from PIL import Image


_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)


def _ensure_fresh_module(mod_name: str):
    """Recarrega módulos locais apenas se foram atualizados em disco (evita erro de hot-reload no Streamlit Cloud)."""
    already_loaded = mod_name in sys.modules
    mod = importlib.import_module(mod_name)
    mod_file = getattr(mod, "__file__", "")
    if mod_file and os.path.exists(mod_file):
        mtime = os.path.getmtime(mod_file)
        prev = getattr(mod, "__loaded_mtime__", None)
        if (already_loaded and prev is None) or (prev is not None and prev != mtime):
            mod = importlib.reload(mod)
        setattr(mod, "__loaded_mtime__", mtime)
    return mod


for _m in (
    "config",
    "services.scraper",
    "services.affiliate",
    "services.copywriter",
    "services.image_generator",
    "services.whatsapp_sender",
):
    _ensure_fresh_module(_m)

from config import (
    load_config,
    save_config,
    load_full_config,
    save_full_config,
    get_profile,
    save_profile,
    create_new_profile,
    generate_secrets_toml,
)
from services.scraper import search_deals, analyze_single_url, sanitize_img_url, build_store_comparison, NICHES, VIRAL_CATALOG
from services.affiliate import convert_to_affiliate, identify_store, clean_product_url, resolve_deals_links_batch
from services.copywriter import generate_whatsapp_copy, generate_instagram_caption
from services.image_generator import generate_social_image, THEMES
from services.whatsapp_sender import generate_wa_link, send_whatsapp_media_api, generate_batch_super_message, download_jpeg_bytes_cached

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
    .badge-flash {
        background-color: #F59E0B;
        color: #111827 !important;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.72rem;
        display: inline-block;
    }
    .badge-best {
        background-color: #0EA5E9;
        color: white !important;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.72rem;
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
wa_cfg_global = config.get("whatsapp", {})
wa_mode = wa_cfg_global.get("mode", "web") # 'web', 'app' or 'universal'
wa_endpoint_global = (wa_cfg_global.get("api_endpoint") or wa_cfg_global.get("webhook_url") or "").strip()
wa_target_global = (wa_cfg_global.get("target_group") or "").strip()
has_wa_api = bool(wa_endpoint_global and wa_target_global)

# Caching de Alto Desempenho
@st.cache_data(ttl=240, show_spinner=False)
def get_cached_deals(
    stores_tuple,
    niche,
    min_discount,
    price_max,
    keyword,
    viral_mode,
    viral_cat,
    only_flash=False,
    only_discounted=False,
    sort_by="best",
    shopee_creds_tuple=("", ""),
):
    return search_deals(
        selected_stores=list(stores_tuple) if stores_tuple else None,
        niche=niche,
        min_discount=min_discount,
        price_max=price_max,
        search_keyword=keyword,
        viral_mode=viral_mode,
        viral_category=viral_cat,
        only_flash=only_flash,
        only_discounted=only_discounted,
        sort_by=sort_by,
        shopee_creds=shopee_creds_tuple,
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_cached_studio_png(
    title: str,
    price_str: str,
    old_price_str: str,
    discount_pct: int,
    store: str,
    image_url: str,
    format_type: str,
    instagram_handle: str,
    theme_name: str,
) -> bytes:
    """Gera e mantém em cache o PNG da arte do Estúdio quando vem por URL, evitando travar reruns da Aba 1."""
    img = generate_social_image(
        title=title,
        price_str=price_str,
        old_price_str=old_price_str,
        discount_pct=discount_pct,
        store=store,
        image_url=image_url,
        uploaded_image=None,
        format_type=format_type,
        instagram_handle=instagram_handle,
        theme_name=theme_name,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Session State Init
if "deals_list" not in st.session_state:
    st.session_state.deals_list = []
if "selected_deal" not in st.session_state:
    st.session_state.selected_deal = None
if "last_search_time" not in st.session_state:
    st.session_state.last_search_time = 0.0
if "selected_indices" not in st.session_state:
    st.session_state.selected_indices = set()
if "display_limit" not in st.session_state:
    st.session_state.display_limit = 30
if "last_query_sig" not in st.session_state:
    st.session_state.last_query_sig = None

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
    aff_tags = config.get("affiliate_tags", {})
    ml_ok = bool(aff_tags.get("mercadolivre", "").strip())
    shp_ok = bool(aff_tags.get("shopee", "").strip() or (aff_tags.get("shopee_app_id", "").strip() and aff_tags.get("shopee_app_secret", "").strip()))
    shn_ok = bool(aff_tags.get("shein", "").strip())
    tags_count = sum([ml_ok, shp_ok, shn_ok])
    wa_badge = "🚀 API Instantânea" if has_wa_api else "📲 WhatsApp Web"
    st.info(f"🏷️ **{tags_count}/3** Lojas | {wa_badge}")

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
        options=[
            "✨ Achadinhos Virais",
            "🔎 Buscar Produto & Comparar (ML × Shopee × Shein)",
            "🏬 Filtrar por Loja & Nicho",
        ],
        horizontal=True
    )
    is_viral_mode = mode_selection.startswith("✨")
    is_compare_mode = mode_selection.startswith("🔎")
    
    with st.container(border=True):
        if is_viral_mode:
            st.markdown("### 🔥 Achadinhos Virais & Mais Vendidos")
            st.caption("Pré-seleção automática por maior desconto real, ofertas relâmpago, avaliações e índice de vendas:")
            
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
            price_limit = 10000

        elif is_compare_mode:
            st.markdown("### 🔎 Buscar Produto Específico & Comparar Preços")
            st.caption("Digite o nome ou palavra-chave de um produto para buscar correspondências simultaneamente no **Mercado Livre**, **Shopee** e **Shein** e comparar preços:")
            c_s1, c_s2, c_s3 = st.columns([2.2, 1.1, 1.1])
            with c_s1:
                search_term_param = st.text_input(
                    "Nome ou Palavra-Chave do Produto:",
                    placeholder="Ex: fone bluetooth, airfryer, vestido, creatina, bolsa...",
                    key="compare_kw_input",
                )
            with c_s2:
                viral_discount = st.select_slider(
                    "Desconto Mínimo:",
                    options=[0, 15, 25, 35, 50],
                    value=0,
                    format_func=lambda x: "Qualquer %" if x == 0 else f"{x}%+ OFF",
                    key="cmp_disc",
                )
            with c_s3:
                st.write("")
                btn_search = st.button("🔎 Buscar & Comparar", type="primary", use_container_width=True)

            selected_stores_param = ("Todas as Lojas",)
            niche_param = "Todos os Nichos"
            actual_cat_param = ""
            price_limit = 10000
            
        else:
            st.markdown("### 🔍 Busca Direta por Loja & Nicho")
            col_f1, col_f2, col_f3 = st.columns([1.5, 1.2, 1.2])
            
            with col_f1:
                all_stores = [
                    "Todas as Lojas",
                    "Mercado Livre",
                    "Shopee",
                    "Shein",
                ]
                selected_stores = st.multiselect(
                    "Lojas:",
                    options=all_stores,
                    default=["Todas as Lojas"]
                )
                selected_stores_param = tuple(selected_stores) if selected_stores else ("Todas as Lojas",)
                
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
                    placeholder="Ex: vestido, airfryer, fone...",
                )
                
            with col_f3:
                price_limit = st.slider(
                    "Preço Máximo (R$):",
                    min_value=20,
                    max_value=5000,
                    value=2500,
                    step=50,
                    format="R$ %d"
                )
                btn_search = st.button("🚀 Rastrear Ofertas com Desconto", type="primary", use_container_width=True)
                
            actual_cat_param = ""

        # Critérios de Qualidade e Link Hygiene
        q_c1, q_c2, q_c3, q_c4 = st.columns([1.6, 1.0, 1.0, 1.1])
        with q_c1:
            sort_choice = st.selectbox(
                "Ordenar por Qualidade:",
                options=[
                    "🔥 Melhores Ofertas (Relâmpago + Vendas + Desconto)",
                    "💥 Maior Desconto (% OFF)",
                    "⭐ Mais Vendidos & Bem Avaliados",
                    "💰 Menor Preço",
                ],
                index=0,
                key="sort_selector"
            )
            sort_slug = (
                "discount" if "Maior Desconto" in sort_choice
                else ("sales" if "Mais Vendidos" in sort_choice
                else ("price_asc" if "Menor Preço" in sort_choice else "best"))
            )
        with q_c2:
            st.write("")
            only_flash = st.checkbox("⚡ Só Relâmpago / +Vendidos", value=False, key="chk_only_flash")
        with q_c3:
            st.write("")
            only_discounted = st.checkbox("💥 Só c/ Desconto Real", value=False, key="chk_only_disc")
        with q_c4:
            st.write("")
            hide_promobit = st.checkbox("🚫 Ocultar Links Promobit", value=True, key="chk_hide_promobit", help="Oculta automaticamente itens que não puderam ser convertidos para link direto da loja")
            
    # Execução Paralela Rápida com Atualização Automática nos Filtros
    current_kw = search_term_param.strip() if not is_viral_mode else ""
    shopee_creds_tuple = (
        config.get("affiliate_tags", {}).get("shopee_app_id", "").strip(),
        config.get("affiliate_tags", {}).get("shopee_app_secret", "").strip(),
    )
    query_sig = (
        selected_stores_param,
        niche_param,
        viral_discount,
        10000 if (is_viral_mode or is_compare_mode) else price_limit,
        current_kw,
        is_viral_mode,
        is_compare_mode,
        actual_cat_param,
        only_flash,
        only_discounted,
        sort_slug,
        shopee_creds_tuple,
    )
    
    if is_compare_mode and not current_kw:
        st.info("🔎 Digite o nome ou palavra-chave de um produto acima (ex.: `airfryer`, `fone bluetooth`, `vestido`) para comparar correspondências entre **Mercado Livre**, **Shopee** e **Shein**.")
        deals = []
    else:
        should_search = btn_search or (query_sig != st.session_state.last_query_sig) or (len(st.session_state.deals_list) == 0)
        
        if should_search:
            st.session_state.last_query_sig = query_sig
            st.session_state.display_limit = 30
            t_start = time.time()
            with st.spinner("⚡ Varrendo catálogos reais das lojas e comparando correspondências..."):
                found = get_cached_deals(
                    stores_tuple=selected_stores_param,
                    niche=niche_param,
                    min_discount=viral_discount,
                    price_max=10000 if (is_viral_mode or is_compare_mode) else price_limit,
                    keyword=current_kw,
                    viral_mode=is_viral_mode,
                    viral_cat=actual_cat_param,
                    only_flash=only_flash,
                    only_discounted=only_discounted,
                    sort_by=sort_slug,
                    shopee_creds_tuple=shopee_creds_tuple,
                )
                st.session_state.deals_list = found
                st.session_state.last_search_time = time.time() - t_start
                st.session_state.selected_indices = set()
                
        deals = st.session_state.deals_list
    
    if deals:
        # Resolve redirecionadores de um lote suficiente para preencher a exibição com links diretos reais
        scan_slice = deals[:max(st.session_state.display_limit + 60, 120)]
        resolve_deals_links_batch(scan_slice, max_promobit=15)
        deals = [d for d in deals if not d.get("_invalid_link")]
        hidden_pb_count = 0
        if hide_promobit:
            clean_only = [d for d in deals if "promobit.com" not in (d.get("url") or "").lower()]
            hidden_pb_count = len(deals) - len(clean_only)
            deals = clean_only
        st.session_state.deals_list = [d for d in st.session_state.deals_list if not d.get("_invalid_link")]

        visible_deals = deals[:st.session_state.display_limit]
        for d in visible_deals:
            if d.get("image") and not str(d["image"]).startswith("http"):
                d["image"] = sanitize_img_url(d["image"], d.get("store", ""))
                
        speed_msg = f"⚡ Busca realizada em **{st.session_state.last_search_time:.2f}s**!" if st.session_state.last_search_time > 0 else ""
        st.success(f"✨ Encontradas **{len(deals)}** promoções com link direto das lojas! (Exibindo Top **{len(visible_deals)}**) {speed_msg}")
        if hidden_pb_count > 0:
            st.caption(f"🛡️ {hidden_pb_count} ofertas que ainda dependiam de redirecionador do Promobit foram ocultadas automaticamente (desmarque *'🚫 Ocultar Links Promobit'* se desejar exibi-las, ou cadastre sua **Shopee Open API** na Aba 4).")

        # ========================================================
        # QUADRO DE COMPARAÇÃO ENTRE LOJAS QUANDO BUSCA POR NOME
        # ========================================================
        if current_kw:
            cmp = build_store_comparison(deals, current_kw)
            st.markdown(f"#### 📊 Comparação para **`{current_kw}`** nos sites cadastrados:")
            all_best = [(st_name, info["best_deal"]) for st_name, info in cmp.items() if info["best_deal"] and (info["best_deal"].get("price") or 0) > 0]
            if all_best:
                win_store, win_deal = min(all_best, key=lambda x: x[1]["price"])
                st.info(f"🏆 **Menor preço encontrado:** **{win_deal['price_str']}** na **{win_store}** — *{win_deal['title'][:70]}*")

            cmp_cols = st.columns(3)
            store_icons = {"Mercado Livre": "🤝", "Shopee": "🧡", "Shein": "👗"}
            for c_idx, st_name in enumerate(("Mercado Livre", "Shopee", "Shein")):
                info = cmp[st_name]
                with cmp_cols[c_idx]:
                    with st.container(border=True):
                        st.markdown(f"**{store_icons[st_name]} {st_name}**")
                        if info["count"] > 0 and info["best_deal"]:
                            bd = info["best_deal"]
                            bd_aff = convert_to_affiliate(
                                bd.get("url", ""),
                                st_name,
                                config,
                                resolve_redirects=True,
                                is_own_shopee_api_link=(bd.get("source") == "Shopee API Oficial"),
                            )
                            st.markdown(f"**{info['count']}** correspondências | Menor: **{bd['price_str']}**")
                            if info["max_discount"] > 0:
                                st.caption(f"Maior desconto nesta busca: -{info['max_discount']}% OFF")
                            st.caption(bd["title"][:65])
                            st.link_button(f"🛒 Ver na {st_name}", bd_aff["url"], use_container_width=True)
                        else:
                            st.caption("Nenhuma correspondência direta no momento.")
                        st.link_button(f"🔎 Pesquisar '{current_kw[:18]}' na loja", info["store_search_url"], use_container_width=True)
        
        # ========================================================
        # BARRA DE DISPARO EM LOTE (ATÉ 10 OFERTAS COM 1 CLIQUE)
        # ========================================================
        selected_deals = [deals[i] for i in sorted(list(st.session_state.selected_indices)) if i < len(deals)][:10]
        
        with st.container(border=True):
            st.markdown(f"#### ⚡ Central de Disparo em Lote • Fila: **{len(selected_deals)}/10** ofertas selecionadas")
            if not has_wa_api:
                st.caption("💡 *Dica de velocidade:* links `WhatsApp Web` sempre abrem nova aba por padrão do navegador. Para envio **instantâneo em 1 clique sem abrir abas**, conecte uma API gratuita/nuvem (Evolution API ou Z-API) na aba **⚙️ Configurações & Afiliados** ou copie o texto pronto nos cards.")
            
            # Botões de Seleção Instantânea (Zero Delay / 1 Clique)
            q_col1, q_col2, q_col3, q_col4 = st.columns([1.5, 1.5, 2.0, 1.2])
            with q_col1:
                if st.button("⚡ Selecionar Top 5 Virais", use_container_width=True, help="Seleciona automaticamente os 5 produtos com maior procura"):
                    st.session_state.selected_indices = set(range(min(5, len(deals))))
                    st.rerun()
            with q_col2:
                if st.button("🔥 Selecionar Top 10 Melhores", use_container_width=True, help="Seleciona os 10 melhores achadinhos em 1 clique"):
                    st.session_state.selected_indices = set(range(min(10, len(deals))))
                    st.rerun()
            with q_col3:
                # Disparo Direto no WhatsApp Web (Super Mensagem 10 em 1)
                super_msg_text = generate_batch_super_message(selected_deals, config) if selected_deals else ""
                super_wa_link = generate_wa_link(super_msg_text, target_mode=wa_mode) if selected_deals else ""
                st.link_button(f"📲 Abrir Super Mensagem ({len(selected_deals)} em 1)", super_wa_link, disabled=(len(selected_deals) == 0), type="secondary" if has_wa_api else "primary", use_container_width=True)
            with q_col4:
                if st.button("🧹 Limpar Fila", use_container_width=True):
                    st.session_state.selected_indices = set()
                    st.rerun()
                    
            if selected_deals:
                with st.expander(f"📋 Ver & Copiar Super Mensagem ({len(selected_deals)} Achadinhos)"):
                    st.code(super_msg_text, language="")
                    
                b_api_col1, b_api_col2 = st.columns([2.5, 1.5])
                with b_api_col1:
                    st.caption("🤖 **Disparo 100% Automático via API (Zero Novas Abas):** Envia cada oferta individualmente com foto + legenda + seu link direto com intervalo anti-ban de 2s direto para o grupo.")
                with b_api_col2:
                    btn_auto_api = st.button("🚀 Disparar Fila Instantâneo (API)", type="primary" if has_wa_api else "secondary", use_container_width=True)
                    
                if btn_auto_api:
                    if not has_wa_api:
                        st.error("⚠️ Configure o Endpoint e o ID do Grupo/Telefone na aba '⚙️ Configurações & Afiliados' (Evolution API ou Z-API) para ativar o disparo instantâneo sem abrir abas.")
                    else:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        success_count = 0
                        for s_idx, d in enumerate(selected_deals):
                            status_text.text(f"Enviando oferta {s_idx+1} de {len(selected_deals)}: {d.get('title')[:30]}...")
                            aff = convert_to_affiliate(
                                d.get("url", ""),
                                d.get("store", ""),
                                config,
                                resolve_redirects=True,
                                is_own_shopee_api_link=(d.get("source") == "Shopee API Oficial"),
                            )
                            caption = generate_whatsapp_copy(d, aff["url"], wa_cfg_global.get("group_link", ""))
                            img_url = d.get("image", "")
                            
                            res = send_whatsapp_media_api(config, image_url=img_url, caption=caption)
                            if res.get("success"):
                                success_count += 1
                            time.sleep(2)
                            progress_bar.progress((s_idx + 1) / len(selected_deals))
                            
                        status_text.empty()
                        st.success(f"🎉 **{success_count} de {len(selected_deals)}** ofertas disparadas instantaneamente para o grupo com foto e seu link!")

        # Grid de Cards (Renderização Leve e Instantânea paginada de 30 em 30)
        cols_per_row = 3
        for i in range(0, len(visible_deals), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(visible_deals):
                    deal = visible_deals[idx]
                    with cols[j]:
                        with st.container(border=True):
                            store_name = deal.get("store", "Loja")
                            disc = deal.get("discount_pct", 0)
                            is_viral = deal.get("is_viral", False)
                            is_flash = deal.get("is_flash", False)
                            is_best = deal.get("is_bestseller", False)
                            
                            # 1. Topo: Seleção e Badges
                            col_chk, col_badges = st.columns([1.15, 1.85])
                            with col_chk:
                                currently_selected = idx in st.session_state.selected_indices
                                is_checked = st.checkbox("Fila (10)", value=currently_selected, key=f"chk_{idx}")
                                if is_checked != currently_selected:
                                    if is_checked:
                                        if len(st.session_state.selected_indices) < 10:
                                            st.session_state.selected_indices.add(idx)
                                        else:
                                            st.toast("⚠️ Limite de 10 ofertas por lote atingido!")
                                            st.session_state[f"chk_{idx}"] = False
                                    else:
                                        st.session_state.selected_indices.discard(idx)
                                    st.rerun()
                                    
                            with col_badges:
                                b_html = '<div style="text-align: right; display: flex; justify-content: flex-end; gap: 4px; flex-wrap: wrap;">'
                                b_html += f'<span class="badge-store">{store_name}</span>'
                                if is_flash:
                                    b_html += '<span class="badge-flash">⚡ RELÂMPAGO</span>'
                                if is_best:
                                    b_html += '<span class="badge-best">🏆 +VENDIDO</span>'
                                elif is_viral:
                                    b_html += '<span class="badge-viral">✨ VIRAL</span>'
                                if disc and disc > 0:
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
                            
                            # 4. Preços Formatados & Provas Sociais Reais
                            p_val = deal.get("price", 0.0)
                            op_val = deal.get("old_price")
                            p_str = f"R$ {p_val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.') if p_val else deal.get("price_str", "Confira")
                            op_str = f"R$ {op_val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.') if (op_val and op_val > p_val) else ""
                            
                            sales_label = deal.get("sales_label", "")
                            if not sales_label and is_viral:
                                sales_label = "✨ Achado Viral em Alta"
                            social_proof_html = (
                                f'<div style="color: #94A3B8; font-size: 0.74rem; margin-top: 3px; font-weight: 600;">{sales_label}</div>'
                                if sales_label else ""
                            )
                            
                            pricing_html = f'''
                            <div class="product-pricing">
                                {f'<span class="price-old">{op_str}</span>' if op_str else ''}
                                <div style="display: flex; align-items: baseline; gap: 6px;">
                                    <span class="price-promo">{p_str}</span>
                                    <span style="font-size: 0.75rem; color: #10B981; font-weight: 700;">no Pix / à vista</span>
                                </div>
                                {social_proof_html}
                                {f'<span class="coupon-tag">🎟️ Cupom: {deal.get("coupon")}</span>' if deal.get("coupon") else ''}
                            </div>
                            '''
                            st.markdown(pricing_html, unsafe_allow_html=True)
                            
                            # 5. Link Direto Limpo + Afiliado Próprio
                            aff_res = convert_to_affiliate(
                                deal.get("url", ""),
                                store_name,
                                config,
                                resolve_redirects=True,
                                is_own_shopee_api_link=(deal.get("source") == "Shopee API Oficial"),
                            )
                            final_aff_link = aff_res["url"]
                            
                            # 6. Envio Rápido WhatsApp (Instantâneo via API sem abrir abas, ou link direto)
                            wa_copy = generate_whatsapp_copy(deal, final_aff_link, wa_cfg_global.get("group_link", ""))
                            wa_direct_link = generate_wa_link(wa_copy, target_mode=wa_mode)
                            if has_wa_api:
                                if st.button("⚡ Enviar Agora (Sem Abrir Abas)", key=f"instant_wa_{idx}", type="primary", use_container_width=True):
                                    res_send = send_whatsapp_media_api(config, image_url=clean_img, caption=wa_copy)
                                    if res_send.get("success"):
                                        st.success("✅ Enviado direto para o grupo!")
                                    else:
                                        st.error(f"Falha API: {res_send.get('error') or res_send.get('response', '')}")
                            else:
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
                                
                            with st.expander("🔗 Link de Afiliado, Foto & Copiar Mensagem"):
                                st.text_input("Link Oficial (Seu Afiliado):", value=final_aff_link, key=f"link_{idx}")
                                st.text_input("Link Direto do Produto (Limpo):", value=aff_res.get("clean_url", deal.get("url", "")), key=f"clean_link_{idx}")
                                st.caption(f"Status: *{aff_res['status']}*")
                                if clean_img:
                                    if st.button("🖼️ Preparar Foto JPG (para WhatsApp)", key=f"prep_jpg_{idx}", use_container_width=True):
                                        jpg_bytes = download_jpeg_bytes_cached(clean_img)
                                        if jpg_bytes:
                                            st.session_state[f"jpg_bytes_{idx}"] = jpg_bytes
                                        else:
                                            st.warning("Não foi possível converter esta imagem agora.")
                                    if st.session_state.get(f"jpg_bytes_{idx}"):
                                        st.download_button(
                                            "⬇️ Baixar Foto JPG Agora",
                                            data=st.session_state[f"jpg_bytes_{idx}"],
                                            file_name=f"mimozae_produto_{idx}.jpg",
                                            mime="image/jpeg",
                                            key=f"dl_jpg_{idx}",
                                            use_container_width=True,
                                        )
                                if has_wa_api:
                                    st.link_button("📲 Abrir no WhatsApp Web (opcional)", wa_direct_link, use_container_width=True)
                                st.caption("📋 Clique no ícone à direita para copiar sem abrir nova aba:")
                                st.code(wa_copy, language="")

        if len(deals) > len(visible_deals):
            rem = len(deals) - len(visible_deals)
            st.write("")
            if st.button(f"➕ Carregar +30 Ofertas ({rem} restantes no radar)", type="secondary", use_container_width=True):
                st.session_state.display_limit += 30
                st.rerun()
    elif not (is_compare_mode and not current_kw):
        st.info("💡 Nenhuma promoção com link direto encontrada para esses filtros. Tente outro termo, reduza o desconto mínimo ou desmarque *'🚫 Ocultar Links Promobit'*.")


# ==========================================
# ABA 2: ANALISADOR DE LINK AVULSO
# ==========================================
with tab_analyzer:
    st.subheader("🔗 Cole qualquer link de produto para gerar seu link de afiliado e posts")
    st.write("Achou uma oferta no **Mercado Livre**, **Shopee** ou **Shein** (ou até link do Promobit/Pelando/encurtado)? Cole abaixo para extrair o link limpo do produto e aplicar o SEU afiliado:")
    
    input_url = st.text_input("Cole o link aqui:", placeholder="https://www.mercadolivre.com.br/... ou https://shopee.com.br/... ou https://br.shein.com/...", key="manual_url")
    
    if st.button("⚡ Processar Link & Gerar Afiliado", type="primary"):
        if input_url:
            with st.spinner("Removendo links de terceiros e gerando o seu link de afiliado..."):
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
                            if parsed.get("old_price_str"):
                                st.markdown(f"**De:** ~{parsed['old_price_str']}~")
                            st.markdown(f"**Por:** <span class='price-promo'>{parsed['price_str']}</span>", unsafe_allow_html=True)
                            if parsed.get("discount_pct"):
                                st.markdown(f"<span class='badge-discount'>-{parsed['discount_pct']}% OFF</span>", unsafe_allow_html=True)
                            if parsed.get("is_viral"):
                                st.markdown('<span class="badge-viral">✨ PRODUTO VIRAL</span>', unsafe_allow_html=True)
                                
                            aff = convert_to_affiliate(parsed.get("url") or input_url, parsed["store"], config, resolve_redirects=True)
                            st.text_input("🔗 Link Oficial de Afiliado (Sua Conta):", value=aff["url"])
                            st.text_input("🧼 Link Limpo do Produto:", value=aff.get("clean_url", parsed.get("url", "")))
                            st.caption(f"Status: {aff['status']}")
                            
                            wa_text = generate_whatsapp_copy(parsed, aff["url"], wa_cfg_global.get("group_link", ""))
                            st.code(wa_text, language="")
                            
                            wa_open = generate_wa_link(wa_text, target_mode=wa_mode)
                            if has_wa_api:
                                if st.button("⚡ Enviar Agora via API (Sem Abrir Abas)", key="analyzer_api_send", type="primary", use_container_width=True):
                                    res_an = send_whatsapp_media_api(config, image_url=clean_p_img, caption=wa_text)
                                    if res_an.get("success"):
                                        st.success("✅ Enviado para o grupo!")
                                    else:
                                        st.error(f"Falha API: {res_an.get('error') or res_an.get('response', '')}")
                                st.link_button("📲 Abrir WhatsApp Web (opcional)", wa_open, use_container_width=True)
                            else:
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
                
            post_store = st.text_input("Nome da Loja:", value="Shopee", key="studio_store")
            post_theme = st.selectbox("Paleta de Cores:", options=list(THEMES.keys()), index=0, key="studio_theme")
            post_format = st.radio("Formato da Imagem:", options=["Feed (1:1 / 1080x1080)", "Story (9:16 / 1080x1920)"], index=0, key="studio_fmt")
            format_slug = "feed" if "Feed" in post_format else "story"
            
            st.markdown("#### 🖼️ Imagem do Produto")
            img_option = st.radio("Origem da Imagem:", ["URL da Imagem", "Fazer Upload"], horizontal=True, key="studio_img_opt")
            
            post_img_url = ""
            uploaded_file = None
            if img_option == "URL da Imagem":
                post_img_url = st.text_input("Link da imagem:", value="", placeholder="Cole a URL da imagem do produto (opcional)...", key="studio_img_url")
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
                buf = io.BytesIO()
                final_img.save(buf, format="PNG")
                byte_im = buf.getvalue()
            else:
                byte_im = get_cached_studio_png(
                    title=post_title,
                    price_str=post_price,
                    old_price_str=post_old_price,
                    discount_pct=post_disc,
                    store=post_store,
                    image_url=post_img_url,
                    format_type=format_slug,
                    instagram_handle=config.get("instagram", {}).get("handle", "@mimozae.of"),
                    theme_name=post_theme
                )
            
            render_deal_image(byte_im, caption=f"Card Gerado - {post_format}", width=440 if format_slug == "feed" else 330)
            
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
                    
    with st.form(f"settings_form_{curr_prof}"):
        st.markdown(f"### 🛒 Afiliados Ativos (Mercado Livre, Shopee & Shein) — {curr_prof}")
        tags = config.get("affiliate_tags", {})
        
        col_tag1, col_tag2, col_tag3 = st.columns(3)
        with col_tag1:
            ml = st.text_input("Mercado Livre (Matt Tool ID):", value=tags.get("mercadolivre", ""), key=f"cfg_ml_{curr_prof}", help="Ex: seu código numérico matt_tool do portal de afiliados ML")
        with col_tag2:
            shp = st.text_input("Shopee (ID an_... ou Sub_ID):", value=tags.get("shopee", ""), key=f"cfg_shp_{curr_prof}", help="Ex: an_18303210286 ou Sub_ID personalizado")
        with col_tag3:
            shn = st.text_input("Shein (Affiliate Tag / ID):", value=tags.get("shein", ""), key=f"cfg_shn_{curr_prof}", help="Ex: seu aff_id ou parâmetro de afiliado Shein")

        st.markdown("#### 🧡 API Oficial Shopee Afiliados (Recomendado — Gera Link `s.shopee.com.br` da SUA Conta)")
        st.caption("Em [affiliate.shopee.com.br](https://affiliate.shopee.com.br) > **API Aberta**, copie seu App ID e Secret. Além de buscar mais vendidos direto da Shopee, **todos os links da Shopee serão convertidos automaticamente em links oficiais da sua conta (`generateShortLink`)**.")
        col_shp1, col_shp2 = st.columns(2)
        with col_shp1:
            shp_app_id = st.text_input("Shopee Open API App ID:", value=tags.get("shopee_app_id", ""), key=f"cfg_shp_id_{curr_prof}", help="Ex: 18392019283")
        with col_shp2:
            shp_app_secret = st.text_input("Shopee Open API Secret Key:", value=tags.get("shopee_app_secret", ""), type="password", key=f"cfg_shp_sec_{curr_prof}")
            
        st.markdown("---")
        st.markdown(f"### 📲 Configurações do WhatsApp — {curr_prof}")
        st.caption("Personalize como este operador envia mensagens para seus grupos ou contatos:")
        
        wa_cfg = config.get("whatsapp", {})
        current_mode = wa_cfg.get("mode", "web")
        
        mode_idx = 0 if current_mode == "web" else (1 if current_mode == "app" else 2)
        selected_wa_mode = st.radio(
            "Destino do Clique de Envio (quando não usar API):",
            options=[
                "🌐 WhatsApp Web Direto (web.whatsapp.com - Sem tela intermediária!) [RECOMENDADO]",
                "💻 Aplicativo WhatsApp Desktop (Windows App nativo)",
                "📱 WhatsApp Universal (api.whatsapp.com)"
            ],
            index=mode_idx,
            key=f"cfg_wa_mode_{curr_prof}",
        )
        mode_slug = "web" if "web.whatsapp.com" in selected_wa_mode else ("app" if "Desktop" in selected_wa_mode else "universal")
        
        wa_grp_link = st.text_input(
            "Link de Convite do Grupo VIP deste Operador (opcional, aparece no rodapé):",
            value=wa_cfg.get("group_link", ""),
            key=f"cfg_wa_grp_{curr_prof}",
            help="Ex: https://chat.whatsapp.com/..."
        )
        
        st.markdown("---")
        st.markdown("### 🤖 Envio Instantâneo Sem Abrir Novas Abas (WhatsApp API)")
        st.caption("Conecte uma instância de WhatsApp via QR Code (Evolution API, Z-API ou Webhook). Com isso preenchido, o botão principal dos cards muda para **⚡ Enviar Agora (Sem Abrir Abas)** e dispara direto com foto + texto em menos de 1 segundo:")
        
        col_wa1, col_wa2 = st.columns(2)
        with col_wa1:
            wa_api_type = st.selectbox(
                "Tipo de Integração / API:",
                options=["Evolution API (v1 / v2)", "Z-API", "Webhook Genérico"],
                index=0,
                key=f"cfg_wa_type_{curr_prof}",
            )
            wa_endpoint = st.text_input(
                "URL do Endpoint da API:",
                value=wa_cfg.get("api_endpoint", wa_cfg.get("webhook_url", "")),
                key=f"cfg_wa_ep_{curr_prof}",
                help="Ex: https://sua-api.com/message/sendMedia/instancia ou https://api.z-api.io/instances/.../token/.../send-image"
            )
            
        with col_wa2:
            wa_token = st.text_input(
                "API Key / Token de Acesso:",
                value=wa_cfg.get("api_token", ""),
                type="password",
                key=f"cfg_wa_tok_{curr_prof}",
                help="Sua chave secreta da API do WhatsApp"
            )
            wa_group_id = st.text_input(
                "ID do Grupo de Destino ou Telefone:",
                value=wa_cfg.get("target_group", ""),
                key=f"cfg_wa_gid_{curr_prof}",
                help="Ex: 1203630248293@g.us (ID do grupo) ou 5511999999999"
            )
            
        st.markdown("---")
        st.markdown("### 📸 Instagram (@mimozae.of)")
        col_net1, col_net2 = st.columns(2)
        with col_net1:
            ig_handle = st.text_input("Usuário do Instagram:", value=config.get("instagram", {}).get("handle", "@mimozae.of"), key=f"cfg_ig_h_{curr_prof}")
        with col_net2:
            ig_cta = st.text_input("Chamada (CTA) Padrão:", value=config.get("instagram", {}).get("default_cta", "Comente 'EU QUERO' para receber o link no direct!"), key=f"cfg_ig_c_{curr_prof}")
            
        submitted = st.form_submit_button(f"💾 Salvar Configurações no Perfil '{curr_prof}'", type="primary")
        
        if submitted:
            merged_tags = dict(tags)
            merged_tags.update({
                "mercadolivre": ml.strip(),
                "shopee": shp.strip(),
                "shopee_app_id": shp_app_id.strip(),
                "shopee_app_secret": shp_app_secret.strip(),
                "shein": shn.strip(),
            })
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
                "affiliate_tags": merged_tags,
            }
            if save_profile(curr_prof, new_conf):
                st.success(f"✅ Configurações salvas com sucesso no perfil de **{curr_prof}**!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Erro ao salvar configurações.")

    st.markdown("---")
    with st.expander("🔒 Blindar IDs de Afiliado no Streamlit Cloud (Para Nunca Sumir ao Atualizar ou Recarregar)", expanded=True):
        st.caption(
            "No Streamlit Community Cloud, o servidor reinicia o disco sempre que há atualização no GitHub. "
            "Depois de salvar seus IDs acima, **copie o bloco TOML abaixo** (ícone no canto direito) e cole em **Manage app (canto inferior direito) > Settings > Secrets > Save** — "
            "assim seus IDs ficam gravados de forma 100% permanente na nuvem!"
        )
        full_saved_now = load_full_config()
        secrets_toml_str = generate_secrets_toml(full_saved_now)
        st.code(secrets_toml_str, language="toml")

        bk_col1, bk_col2 = st.columns(2)
        with bk_col1:
            import json as _json_bk
            st.download_button(
                "📤 Exportar Backup (.json)",
                data=_json_bk.dumps(full_saved_now, indent=2, ensure_ascii=False),
                file_name="mimozae_backup_afiliados.json",
                mime="application/json",
                use_container_width=True,
            )
        with bk_col2:
            up_bk = st.file_uploader("📥 Restaurar Backup (.json)", type=["json"], key="restore_cfg_json")
            if up_bk is not None:
                try:
                    import json as _json_bk2
                    restored = _json_bk2.load(up_bk)
                    if isinstance(restored, dict) and "profiles" in restored:
                        save_full_config(restored)
                        st.success("✅ Backup restaurado! Recarregando...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Arquivo .json inválido.")
                except Exception as ex:
                    st.error(f"Erro ao importar: {ex}")
