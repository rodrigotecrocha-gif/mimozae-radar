import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_PROFILE_DATA = {
    "instagram": {
        "handle": "@mimozae.of",
        "default_cta": "Comente 'EU QUERO' para receber o link com desconto no Direct!",
        "hashtags": "#achadinhos #promocao #desconto #ofertas #mimozae #comprinhas #blackfriday #achados"
    },
    "whatsapp": {
        "group_link": "",
        "api_endpoint": "",
        "api_token": "",
        "target_group": "",
        "mode": "web",
        "api_type": "evolution",
        "webhook_url": ""
    },
    "affiliate_tags": {
        "amazon": "",
        "mercadolivre": "",
        "shopee": "",
        "magalu": "",
        "casasbahia": "",
        "shein": "",
        "aliexpress": "",
        "dafiti": ""
    }
}

def load_full_config():
    if not os.path.exists(CONFIG_FILE):
        initial = {
            "active_profile": "Rodrigo",
            "profiles": {
                "Rodrigo": json.loads(json.dumps(DEFAULT_PROFILE_DATA)),
                "Parceira": json.loads(json.dumps(DEFAULT_PROFILE_DATA))
            }
        }
        save_full_config(initial)
        return initial
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Migração automática de formato legado (sem 'profiles')
        if "profiles" not in data:
            old_data = data
            data = {
                "active_profile": "Rodrigo",
                "profiles": {
                    "Rodrigo": old_data,
                    "Parceira": json.loads(json.dumps(DEFAULT_PROFILE_DATA))
                }
            }
            save_full_config(data)
            
        # Garante estrutura completa em todos os perfis
        for prof_name, prof_data in data.get("profiles", {}).items():
            for k, val in DEFAULT_PROFILE_DATA.items():
                if k not in prof_data:
                    prof_data[k] = val
                elif isinstance(val, dict):
                    for subk, subv in val.items():
                        if subk not in prof_data[k]:
                            prof_data[k][subk] = subv
                            
        return data
    except Exception as e:
        print("Erro ao carregar config:", e)
        return {
            "active_profile": "Rodrigo",
            "profiles": {
                "Rodrigo": json.loads(json.dumps(DEFAULT_PROFILE_DATA)),
                "Parceira": json.loads(json.dumps(DEFAULT_PROFILE_DATA))
            }
        }

def save_full_config(config_dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print("Erro ao salvar config:", e)
        return False

def get_profile(profile_name: str = None):
    full = load_full_config()
    profiles = full.get("profiles", {})
    if not profile_name or profile_name not in profiles:
        profile_name = full.get("active_profile", list(profiles.keys())[0] if profiles else "Rodrigo")
    return profiles.get(profile_name, json.loads(json.dumps(DEFAULT_PROFILE_DATA)))

def save_profile(profile_name: str, profile_data: dict):
    full = load_full_config()
    if "profiles" not in full:
        full["profiles"] = {}
    full["profiles"][profile_name] = profile_data
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
        full["profiles"][clean_name] = json.loads(json.dumps(DEFAULT_PROFILE_DATA))
        full["active_profile"] = clean_name
        save_full_config(full)
    return True

# Retrocompatibilidade
def load_config():
    return get_profile()

def save_config(config_dict):
    full = load_full_config()
    active = full.get("active_profile", "Rodrigo")
    return save_profile(active, config_dict)
