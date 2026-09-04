import sqlite3
import json
import re
import vk_api
from vk_api.utils import get_random_id
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# ==================== ЗАГРУЗКА НАСТРОЕК ====================

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
CONFIRMATION_TOKEN = os.getenv("CONFIRMATION_TOKEN", "")

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "welcome_enabled": True,
    "welcome_message": "👋 Добро пожаловать, {user}! Ознакомься с правилами.",
    "farewell_enabled": True,
    "farewell_message": "👋 {user} покинул нас. Будем скучать!",
    "antispam_enabled": True,
    "antispam_seconds": 3,
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
}

# ==================== БАЗА ДАННЫХ ====================

DB_NAME = "bot_manager.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Роли пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            chat_id INTEGER,
            role TEXT,
            assigned_by INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # Кастомные роли
    cur.execute('''
        CREATE TABLE IF NOT EXISTS custom_roles (
            chat_id INTEGER,
            role_name TEXT,
            priority INTEGER,
            created_by INTEGER,
            permissions TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, role_name)
        )
    ''')
    
    # Баны
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER,
            chat_id INTEGER,
            reason TEXT,
            banned_by INTEGER,
            until_date TEXT,
            is_global BOOLEAN DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # Муты
    cur.execute('''
        CREATE TABLE IF NOT EXISTS mutes (
            user_id INTEGER,
            chat_id INTEGER,
            until_date TEXT,
            muted_by INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # Ники
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nicknames (
            user_id INTEGER,
            chat_id INTEGER,
            nickname TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # Варны
    cur.execute('''
        CREATE TABLE IF NOT EXISTS warns (
            user_id INTEGER,
            chat_id INTEGER,
            count INTEGER DEFAULT 0,
            last_warn DATETIME,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    
    # Связка бесед
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_ids TEXT
        )
    ''')
    
    # Настройки чатов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            settings TEXT
        )
    ''')
    
    # Логи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            user_id INTEGER,
            target_id INTEGER,
            chat_id INTEGER,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Чёрный список слов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bad_words (
            chat_id INTEGER,
            word TEXT,
            PRIMARY KEY (chat_id, word)
        )
    ''')
    
    # Белый список ссылок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS allowed_domains (
            chat_id INTEGER,
            domain TEXT,
            PRIMARY KEY (chat_id, domain)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[DB] Инициализация завершена")

# === РОЛИ ===
def set_role(user_id, chat_id, role, assigned_by):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO user_roles (user_id, chat_id, role, assigned_by)
        VALUES (?, ?, ?, ?)
    ''', (user_id, chat_id, role, assigned_by))
    conn.commit()
    conn.close()

