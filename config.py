import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "241266509"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
# Добавьте в config.py
CONFIRMATION_TOKEN = "fbe8394f"

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "welcome_enabled": True,
    "welcome_message": "👋 Добро пожаловать, {user}! Ознакомься с правилами.",
    "farewell_enabled": True,
    "farewell_message": "👋 {user} покинул нас. Будем скучать!",
    
    "antispam_enabled": True,
    "antispam_seconds": 3,
    "antispam_warns": 3,
    
    "antimat_enabled": True,
    "mat_words": [],
    "antimat_action": "warn",
    
    "antilink_enabled": True,
    "allowed_domains": ["vk.com", "youtube.com", "youtu.be"],
    "antilink_action": "warn",
    
    "anticaps_enabled": True,
    "caps_limit": 70,
    "anticaps_action": "warn",
    
    "auto_mute_duration": 10,
    "max_warns": 3,
    "warn_action": "mute",
    
    "ban_notify": True,
    "unban_notify": True,
}