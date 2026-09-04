import sqlite3
import json
from datetime import datetime, timedelta

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

def get_expired_bans(chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    if chat_id:
        cur.execute('''
            SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
            FROM bans 
            WHERE (chat_id = ? OR is_global = 1) 
            AND until_date != "forever" AND until_date <= ?
            ORDER BY timestamp DESC
        ''', (chat_id, now))
    else:
        cur.execute('''
            SELECT user_id, reason, banned_by, until_date, timestamp, is_global 
            FROM bans 
            WHERE until_date != "forever" AND until_date <= ?
            ORDER BY timestamp DESC
        ''', (now,))
    
    results = cur.fetchall()
    conn.close()
    return results

def get_bans_by_admin(admin_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT user_id, chat_id, reason, until_date, timestamp, is_global 
        FROM bans 
        WHERE banned_by = ?
        ORDER BY timestamp DESC
    ''', (admin_id,))
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

def get_all_nicknames(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, nickname FROM nicknames WHERE chat_id = ?", (chat_id,))
    results = cur.fetchall()
    conn.close()
    return results

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

def clear_links():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_links")
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
        from config import DEFAULT_SETTINGS
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

def clear_allowed_domains(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM allowed_domains WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

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

init_db()