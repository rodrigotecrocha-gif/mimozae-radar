import copy
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
BACKUP_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mimozae_radar")
BACKUP_CONFIG_FILE = os.path.join(BACKUP_CONFIG_DIR, "config.json")

DEFAULT_PROFILE_DATA = {
    "instagram": {
        "handle": "@mimozae.of",
        "default_cta": "Comente 'EU QUERO' para receber o link com desconto no Direct!",
        "hashtags": "#achadinhos #promocao #desconto #ofertas #mimozae #comprinhas #blackfriday #achados",
    },
    "whatsapp": {
        "group_link": "",
        "api_endpoint": "",
        "api_token": "",
        "target_group": "",
        "mode": "web",
        "api_type": "evolution",
        "webhook_url": "",
    },
    "affiliate_tags": {
        "amazon": "",
        "mercadolivre": "",
        "shopee": "",
        "shopee_app_id": "",
        "shopee_app_secret": "",
        "magalu": "",
        "casasbahia": "",
        "shein": "",
        "aliexpress": "",
        "dafiti": "",
    },
}


def _default_full_config() -> dict:
    return {
        "active_profile": "Rodrigo",
        "profiles": {
            "Rodrigo": copy.deepcopy(DEFAULT_PROFILE_DATA),
            "Parceira": copy.deepcopy(DEFAULT_PROFILE_DATA),
        },
    }


def _normalize_profile(prof_data: dict) -> dict:
    normalized = copy.deepcopy(DEFAULT_PROFILE_DATA)
    if not isinstance(prof_data, dict):
        return normalized
    for section, defaults in DEFAULT_PROFILE_DATA.items():
        val = prof_data.get(section)
        if isinstance(defaults, dict) and isinstance(val, dict):
            for subk, subv in val.items():
                if subk in normalized[section] and subv is not None:
                    normalized[section][subk] = subv
    return normalized


def _merge_non_empty(base_full: dict, overlay_full: dict) -> dict:
    """Preserva IDs/chaves já salvos: nunca sobrescreve valores preenchidos com string vazia."""
    if not isinstance(overlay_full, dict):
        return base_full
    if overlay_full.get("active_profile"):
        base_full["active_profile"] = overlay_full["active_profile"]
    for prof_name, ov_prof in (overlay_full.get("profiles") or {}).items():
        if prof_name not in base_full["profiles"]:
            base_full["profiles"][prof_name] = _normalize_profile(ov_prof)
            continue
        target_prof = base_full["profiles"][prof_name]
        if not isinstance(ov_prof, dict):
            continue
        for section, ov_sec in ov_prof.items():
            if isinstance(ov_sec, dict) and isinstance(target_prof.get(section), dict):
                for k, v in ov_sec.items():
                    if v not in (None, ""):
                        target_prof[section][k] = v
    return base_full


