import re
import vk_api
from datetime import datetime
import database as db

def get_user_id_from_mention(text):
    """Извлекает ID из упоминания [id123|name] или @username"""
    match = re.search(r'\[id(\d+)\|', text)
    if match:
        return int(match.group(1))
    
    match = re.search(r'@(\w+)', text)
    if match:
        return None
    
    match = re.search(r'(\d+)', text)
    if match:
        return int(match.group(1))
    
    return None

def get_user_info(vk, user_id):
    """Получить информацию о пользователе"""
    try:
        user = vk.users.get(
            user_ids=user_id, 
            fields="first_name,last_name,sex,bdate,city,country,photo_100,online,last_seen"
        )[0]
        return user
    except:
        return None

def format_user(user):
    if user and 'id' in user:
        return f"[id{user['id']}|{user.get('first_name', '')} {user.get('last_name', '')}]"
    return f"id{user_id}"

def parse_duration(text):
    """Парсит длительность: 1d, 2w, 3m, 1y, forever"""
    text = text.lower()
    if text in ["forever", "навсегда", "∞", "бессрочно"]:
        return -1
    
    match = re.search(r'(\d+)([dwmy])', text)
    if not match:
        return 0
    
    num = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'd':
        return num
    elif unit == 'w':
        return num * 7
    elif unit == 'm':
        return num * 30
    elif unit == 'y':
        return num * 365
    return 0

def get_nickname_or_name(vk, user_id, chat_id):
    """Получает ник или имя пользователя"""
    nickname = db.get_nickname(user_id, chat_id)
    if nickname:
        return nickname
    
    user = get_user_info(vk, user_id)
    if user:
        return f"{user['first_name']} {user['last_name']}"
    return f"id{user_id}"

def format_duration(until_date):
    """Форматирует срок в читаемый вид"""
    if until_date == "forever":
        return "🔨 Навсегда"
    
    try:
        until = datetime.fromisoformat(until_date)
        now = datetime.now()
        
        if now > until:
            return "✅ Истек"
        
        remaining = until - now
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0 and days == 0:
            parts.append(f"{minutes}м")
        
        return "⏱ " + " ".join(parts) if parts else "⏱ Менее минуты"
    except:
        return until_date

def get_remaining_time(until_date):
    """Получает оставшееся время в виде строки"""
    if until_date == "forever":
        return "Бессрочный бан"
    
    try:
        until = datetime.fromisoformat(until_date)
        now = datetime.now()
        
        if now > until:
            return "Бан истек"
        
        remaining = until - now
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        return f"Осталось: {days} дней, {hours} часов, {minutes} минут"
    except:
        return ""

def is_admin(user_id, chat_id):
    """Проверяет, является ли пользователь администратором"""
    from config import OWNER_ID, DEVELOPER_ID
    if user_id in [OWNER_ID, DEVELOPER_ID]:
        return True
    role = db.get_role(user_id, chat_id)
    return role is not None

def get_user_rank(user_id, chat_id):
    """Получает ранг пользователя"""
    if user_id in [config.OWNER_ID, config.DEVELOPER_ID]:
        return "Владелец"
    role = db.get_role(user_id, chat_id)
    return role or "Пользователь"

def get_role_permissions(role):
    """Получает права для роли"""
    # Базовая система прав
    permissions = {
        "can_kick": False,
        "can_ban": False,
        "can_mute": False,
        "can_set_role": False,
        "can_manage_settings": False,
    }
    
    # В зависимости от уровня роли
    level = get_role_level(role) if role in ROLE_HIERARCHY else 999
    
    if level <= 5:  # Высшее руководство
        permissions.update({
            "can_kick": True,
            "can_ban": True,
            "can_mute": True,
            "can_set_role": True,
            "can_manage_settings": True,
        })
    elif level <= 10:  # Администраторы
        permissions.update({
            "can_kick": True,
            "can_ban": True,
            "can_mute": True,
            "can_set_role": False,
            "can_manage_settings": False,
        })
    elif level <= 15:  # Модераторы
        permissions.update({
            "can_kick": True,
            "can_ban": False,
            "can_mute": True,
            "can_set_role": False,
            "can_manage_settings": False,
        })
    
    return permissions