def get_role(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT role FROM user_roles WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def remove_role(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM user_roles WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def get_all_roles(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, role FROM user_roles WHERE chat_id = ?", (chat_id,))
    results = cur.fetchall()
    conn.close()
    return results

# === КАСТОМНЫЕ РОЛИ ===
def add_custom_role(chat_id, role_name, priority, created_by, permissions=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO custom_roles (chat_id, role_name, priority, created_by, permissions)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, role_name, priority, created_by, json.dumps(permissions or {})))
    conn.commit()
    conn.close()

def get_custom_role(chat_id, role_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM custom_roles WHERE chat_id = ? AND role_name = ?", (chat_id, role_name))
    result = cur.fetchone()
    conn.close()
    return result

def get_all_custom_roles(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT role_name, priority FROM custom_roles WHERE chat_id = ? ORDER BY priority", (chat_id,))
    result = cur.fetchall()
    conn.close()
    return result

def remove_custom_role(chat_id, role_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM custom_roles WHERE chat_id = ? AND role_name = ?", (chat_id, role_name))
    conn.commit()
    conn.close()

# === БАНЫ ===
def ban_user(user_id, chat_id, reason, banned_by, days=0, is_global=False):
    until_date = None
    if days > 0:
        until_date = (datetime.now() + timedelta(days=days)).isoformat()
    elif days == -1:
        until_date = "forever"
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO bans (user_id, chat_id, reason, banned_by, until_date, is_global)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, chat_id, reason, banned_by, until_date, is_global))
    conn.commit()
    conn.close()

def unban_user(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM bans WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def is_banned(user_id, chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if chat_id:
        cur.execute("SELECT until_date FROM bans WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    else:
        cur.execute("SELECT until_date FROM bans WHERE user_id = ? AND is_global = 1", (user_id,))
    result = cur.fetchone()
    conn.close()
    
    if result:
        until = result[0]
        if until == "forever":
            return True
        if until and datetime.now() < datetime.fromisoformat(until):
            return True
    return False

def get_ban_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM bans WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result

def get_all_bans(chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    if chat_id:
        cur.execute('''
            SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
            FROM bans 
            WHERE chat_id = ? OR is_global = 1
            ORDER BY timestamp DESC
        ''', (chat_id,))
    else:
        cur.execute('''
            SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
            FROM bans 
            ORDER BY timestamp DESC
        ''')
    
    results = cur.fetchall()
    conn.close()
    return results

def get_ban_history(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT chat_id, reason, banned_by, until_date, timestamp, is_global 
        FROM bans 
        WHERE user_id = ?
        ORDER BY timestamp DESC
    ''', (user_id,))
    results = cur.fetchall()
    conn.close()
    return results

def get_ban_count(chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    if chat_id:
        cur.execute('SELECT COUNT(*) FROM bans WHERE chat_id = ? OR is_global = 1', (chat_id,))
    else:
        cur.execute('SELECT COUNT(*) FROM bans')
    
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_active_bans(chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    if chat_id:
        cur.execute('''
            SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
            FROM bans 
            WHERE (chat_id = ? OR is_global = 1) 
            AND (until_date = "forever" OR until_date > ?)
            ORDER BY timestamp DESC
        ''', (chat_id, now))
    else:
        cur.execute('''
            SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
            FROM bans 
            WHERE until_date = "forever" OR until_date > ?
            ORDER BY timestamp DESC
        ''', (now,))
    
    results = cur.fetchall()
    conn.close()
    return results

def get_ban_stats():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM bans')
    total = cur.fetchone()[0]
    
    now = datetime.now().isoformat()
    cur.execute('''
        SELECT COUNT(*) FROM bans 
        WHERE until_date = "forever" OR until_date > ?
    ''', (now,))
    active = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM bans WHERE is_global = 1')
    global_bans = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM bans WHERE until_date = "forever"')
    forever = cur.fetchone()[0]
    
    conn.close()
    return {
        "total": total,
        "active": active,
        "global": global_bans,
        "forever": forever
    }

def search_bans(query, chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    sql = '''
        SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
        FROM bans 
        WHERE user_id LIKE ? OR reason LIKE ?
    '''
    params = (f'%{query}%', f'%{query}%')
    
    if chat_id:
        sql += ' AND (chat_id = ? OR is_global = 1)'
        params = params + (chat_id,)
    
    sql += ' ORDER BY timestamp DESC'
    
    cur.execute(sql, params)
    results = cur.fetchall()
    conn.close()
    return results

# === МУТЫ ===
def mute_user(user_id, chat_id, minutes, muted_by, reason=""):
    until_date = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO mutes (user_id, chat_id, until_date, muted_by, reason)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, chat_id, until_date, muted_by, reason))
    conn.commit()
    conn.close()

def unmute_user(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM mutes WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def is_muted(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT until_date FROM mutes WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    result = cur.fetchone()
    conn.close()
    
    if result and datetime.now() < datetime.fromisoformat(result[0]):
        return True
    
    if result:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM mutes WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()
        conn.close()
    
    return False

def get_mute_time(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT until_date FROM mutes WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    result = cur.fetchone()
    conn.close()
    return datetime.fromisoformat(result[0]) if result else None

def get_all_mutes(chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if chat_id:
        cur.execute("SELECT user_id, until_date, muted_by, reason FROM mutes WHERE chat_id = ?", (chat_id,))
    else:
        cur.execute("SELECT user_id, chat_id, until_date, muted_by, reason FROM mutes")
    results = cur.fetchall()
    conn.close()
    return results

# === НИКИ ===
def set_nickname(user_id, chat_id, nickname):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO nicknames (user_id, chat_id, nickname) VALUES (?, ?, ?)',
                (user_id, chat_id, nickname))
    conn.commit()
    conn.close()

def get_nickname(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nickname FROM nicknames WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

# === ВАРНЫ ===
def add_warn(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO warns (user_id, chat_id, count, last_warn)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET 
            count = count + 1,
            last_warn = ?
    ''', (user_id, chat_id, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    
    cur.execute("SELECT count FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    count = cur.fetchone()[0]
    conn.close()
    return count

def reset_warns(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def get_warns(user_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT count FROM warns WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

# === СВЯЗКА БЕСЕД ===
def link_chats(chat_ids):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO chat_links (chat_ids) VALUES (?)", (json.dumps(chat_ids),))
    conn.commit()
    conn.close()

def get_linked_chats():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT chat_ids FROM chat_links")
    results = cur.fetchall()
    conn.close()
    linked = []
    for row in results:
        linked.extend(json.loads(row[0]))
    return linked

def unlink_chat(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT chat_ids FROM chat_links")
    results = cur.fetchall()
    for row in results:
        ids = json.loads(row[0])
        if chat_id in ids:
            ids.remove(chat_id)
            cur.execute("UPDATE chat_links SET chat_ids = ? WHERE chat_ids = ?", 
                       (json.dumps(ids), json.dumps(row[0])))
    conn.commit()
    conn.close()

# === НАСТРОЙКИ ЧАТОВ ===
def get_chat_settings(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT settings FROM chat_settings WHERE chat_id = ?", (chat_id,))
    result = cur.fetchone()
    conn.close()
    
    if result:
        settings = json.loads(result[0])
        for key, value in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = value
        return settings
    return dict(DEFAULT_SETTINGS)

def set_chat_settings(chat_id, settings):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO chat_settings (chat_id, settings)
        VALUES (?, ?)
    ''', (chat_id, json.dumps(settings)))
    conn.commit()
    conn.close()

def update_chat_setting(chat_id, key, value):
    settings = get_chat_settings(chat_id)
    settings[key] = value
    set_chat_settings(chat_id, settings)

# === ЧЁРНЫЙ СПИСОК СЛОВ ===
def add_bad_word(chat_id, word):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO bad_words (chat_id, word) VALUES (?, ?)", (chat_id, word.lower()))
    conn.commit()
    conn.close()

def remove_bad_word(chat_id, word):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM bad_words WHERE chat_id = ? AND word = ?", (chat_id, word.lower()))
    conn.commit()
    conn.close()

def get_bad_words(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT word FROM bad_words WHERE chat_id = ?", (chat_id,))
    result = cur.fetchall()
    conn.close()
    return [row[0] for row in result]

def clear_bad_words(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM bad_words WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# === БЕЛЫЙ СПИСОК ССЫЛОК ===
def add_allowed_domain(chat_id, domain):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO allowed_domains (chat_id, domain) VALUES (?, ?)", (chat_id, domain.lower()))
    conn.commit()
    conn.close()

def remove_allowed_domain(chat_id, domain):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM allowed_domains WHERE chat_id = ? AND domain = ?", (chat_id, domain.lower()))
    conn.commit()
    conn.close()

def get_allowed_domains(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT domain FROM allowed_domains WHERE chat_id = ?", (chat_id,))
    result = cur.fetchall()
    conn.close()
    return [row[0] for row in result]

# === ЛОГИ ===
def log_action(action, user_id, target_id, chat_id, details=""):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO logs (action, user_id, target_id, chat_id, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (action, user_id, target_id, chat_id, details))
    conn.commit()
    conn.close()

def get_logs(chat_id=None, limit=50):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if chat_id:
        cur.execute('''
            SELECT action, user_id, target_id, details, timestamp 
            FROM logs 
            WHERE chat_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (chat_id, limit))
    else:
        cur.execute('''
            SELECT action, user_id, target_id, details, timestamp 
            FROM logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
    results = cur.fetchall()
    conn.close()
    return results

# ==================== ИЕРАРХИЯ РОЛЕЙ ====================

ROLE_HIERARCHY = {
    "Разработчик бот менеджера": 0,
    "Владелец проекта": 1,
    "Директор проекта": 2,
    "Заместитель директора проекта": 3,
    "Руководитель проекта": 4,
    "Заместитель руководителя проекта": 5,
    "Специальный администратор": 6,
    "Заместитель специального администратора": 7,
    "Команда проекта": 8,
    "Главный администратор": 9,
    "Основной заместитель главного администратора": 10,
    "Заместитель главного администратора": 11,
    "Куратор администрации": 12,
    "Заместитель куратора администрации": 13,
    "Куратор организации агентов поддержки": 14,
    "Заместитель куратора организации агентов поддержки": 15,
    "Старший администратор": 16,
    "Администратор": 17,
    "Старший модератор": 18,
    "Модератор": 19,
    "Младший модератор": 20,
}

ALL_ROLES = list(ROLE_HIERARCHY.keys())

def get_role_level(role):
    return ROLE_HIERARCHY.get(role, 999)

def get_role_priority(role):
    return get_role_level(role)

def can_manage(target_role, manager_role):
    return get_role_level(manager_role) < get_role_level(target_role)

def get_default_role():
    return "Младший модератор"

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_user_id_from_mention(text):
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

def format_duration(until_date):
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
    if user_id in [OWNER_ID, DEVELOPER_ID]:
        return True
    role = get_role(user_id, chat_id)
    return role is not None

# ==================== МОДЕРАЦИЯ ====================

class Moderation:
    def __init__(self, vk):
        self.vk = vk
        self.user_last_msg = {}
    
    def check_message(self, chat_id, user_id, text):
        settings = get_chat_settings(chat_id)
        violations = []
        
        if settings.get("antimat_enabled", True):
            bad_words = get_bad_words(chat_id) + settings.get("mat_words", [])
            for word in bad_words:
                if word.lower() in text.lower():
                    violations.append(("мат", settings.get("antimat_action", "warn"), word))
                    break
        
        if settings.get("antispam_enabled", True):
            key = f"{chat_id}_{user_id}"
            now = datetime.now()
            if key in self.user_last_msg:
                last_time = self.user_last_msg[key]
                seconds = (now - last_time).total_seconds()
                if seconds < settings.get("antispam_seconds", 3):
                    violations.append(("спам", "warn", f"{int(seconds)}с"))
            self.user_last_msg[key] = now
        
        if settings.get("antilink_enabled", True):
            urls = re.findall(r'https?://[^\s]+', text)
            if urls:
                allowed = get_allowed_domains(chat_id) + settings.get("allowed_domains", [])
                for url in urls:
                    clean_url = re.sub(r'https?://(www\.)?', '', url).split('/')[0].lower()
                    clean_url = clean_url.split(':')[0]
                    is_allowed = False
                    for domain in allowed:
                        if domain.lower() in clean_url or clean_url.endswith(domain.lower()):
                            is_allowed = True
                            break
                    if not is_allowed:
                        violations.append(("ссылка", settings.get("antilink_action", "warn"), clean_url))
                        break
        
        if settings.get("anticaps_enabled", True):
            letters = sum(c.isalpha() for c in text if c.isalpha())
            if letters > 5:
                caps = sum(c.isupper() for c in text if c.isalpha())
                caps_percent = (caps / letters) * 100
                if caps_percent >= settings.get("caps_limit", 70):
                    violations.append(("капс", settings.get("anticaps_action", "warn"), f"{int(caps_percent)}%"))
        
        return violations
    
    def handle_violation(self, chat_id, admin_id, user_id, violation_type, action, detail):
        settings = get_chat_settings(chat_id)
        
        if action == "warn":
            count = add_warn(user_id, chat_id)
            max_warns = settings.get("max_warns", 3)
            
            if count >= max_warns:
                auto_action = settings.get("warn_action", "mute")
                if auto_action == "mute":
                    duration = settings.get("auto_mute_duration", 10)
                    mute_user(user_id, chat_id, duration, admin_id, f"Автомут после {count} предупреждений")
                    self.vk.messages.send(
                        chat_id=chat_id,
                        message=f"⚠️ Пользователь замучен на {duration} минут (автоматически)",
                        random_id=get_random_id()
                    )
                    log_action("auto_mute", admin_id, user_id, chat_id, f"{duration} мин, {violation_type}")
                elif auto_action == "ban":
                    ban_user(user_id, chat_id, f"Автобан после {count} предупреждений", admin_id, -1)
                    self.vk.messages.send(
                        chat_id=chat_id,
                        message=f"🔨 Пользователь забанен (автоматически)",
                        random_id=get_random_id()
                    )
                    log_action("auto_ban", admin_id, user_id, chat_id, f"{violation_type}")
            else:
                self.vk.messages.send(
                    chat_id=chat_id,
                    message=f"⚠️ Предупреждение {count}/{max_warns} за {violation_type}: {detail}",
                    random_id=get_random_id()
                )
                log_action("warn", admin_id, user_id, chat_id, f"{violation_type}: {detail}")
        
        elif action == "mute":
            duration = settings.get("auto_mute_duration", 10)
            mute_user(user_id, chat_id, duration, admin_id, f"{violation_type}: {detail}")
            self.vk.messages.send(
                chat_id=chat_id,
                message=f"🔇 Пользователь замучен на {duration} минут за {violation_type}",
                random_id=get_random_id()
            )
            log_action("mute", admin_id, user_id, chat_id, f"{duration} мин, {violation_type}: {detail}")
        
        elif action == "ban":
            ban_user(user_id, chat_id, f"{violation_type}: {detail}", admin_id, -1)
            self.vk.messages.send(
                chat_id=chat_id,
                message=f"🔨 Пользователь забанен за {violation_type}",
                random_id=get_random_id()
            )
            log_action("ban", admin_id, user_id, chat_id, f"{violation_type}: {detail}")

# ==================== МУТ СИСТЕМА ====================

class MuteSystem:
    def __init__(self, vk):
        self.vk = vk
    
    def mute(self, chat_id, admin_id, user_id, minutes, reason=""):
        mute_user(user_id, chat_id, minutes, admin_id, reason)
        log_action("mute", admin_id, user_id, chat_id, f"{minutes} мин: {reason}")
        user_info = get_user_info(self.vk, user_id)
        user_name = format_user(user_info) if user_info else f"id{user_id}"
        return f"🔇 {user_name} замучен на {minutes} минут: {reason if reason else 'Без причины'}"
    
    def unmute(self, chat_id, admin_id, user_id):
        unmute_user(user_id, chat_id)
        log_action("unmute", admin_id, user_id, chat_id, "")
        user_info = get_user_info(self.vk, user_id)
        user_name = format_user(user_info) if user_info else f"id{user_id}"
        return f"🔊 {user_name} размучен"
    
    def check_mute(self, user_id, chat_id):
        return is_muted(user_id, chat_id)
    
    def get_mute_info(self, user_id, chat_id):
        until = get_mute_time(user_id, chat_id)
        if until:
            remaining = int((until - datetime.now()).total_seconds() / 60)
            return f"⏱ Осталось {remaining} минут"
        return "Не в муте"
    
    def get_mute_list(self, chat_id):
        mutes = get_all_mutes(chat_id)
        if not mutes:
            return "📋 В муте никого нет"
        text = "📋 **Список замученных:**\n"
        for user_id, until_date, muted_by, reason in mutes[:20]:
            user_info = get_user_info(self.vk, user_id)
            user_name = format_user(user_info) if user_info else f"id{user_id}"
            remaining = (datetime.fromisoformat(until_date) - datetime.now())
            minutes = int(remaining.total_seconds() / 60)
            text += f"• {user_name} - {minutes} мин ({reason or 'Без причины'})\n"
        return text

# ==================== ПРИВЕТСТВИЯ ====================

class WelcomeSystem:
    def __init__(self, vk):
        self.vk = vk
    
    def send_welcome(self, chat_id, user_id):
        settings = get_chat_settings(chat_id)
        if not settings.get("welcome_enabled", True):
            return
        
        try:
            user = self.vk.users.get(user_ids=user_id, fields="first_name,last_name")[0]
        except:
            user = {"first_name": "", "last_name": ""}
        
        name = f"[id{user_id}|{user.get('first_name', '')} {user.get('last_name', '')}]"
        
        message = settings.get("welcome_message", "👋 Добро пожаловать, {user}!")
        message = message.replace("{user}", name)
        message = message.replace("{user_id}", str(user_id))
        message = message.replace("{first_name}", user.get('first_name', ''))
        message = message.replace("{last_name}", user.get('last_name', ''))
        
        self.vk.messages.send(
            chat_id=chat_id,
            message=message,
            random_id=get_random_id()
        )
    
    def send_farewell(self, chat_id, user_id):
        settings = get_chat_settings(chat_id)
        if not settings.get("farewell_enabled", True):
            return
        
        try:
            user = self.vk.users.get(user_ids=user_id, fields="first_name,last_name")[0]
            name = f"[id{user_id}|{user.get('first_name', '')} {user.get('last_name', '')}]"
        except:
            name = f"id{user_id}"
        
        message = settings.get("farewell_message", "👋 {user} покинул нас. Будем скучать!")
        message = message.replace("{user}", name)
        message = message.replace("{user_id}", str(user_id))
        
        self.vk.messages.send(
            chat_id=chat_id,
            message=message,
            random_id=get_random_id()
        )

# ==================== КАСТОМНЫЕ РОЛИ ====================

class CustomRoles:
    def __init__(self, vk):
        self.vk = vk
    
    def add_role(self, chat_id, admin_id, role_name, priority, permissions=None):
        if admin_id not in [OWNER_ID, DEVELOPER_ID]:
            return "❌ Только владелец/разработчик может создавать роли"
        
        if get_custom_role(chat_id, role_name):
            return f"❌ Роль '{role_name}' уже существует"
        
        existing = get_all_custom_roles(chat_id)
        for name, prio in existing:
            if prio == priority:
                return f"❌ Приоритет {priority} уже занят ролью '{name}'"
        
        add_custom_role(chat_id, role_name, priority, admin_id, permissions or {})
        log_action("add_role", admin_id, 0, chat_id, f"{role_name} (приоритет {priority})")
        
        return f"✅ Роль '{role_name}' создана с приоритетом {priority}"
    
    def remove_role(self, chat_id, admin_id, role_name):
        if admin_id not in [OWNER_ID, DEVELOPER_ID]:
            return "❌ Только владелец/разработчик может удалять роли"
        
        if not get_custom_role(chat_id, role_name):
            return f"❌ Роль '{role_name}' не найдена"
        
        remove_custom_role(chat_id, role_name)
        log_action("remove_role", admin_id, 0, chat_id, role_name)
        
        return f"✅ Роль '{role_name}' удалена"
    
    def list_roles(self, chat_id):
        custom = get_all_custom_roles(chat_id)
        default_roles = ALL_ROLES
        
        text = "📋 **Доступные роли:**\n\n"
        text += "🔹 **Стандартные роли:**\n"
        for role in default_roles[:10]:
            text += f"• {role}\n"
        text += "...\n\n"
        
        if custom:
            text += "🔸 **Кастомные роли:**\n"
            for name, priority in custom:
                text += f"• {name} (приоритет: {priority})\n"
        else:
            text += "🔸 Кастомные роли отсутствуют\n"
        
        return text
    
    def set_user_role(self, chat_id, admin_id, user_id, role_name):
        role_data = get_custom_role(chat_id, role_name)
        if not role_data:
            return f"❌ Роль '{role_name}' не найдена"
        
        admin_role = get_role(admin_id, chat_id)
        role_priority = role_data[2]
        
        if admin_role:
            admin_priority = get_role_priority(admin_role)
            if admin_priority >= role_priority:
                return "❌ Вы не можете назначить роль выше вашей"
        
        set_role(user_id, chat_id, role_name, admin_id)
        log_action("set_custom_role", admin_id, user_id, chat_id, role_name)
        
        user_info = get_user_info(self.vk, user_id)
        user_name = format_user(user_info) if user_info else f"id{user_id}"
        
        return f"✅ {user_name} назначена роль '{role_name}'"

# ==================== НАСТРОЙКИ ====================

class SettingsManager:
    def __init__(self, vk):
        self.vk = vk
    
    def show_settings(self, chat_id, admin_id):
        settings = get_chat_settings(chat_id)
        
        text = "⚙️ **Настройки чата:**\n\n"
        text += f"🔹 Приветствия: {'✅' if settings.get('welcome_enabled') else '❌'}\n"
        text += f"🔹 Прощания: {'✅' if settings.get('farewell_enabled') else '❌'}\n"
        text += f"🔹 Антиспам: {'✅' if settings.get('antispam_enabled') else '❌'} ({settings.get('antispam_seconds')}с)\n"
        text += f"🔹 Антимат: {'✅' if settings.get('antimat_enabled') else '❌'}\n"
        text += f"🔹 Антиссылки: {'✅' if settings.get('antilink_enabled') else '❌'}\n"
        text += f"🔹 Антикапс: {'✅' if settings.get('anticaps_enabled') else '❌'} ({settings.get('caps_limit')}%)\n"
        text += f"🔹 Макс. предупреждений: {settings.get('max_warns')}\n"
        text += f"🔹 Действие при предупреждениях: {settings.get('warn_action')}\n"
        text += f"🔹 Длительность мута: {settings.get('auto_mute_duration')} мин\n"
        
        return text
    
    def set_setting(self, chat_id, admin_id, key, value):
        settings = get_chat_settings(chat_id)
        
        if key not in settings:
            return f"❌ Настройка '{key}' не найдена"
        
        if isinstance(settings[key], bool):
            value = value.lower() in ['true', 'yes', '1', 'on', '✅', 'вкл', 'включить']
        elif isinstance(settings[key], int):
            try:
                value = int(value)
            except:
                return f"❌ Значение должно быть числом"
        
        settings[key] = value
        set_chat_settings(chat_id, settings)
        log_action("change_setting", admin_id, 0, chat_id, f"{key}={value}")
        
        return f"✅ Настройка '{key}' изменена на {value}"
    
    def reset_settings(self, chat_id, admin_id):
        set_chat_settings(chat_id, dict(DEFAULT_SETTINGS))
        log_action("reset_settings", admin_id, 0, chat_id, "")
        return "✅ Настройки сброшены к стандартным"

# ==================== АДМИН КОМАНДЫ ====================

class AdminCommands:
    def __init__(self, vk):
        self.vk = vk
    
    def check_permission(self, user_id, chat_id, required_role=None):
        if user_id in [OWNER_ID, DEVELOPER_ID]:
            return True
        user_role = get_role(user_id, chat_id)
        if not user_role:
            return False
        if required_role:
            return can_manage(required_role, user_role)
        return True
    
    def get_user_info_command(self, chat_id, target_id):
        user = get_user_info(self.vk, target_id)
        if not user:
            return "❌ Пользователь не найден"
        
        ban_info = get_ban_info(target_id)
        ban_status = "✅ Не в бане"
        if ban_info:
            until = ban_info[3]
            if until == "forever":
                ban_status = "🔨 В бане (навсегда)"
            elif until and datetime.now() < datetime.fromisoformat(until):
                ban_status = f"🔨 В бане до {until[:10]}"
        
        role = get_role(target_id, chat_id) or "Нет роли"
        nickname = get_nickname(target_id, chat_id) or "Не установлен"
        warns = get_warns(target_id, chat_id)
        
        info = f"""
📋 **Информация о пользователе:**
ID: {target_id}
Имя: {user.get('first_name', '')} {user.get('last_name', '')}
Пол: {"👨 Мужской" if user.get('sex') == 2 else "👩 Женский" if user.get('sex') == 1 else "❓ Не указан"}
Город: {user.get('city', {}).get('title', 'Не указан')}
Онлайн: {"🟢 В сети" if user.get('online') else "⚫ Не в сети"}

🎭 Роль: {role}
🏷️ Ник: {nickname}
⚠️ Предупреждений: {warns}
🔒 Статус бана: {ban_status}
        """
        return info
    
    def kick(self, chat_id, admin_id, target_id, reason=""):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        target_role = get_role(target_id, chat_id) or "Младший модератор"
        admin_role = get_role(admin_id, chat_id) or "Младший модератор"
        
        if not can_manage(target_role, admin_role):
            return "❌ Вы не можете кикнуть этого пользователя"
        
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id, member_id=admin_id)
            log_action("kick", admin_id, target_id, chat_id, reason)
            user_info = get_user_info(self.vk, target_id)
            user_name = format_user(user_info) if user_info else f"id{target_id}"
            return f"👢 {user_name} кикнут: {reason if reason else 'Без причины'}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def gkick(self, chat_id, admin_id, target_id, reason=""):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        linked = get_linked_chats()
        success = 0
        for cid in linked:
            try:
                self.vk.messages.removeChatUser(chat_id=cid, user_id=target_id, member_id=admin_id)
                success += 1
            except:
                pass
        
        log_action("gkick", admin_id, target_id, chat_id, reason)
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        return f"🌍 {user_name} кикнут из {success} бесед: {reason if reason else 'Без причины'}"
    
    def ban(self, chat_id, admin_id, target_id, duration=0, reason=""):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        target_role = get_role(target_id, chat_id) or "Младший модератор"
        admin_role = get_role(admin_id, chat_id) or "Младший модератор"
        
        if not can_manage(target_role, admin_role):
            return "❌ Вы не можете забанить этого пользователя"
        
        ban_user(target_id, chat_id, reason, admin_id, duration, is_global=False)
        
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id, member_id=admin_id)
        except:
            pass
        
        duration_str = "навсегда" if duration == -1 else f"{duration} дней" if duration > 0 else "навсегда"
        log_action("ban", admin_id, target_id, chat_id, f"{duration_str}: {reason}")
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        return f"🔨 {user_name} забанен ({duration_str}): {reason if reason else 'Без причины'}"
    
    def gban(self, chat_id, admin_id, target_id, duration=0, reason=""):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        target_role = get_role(target_id, chat_id) or "Младший модератор"
        admin_role = get_role(admin_id, chat_id) or "Младший модератор"
        
        if not can_manage(target_role, admin_role):
            return "❌ Вы не можете забанить этого пользователя"
        
        linked = get_linked_chats()
        success = 0
        
        for cid in linked:
            ban_user(target_id, cid, reason, admin_id, duration, is_global=True)
            try:
                self.vk.messages.removeChatUser(chat_id=cid, user_id=target_id, member_id=admin_id)
                success += 1
            except:
                pass
        
        duration_str = "навсегда" if duration == -1 else f"{duration} дней" if duration > 0 else "навсегда"
        log_action("gban", admin_id, target_id, chat_id, f"{duration_str}: {reason} (в {success} чатах)")
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        return f"🌍 {user_name} забанен глобально ({duration_str}) в {success} беседах: {reason if reason else 'Без причины'}"
    
    def unban(self, chat_id, admin_id, target_id, reason=""):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if not is_banned(target_id, chat_id):
            return f"❌ Пользователь не в бане"
        
        unban_user(target_id, chat_id)
        log_action("unban", admin_id, target_id, chat_id, reason)
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        return f"✅ {user_name} разбанен. Причина: {reason if reason else 'По просьбе администрации'}"
    
    def get_banlist(self, chat_id, admin_id, page=1, filter_type="all"):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if filter_type == "active":
            bans = get_active_bans(chat_id)
        elif filter_type == "expired":
            bans = get_expired_bans(chat_id) if 'get_expired_bans' in globals() else []
        elif filter_type == "global":
            bans = [b for b in get_all_bans(chat_id) if b[5] == 1]
        elif filter_type == "forever":
            bans = [b for b in get_all_bans(chat_id) if b[3] == "forever"]
        else:
            bans = get_all_bans(chat_id)
        
        if not bans:
            return "📋 В списке банов пусто"
        
        items_per_page = 10
        total_pages = (len(bans) + items_per_page - 1) // items_per_page
        
        if page > total_pages:
            page = total_pages
        if page < 1:
            page = 1
        
        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_bans = bans[start:end]
        
        stats = get_ban_stats()
        text = f"📋 **Список банов** (страница {page}/{total_pages})\n"
        text += f"📊 Всего: {stats['total']} | Активных: {stats['active']} | Глобальных: {stats['global']} | Навсегда: {stats['forever']}\n"
        text += "─" * 30 + "\n"
        
        for ban in page_bans:
            user_id = ban[0]
            reason = ban[1] or "Без причины"
            banned_by = ban[2]
            until_date = ban[3]
            timestamp = ban[4]
            is_global = ban[5]
            
            user_info = get_user_info(self.vk, user_id)
            user_name = format_user(user_info) if user_info else f"id{user_id}"
            
            admin_info = get_user_info(self.vk, banned_by)
            admin_name = format_user(admin_info) if admin_info else f"id{banned_by}"
            
            ban_date = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
            duration = format_duration(until_date)
            global_tag = " 🌍" if is_global else ""
            
            text += f"""
👤 {user_name}{global_tag}
📌 Причина: {reason}
👮 Забанил: {admin_name}
📅 Дата: {ban_date}
⏳ Срок: {duration}
─" * 30 + "\n"
        
        text += f"\n📌 Используйте /baninfo @user для подробной информации"
        text += f"\n📌 Фильтры: /banlist [страница] [all/active/expired/global/forever]"
        
        return text
    
    def get_baninfo(self, chat_id, admin_id, target_id):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if not is_banned(target_id, chat_id):
            return f"✅ Пользователь не в бане"
        
        history = get_ban_history(target_id)
        if not history:
            return f"✅ Пользователь не в бане"
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        
        current_ban = history[0]
        chat_id_ban = current_ban[0]
        reason = current_ban[1] or "Без причины"
        banned_by = current_ban[2]
        until_date = current_ban[3]
        timestamp = current_ban[4]
        is_global = current_ban[5]
        
        admin_info = get_user_info(self.vk, banned_by)
        admin_name = format_user(admin_info) if admin_info else f"id{banned_by}"
        
        ban_date = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        duration = format_duration(until_date)
        remaining_text = get_remaining_time(until_date)
        
        history_text = "\n📜 **История банов:**\n"
        for i, ban in enumerate(history[:5], 1):
            h_chat = ban[0]
            h_reason = ban[1] or "Без причины"
            h_date = datetime.fromisoformat(ban[4]).strftime("%d.%m.%Y %H:%M")
            h_until = "Навсегда" if ban[3] == "forever" else ban[3][:10]
            h_global = "🌍 " if ban[5] else ""
            history_text += f"{i}. {h_global}Чат {h_chat}: {h_reason} ({h_date}) → до {h_until}\n"
        
        total_bans = len(history)
        
        text = f"""
📋 **Информация о бане пользователя**

👤 {user_name} (ID: {target_id})
{'🌍 Глобальный бан' if is_global else '🔒 Локальный бан'}

📌 Причина: {reason}
👮 Забанил: {admin_name}
📅 Дата бана: {ban_date}
⏳ Срок: {duration}
{remaining_text}

📊 Всего банов: {total_bans}
{history_text}
"""
        return text
    
    def get_mybans(self, chat_id, user_id):
        history = get_ban_history(user_id)
        if not history:
            return "✅ Вы не в бане"
        
        text = "📋 **Ваши баны:**\n"
        for ban in history[:10]:
            h_chat = ban[0]
            h_reason = ban[1] or "Без причины"
            h_date = datetime.fromisoformat(ban[4]).strftime("%d.%m.%Y %H:%M")
            h_until = "Навсегда" if ban[3] == "forever" else ban[3][:10]
            h_global = "🌍 " if ban[5] else ""
            text += f"{h_global}Чат {h_chat}: {h_reason} ({h_date}) → до {h_until}\n"
        
        return text
    
    def search_banlist(self, chat_id, admin_id, query):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        results = search_bans(query, chat_id)
        if not results:
            return f"🔍 По запросу '{query}' ничего не найдено"
        
        text = f"🔍 **Результаты поиска** (найдено: {len(results)}):\n"
        text += "─" * 30 + "\n"
        
        for ban in results[:20]:
            user_id = ban[0]
            reason = ban[1] or "Без причины"
            until_date = ban[3]
            is_global = ban[5]
            
            user_info = get_user_info(self.vk, user_id)
            user_name = format_user(user_info) if user_info else f"id{user_id}"
            
            duration = "Навсегда" if until_date == "forever" else until_date[:10]
            global_tag = " 🌍" if is_global else ""
            
            text += f"• {user_name}{global_tag}: {reason} → {duration}\n"
        
        return text
    
    def get_banstats(self, chat_id, admin_id):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        stats = get_ban_stats()
        
        text = f"""
📊 **Статистика банов:**
• Всего банов: {stats['total']}
• Активных: {stats['active']}
• Глобальных: {stats['global']}
• Навсегда: {stats['forever']}
        """
        return text
    
    def set_nick(self, chat_id, admin_id, target_id, nickname):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        set_nickname(target_id, chat_id, nickname)
        log_action("setnick", admin_id, target_id, chat_id, nickname)
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        
        return f"✅ {user_name} установлен ник: {nickname}"
    
    def gset_nick(self, admin_id, target_id, nickname):
        if admin_id != OWNER_ID and admin_id != DEVELOPER_ID:
            return "❌ Только владелец/разработчик может устанавливать глобальный ник"
        
        linked = get_linked_chats()
        for cid in linked:
            set_nickname(target_id, cid, nickname)
        
        log_action("gsetnick", admin_id, target_id, 0, nickname)
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🌍 {user_name} установлен глобальный ник: {nickname}"
    
    def set_role(self, chat_id, admin_id, target_id, role):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if role not in ALL_ROLES:
            return f"❌ Роль '{role}' не найдена.\nДоступные роли:\n" + "\n".join(ALL_ROLES[:15])
        
        admin_role = get_role(admin_id, chat_id) or "Младший модератор"
        if not can_manage(role, admin_role):
            return "❌ Вы не можете назначить роль выше вашей"
        
        set_role(target_id, chat_id, role, admin_id)
        log_action("setrole", admin_id, target_id, chat_id, role)
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        
        return f"✅ {user_name} назначена роль: {role}"
    
    def gset_role(self, admin_id, target_id, role):
        if admin_id != OWNER_ID and admin_id != DEVELOPER_ID:
            return "❌ Только владелец/разработчик может назначать глобальные роли"
        
        if role not in ALL_ROLES:
            return f"❌ Роль '{role}' не найдена"
        
        linked = get_linked_chats()
        for cid in linked:
            set_role(target_id, cid, role, admin_id)
        
        log_action("gsetrole", admin_id, target_id, 0, role)
        
        user_info = get_user_info(self.vk, target_id)
        user_name = format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🌍 {user_name} назначена глобальная роль: {role}"
    
    def link(self, chat_id, admin_id, target_chat_id):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        linked = get_linked_chats()
        if chat_id not in linked:
            linked.append(chat_id)
        if target_chat_id not in linked:
            linked.append(target_chat_id)
        
        link_chats(linked)
        log_action("link", admin_id, 0, chat_id, f"Связано с {target_chat_id}")
        
        return f"🔗 Беседы {chat_id} и {target_chat_id} связаны"
    
    def createlink(self, admin_id, chat_ids_str):
        if admin_id != OWNER_ID and admin_id != DEVELOPER_ID:
            return "❌ Только владелец/разработчик может создавать связки"
        
        chat_ids = [int(x.strip()) for x in chat_ids_str.split(',')]
        link_chats(chat_ids)
        log_action("createlink", admin_id, 0, 0, f"Создана связка: {chat_ids}")
        
        return f"✅ Создана новая связка бесед: {chat_ids}"
    
    def unlink(self, chat_id, admin_id):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        unlink_chat(chat_id)
        log_action("unlink", admin_id, 0, chat_id, "")
        
        return f"✅ Беседа {chat_id} отвязана"
    
    def clear_chat(self, chat_id, admin_id, count=100):
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        try:
            history = self.vk.messages.getHistory(chat_id=chat_id, count=min(count, 100))
            deleted = 0
            for msg in history['items']:
                try:
                    self.vk.messages.delete(
                        message_id=msg['id'],
                        peer_id=2000000000 + chat_id,
                        delete_for_all=1
                    )
                    deleted += 1
                except:
                    pass
            
            log_action("clear", admin_id, 0, chat_id, f"{deleted} сообщений")
            return f"🧹 Удалено {deleted} сообщений"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

print("[BOT] Инициализация...")
init_db()
print("[BOT] Готов к работе!")