def _read_json_safe(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        if "profiles" not in data:
            data = {
                "active_profile": "Rodrigo",
                "profiles": {
                    "Rodrigo": _normalize_profile(data),
                    "Parceira": copy.deepcopy(DEFAULT_PROFILE_DATA),
                },
            }
        for pname in list(data.get("profiles", {}).keys()):
            data["profiles"][pname] = _normalize_profile(data["profiles"][pname])
        return data
    except Exception as e:
        print("Erro ao ler config:", path, e)
        return None


def _load_st_secrets_overlay() -> dict | None:
    """Lê credenciais permanentes configuradas em Streamlit Cloud Secrets (Manage app > Settings > Secrets)."""
    try:
        import streamlit as st
        sec = st.secrets
        if not sec:
            return None
        sec_dict = dict(sec)
        overlay = {"profiles": {}}
        if sec_dict.get("active_profile"):
            overlay["active_profile"] = str(sec_dict["active_profile"])

        if "profiles" in sec_dict and hasattr(sec_dict["profiles"], "items"):
            for pname, pval in sec_dict["profiles"].items():
                p_clean = {}
                for section in ("instagram", "whatsapp", "affiliate_tags"):
                    sval = dict(pval).get(section) if hasattr(pval, "items") else None
                    if sval and hasattr(sval, "items"):
                        p_clean[section] = dict(sval)
                overlay["profiles"][str(pname)] = _normalize_profile(p_clean)
            return overlay

        # Suporta formato plano em st.secrets ([affiliate_tags] / [whatsapp] / [instagram]) para perfil ativo
        flat_prof = {}
        for section in ("instagram", "whatsapp", "affiliate_tags"):
            if section in sec_dict and hasattr(sec_dict[section], "items"):
                flat_prof[section] = dict(sec_dict[section])
        if flat_prof:
            target_p = str(sec_dict.get("active_profile") or "Rodrigo")
            overlay["profiles"][target_p] = _normalize_profile(flat_prof)
            return overlay
    except Exception:
        pass
    return None


def load_full_config():
    data = _default_full_config()

    repo_data = _read_json_safe(CONFIG_FILE)
    if repo_data:
        data = _merge_non_empty(data, repo_data)

    backup_data = _read_json_safe(BACKUP_CONFIG_FILE)
    if backup_data:
        data = _merge_non_empty(data, backup_data)

    secrets_data = _load_st_secrets_overlay()
    if secrets_data:
        data = _merge_non_empty(data, secrets_data)

    return data


def save_full_config(config_dict):
    ok = False
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
        ok = True
    except Exception as e:
        print("Erro ao salvar config local:", e)

    try:
        os.makedirs(BACKUP_CONFIG_DIR, exist_ok=True)
        with open(BACKUP_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
        ok = True
    except Exception as e:
        print("Erro ao salvar backup persistente:", e)

    return ok


def get_profile(profile_name: str = None):
    full = load_full_config()
    profiles = full.get("profiles", {})
    if not profile_name or profile_name not in profiles:
        profile_name = full.get("active_profile", list(profiles.keys())[0] if profiles else "Rodrigo")
    return profiles.get(profile_name, copy.deepcopy(DEFAULT_PROFILE_DATA))


def save_profile(profile_name: str, profile_data: dict):
    full = load_full_config()
    if "profiles" not in full:
        full["profiles"] = {}
    full["profiles"][profile_name] = _normalize_profile(profile_data)
    full["active_profile"] = profile_name
    return save_full_config(full)


def create_new_profile(profile_name: str):
    clean_name = profile_name.strip()
    if not clean_name:
        return False
    full = load_full_config()
    if "profiles" not in full:
        full["profiles"] = {}
    if clean_name not in full["profiles"]:
        full["profiles"][clean_name] = copy.deepcopy(DEFAULT_PROFILE_DATA)
        full["active_profile"] = clean_name
        save_full_config(full)
    return True


def generate_secrets_toml(full_cfg: dict) -> str:
    """Gera o bloco TOML pronto para colar em Streamlit Cloud > Settings > Secrets e nunca perder seus IDs."""
    def _q(val) -> str:
        return json.dumps(str(val or ""), ensure_ascii=False)

    lines = [f'active_profile = {_q(full_cfg.get("active_profile", "Rodrigo"))}', ""]
    for pname, pdata in full_cfg.get("profiles", {}).items():
        safe_p = pname if pname.isidentifier() else _q(pname)
        aff = pdata.get("affiliate_tags", {})
        wa = pdata.get("whatsapp", {})
        ig = pdata.get("instagram", {})

        lines.append(f"[profiles.{safe_p}.affiliate_tags]")
        for k in ("mercadolivre", "shopee", "shopee_app_id", "shopee_app_secret", "shein"):
            lines.append(f"{k} = {_q(aff.get(k, ''))}")
        lines.append("")
        lines.append(f"[profiles.{safe_p}.whatsapp]")
        for k in ("mode", "api_type", "api_endpoint", "api_token", "target_group", "group_link"):
            lines.append(f"{k} = {_q(wa.get(k, ''))}")
        lines.append("")
        lines.append(f"[profiles.{safe_p}.instagram]")
        for k in ("handle", "default_cta"):
            lines.append(f"{k} = {_q(ig.get(k, ''))}")
        lines.append("")
    return "\n".join(lines).strip()


def load_config():
    return get_profile()


def save_config(cfg):
    return save_profile("Rodrigo", cfg)
