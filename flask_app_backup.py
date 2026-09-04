from flask import Flask, request, jsonify
import vk_api
from vk_api.utils import get_random_id
import os
import json
import time
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# === НАСТРОЙКИ ИЗ .env ===
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
CONFIRMATION_TOKEN = os.getenv("CONFIRMATION_TOKEN", "")

# Проверка наличия токена
if not VK_TOKEN:
    print("❌ ОШИБКА: VK_TOKEN не найден в .env!")
    exit(1)

print(f"✅ Бот запускается с GROUP_ID={GROUP_ID}")
print(f"✅ OWNER_ID={OWNER_ID}, DEVELOPER_ID={DEVELOPER_ID}")

app = Flask(__name__)

# === ИМПОРТ ВСЕЙ ЛОГИКИ ИЗ bot.py ===
# ВАЖНО: bot.py должен лежать рядом с этим файлом

try:
    import bot
    print("✅ bot.py успешно импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта bot.py: {e}")
    print("❌ Убедитесь, что файл bot.py загружен на сервер!")
    exit(1)

# Инициализация VK API
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

# Инициализация систем бота
admin_cmd = bot.AdminCommands(vk)
moderation = bot.Moderation(vk)
mute_system = bot.MuteSystem(vk)
welcome = bot.WelcomeSystem(vk)
custom_roles = bot.CustomRoles(vk)
settings_mgr = bot.SettingsManager(vk)

# ============================================
# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
# ============================================

def is_admin(user_id, chat_id):
    """Проверка прав администратора"""
    if user_id in [OWNER_ID, DEVELOPER_ID]:
        return True
    role = bot.get_role(user_id, chat_id)
    return role is not None

# ============================================
# === ОСНОВНАЯ ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ===
# ============================================

def handle_message(user_id, chat_id, text, event_id=None):
    """Обработчик сообщений — вся логика бота"""
    
    # === ПРОВЕРКА НА БАН ===
    if bot.is_banned(user_id, chat_id):
        try:
            vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id, member_id=user_id)
        except:
            pass
        return None
    
    # === ПРОВЕРКА НА МУТ ===
    if mute_system.check_mute(user_id, chat_id):
        try:
            if event_id:
                vk.messages.delete(
                    message_id=event_id,
                    peer_id=2000000000 + chat_id,
                    delete_for_all=1
                )
            mute_info = mute_system.get_mute_info(user_id, chat_id)
            vk.messages.send(
                chat_id=chat_id,
                message=f"🔇 Вы в муте. {mute_info}",
                random_id=get_random_id()
            )
        except:
            pass
        return None
    
    # === АВТОМОДЕРАЦИЯ ===
    if not text.startswith("/"):
        violations = moderation.check_message(chat_id, user_id, text)
        if violations:
            for v_type, action, detail in violations:
                moderation.handle_violation(chat_id, user_id, user_id, v_type, action, detail)
                try:
                    if event_id:
                        vk.messages.delete(
                            message_id=event_id,
                            peer_id=2000000000 + chat_id,
                            delete_for_all=1
                        )
                except:
                    pass
            return None
    
    # === ОБРАБОТКА КОМАНД ===
    if not text.startswith("/"):
        return None
    
    parts = text.split()
    cmd = parts[0][1:].lower()
    
    # Список админ-команд
    admin_commands = [
        "kick", "gkick", "ban", "gban", "unban", 
        "mute", "unmute", "muteinfo", "mutelist",
        "setrole", "gsetrole", "setnick", "gsetnick",
        "banlist", "baninfo", "searchban", "banstats", "mybans",
        "clear", "link", "unlink", "createlink",
        "set", "resetsettings",
        "addword", "removeword", "listwords", "clearwords",
        "adddomain", "removedomain", "listdomains",
        "addrole", "removerole", "listroles", "setuserrole"
    ]
    
    # Проверка прав для админ-команд
    if cmd in admin_commands and not is_admin(user_id, chat_id):
        vk.messages.send(
            chat_id=chat_id, 
            message="❌ Недостаточно прав", 
            random_id=get_random_id()
        )
        return None
    
    try:
        # ==========================================
        # === ВСЕ КОМАНДЫ БОТА ===
        # ==========================================
        
        # ---- ИНФОРМАЦИЯ ----
        
        # /id @user
        if cmd == "id" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                vk.messages.send(
                    chat_id=chat_id, 
                    message=f"🆔 ID: {target_id}", 
                    random_id=get_random_id()
                )
        
        # /get @user
        elif cmd == "get" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                result = admin_cmd.get_user_info_command(chat_id, target_id)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # ---- КИК ----
        
        # /kick @user [причина]
        elif cmd == "kick" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                reason = " ".join(parts[2:]) if len(parts) > 2 else ""
                result = admin_cmd.kick(chat_id, user_id, target_id, reason)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /gkick @user [причина]
        elif cmd == "gkick" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                reason = " ".join(parts[2:]) if len(parts) > 2 else ""
                result = admin_cmd.gkick(chat_id, user_id, target_id, reason)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # ---- БАН ----
        
        # /ban @user [срок] [причина]
        elif cmd == "ban" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                duration = 0
                reason_start = 2
                if len(parts) > 2:
                    duration = bot.parse_duration(parts[2])
                    if duration is not None:
                        reason_start = 3
                reason = " ".join(parts[reason_start:]) if len(parts) > reason_start else ""
                result = admin_cmd.ban(chat_id, user_id, target_id, duration, reason)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /gban @user [срок] [причина]
        elif cmd == "gban" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                duration = 0
                reason_start = 2
                if len(parts) > 2:
                    duration = bot.parse_duration(parts[2])
                    if duration is not None:
                        reason_start = 3
                reason = " ".join(parts[reason_start:]) if len(parts) > reason_start else ""
                result = admin_cmd.gban(chat_id, user_id, target_id, duration, reason)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /unban @user [причина]
        elif cmd == "unban" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                reason = " ".join(parts[2:]) if len(parts) > 2 else ""
                result = admin_cmd.unban(chat_id, user_id, target_id, reason)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /banlist [страница] [фильтр]
        elif cmd == "banlist":
            page = 1
            filter_type = "all"
            if len(parts) > 1:
                if parts[1].isdigit():
                    page = int(parts[1])
                    if len(parts) > 2:
                        filter_type = parts[2]
                else:
                    filter_type = parts[1]
            result = admin_cmd.get_banlist(chat_id, user_id, page, filter_type)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /baninfo @user
        elif cmd == "baninfo" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                result = admin_cmd.get_baninfo(chat_id, user_id, target_id)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /mybans
        elif cmd == "mybans":
            result = admin_cmd.get_mybans(chat_id, user_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /searchban [запрос]
        elif cmd == "searchban" and len(parts) >= 2:
            query = " ".join(parts[1:])
            result = admin_cmd.search_banlist(chat_id, user_id, query)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /banstats
        elif cmd == "banstats":
            result = admin_cmd.get_banstats(chat_id, user_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # ---- МУТ ----
        
        # /mute @user [минуты] [причина]
        elif cmd == "mute" and len(parts) >= 3:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                minutes = int(parts[2])
                reason = " ".join(parts[3:]) if len(parts) > 3 else ""
                result = mute_system.mute(chat_id, user_id, target_id, minutes, reason)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /unmute @user
        elif cmd == "unmute" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                result = mute_system.unmute(chat_id, user_id, target_id)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /muteinfo @user
        elif cmd == "muteinfo" and len(parts) >= 2:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                result = mute_system.get_mute_info(target_id, chat_id)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /mutelist
        elif cmd == "mutelist":
            result = mute_system.get_mute_list(chat_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # ---- НИКИ ----
        
        # /setnick @user [ник]
        elif cmd == "setnick" and len(parts) >= 3:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                nickname = " ".join(parts[2:])
                result = admin_cmd.set_nick(chat_id, user_id, target_id, nickname)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /gsetnick @user [ник]
        elif cmd == "gsetnick" and len(parts) >= 3:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                nickname = " ".join(parts[2:])
                result = admin_cmd.gset_nick(user_id, target_id, nickname)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # ---- РОЛИ ----
        
        # /setrole @user [роль]
        elif cmd == "setrole" and len(parts) >= 3:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                role = " ".join(parts[2:])
                result = admin_cmd.set_role(chat_id, user_id, target_id, role)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # /gsetrole @user [роль]
        elif cmd == "gsetrole" and len(parts) >= 3:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                role = " ".join(parts[2:])
                result = admin_cmd.gset_role(user_id, target_id, role)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # ---- КАСТОМНЫЕ РОЛИ ----
        
        # /addrole [приоритет] [название]
        elif cmd == "addrole" and len(parts) >= 3:
            priority = int(parts[1])
            role_name = " ".join(parts[2:])
            result = custom_roles.add_role(chat_id, user_id, role_name, priority)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /removerole [название]
        elif cmd == "removerole" and len(parts) >= 2:
            role_name = " ".join(parts[1:])
            result = custom_roles.remove_role(chat_id, user_id, role_name)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /listroles
        elif cmd == "listroles":
            result = custom_roles.list_roles(chat_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /setuserrole @user [роль]
        elif cmd == "setuserrole" and len(parts) >= 3:
            target_id = bot.get_user_id_from_mention(parts[1])
            if target_id:
                role = " ".join(parts[2:])
                result = custom_roles.set_user_role(chat_id, user_id, target_id, role)
                vk.messages.send(
                    chat_id=chat_id, 
                    message=result, 
                    random_id=get_random_id()
                )
        
        # ---- СВЯЗКА БЕСЕД ----
        
        # /link [номер]
        elif cmd == "link" and len(parts) >= 2:
            target_chat = int(parts[1])
            result = admin_cmd.link(chat_id, user_id, target_chat)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /createlink [номера через запятую]
        elif cmd == "createlink" and len(parts) >= 2:
            result = admin_cmd.createlink(user_id, parts[1])
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /unlink
        elif cmd == "unlink":
            result = admin_cmd.unlink(chat_id, user_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # ---- ОЧИСТКА ----
        
        # /clear [количество]
        elif cmd == "clear":
            count = int(parts[1]) if len(parts) > 1 else 100
            result = admin_cmd.clear_chat(chat_id, user_id, count)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # ---- НАСТРОЙКИ ----
        
        # /settings
        elif cmd == "settings":
            result = settings_mgr.show_settings(chat_id, user_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /set [ключ] [значение]
        elif cmd == "set" and len(parts) >= 3:
            key = parts[1]
            value = " ".join(parts[2:])
            result = settings_mgr.set_setting(chat_id, user_id, key, value)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # /resetsettings
        elif cmd == "resetsettings":
            result = settings_mgr.reset_settings(chat_id, user_id)
            vk.messages.send(
                chat_id=chat_id, 
                message=result, 
                random_id=get_random_id()
            )
        
        # ---- УПРАВЛЕНИЕ СЛОВАМИ ----
        
        # /addword [слово]
        elif cmd == "addword" and len(parts) >= 2:
            word = " ".join(parts[1:])
            bot.add_bad_word(chat_id, word)
            vk.messages.send(
                chat_id=chat_id, 
                message=f"✅ Слово '{word}' добавлено в чёрный список", 
                random_id=get_random_id()
            )
        
        # /removeword [слово]
        elif cmd == "removeword" and len(parts) >= 2:
            word = " ".join(parts[1:])
            bot.remove_bad_word(chat_id, word)
            vk.messages.send(
                chat_id=chat_id, 
                message=f"✅ Слово '{word}' удалено из чёрного списка", 
                random_id=get_random_id()
            )
        
        # /listwords
        elif cmd == "listwords":
            words = bot.get_bad_words(chat_id)
            if words:
                vk.messages.send(
                    chat_id=chat_id, 
                    message=f"📋 Чёрный список: {', '.join(words)}", 
                    random_id=get_random_id()
                )
            else:
                vk.messages.send(
                    chat_id=chat_id, 
                    message="📋 Чёрный список пуст", 
                    random_id=get_random_id()
                )
        
        # /clearwords
        elif cmd == "clearwords":
            bot.clear_bad_words(chat_id)
            vk.messages.send(
                chat_id=chat_id, 
                message="✅ Чёрный список очищен", 
                random_id=get_random_id()
            )
        
        # ---- УПРАВЛЕНИЕ ДОМЕНАМИ ----
        
        # /adddomain [домен]
        elif cmd == "adddomain" and len(parts) >= 2:
            domain = parts[1].lower()
            bot.add_allowed_domain(chat_id, domain)
            vk.messages.send(
                chat_id=chat_id, 
                message=f"✅ Домен '{domain}' добавлен в белый список", 
                random_id=get_random_id()
            )
        
        # /removedomain [домен]
        elif cmd == "removedomain" and len(parts) >= 2:
            domain = parts[1].lower()
            bot.remove_allowed_domain(chat_id, domain)
            vk.messages.send(
                chat_id=chat_id, 
                message=f"✅ Домен '{domain}' удалён из белого списка", 
                random_id=get_random_id()
            )
        
        # /listdomains
        elif cmd == "listdomains":
            domains = bot.get_allowed_domains(chat_id)
            if domains:
                vk.messages.send(
                    chat_id=chat_id, 
                    message=f"📋 Белый список доменов: {', '.join(domains)}", 
                    random_id=get_random_id()
                )
            else:
                vk.messages.send(
                    chat_id=chat_id, 
                    message="📋 Белый список доменов пуст", 
                    random_id=get_random_id()
                )
        
        # ---- ПРИВЕТСТВИЯ ----
        
        # /testwelcome
        elif cmd == "testwelcome":
            welcome.send_welcome(chat_id, user_id)
        
        # /testfarewell
        elif cmd == "testfarewell":
            welcome.send_farewell(chat_id, user_id)
        
        # ---- СПРАВКА ----
        
        # /help
        elif cmd == "help":
            help_text = """
📋 **КОМАНДЫ БОТА-МЕНЕДЖЕРА**

👤 **Информация:**
/id @user - ID пользователя
/get @user - Полная информация

👢 **Кик:**
/kick @user [причина] - Кикнуть
/gkick @user [причина] - Глобальный кик

🔨 **Бан:**
/ban @user [срок] [причина] - Забанить
/gban @user [срок] [причина] - Глобальный бан
/unban @user [причина] - Разбанить
/banlist [стр] [фильтр] - Список банов
/baninfo @user - Информация о бане
/mybans - Мои баны
/searchban [запрос] - Поиск банов
/banstats - Статистика банов

🔇 **Мут:**
/mute @user [минуты] [причина] - Замутить
/unmute @user - Размутить
/muteinfo @user - Информация о муте
/mutelist - Список замученных

🏷️ **Ники:**
/setnick @user [ник] - Установить ник
/gsetnick @user [ник] - Глобальный ник

🎭 **Роли:**
/setrole @user [роль] - Назначить роль
/gsetrole @user [роль] - Глобальная роль
/addrole [приоритет] [название] - Создать роль
/removerole [название] - Удалить роль
/listroles - Список ролей
/setuserrole @user [роль] - Кастомная роль

🔗 **Связка:**
/link [номер] - Связать беседы
/createlink [номера] - Создать связку
/unlink - Отвязать беседу

⚙️ **Настройки:**
/settings - Показать настройки
/set [ключ] [значение] - Изменить настройку
/resetsettings - Сброс настроек

🚫 **Автомодерация:**
/addword [слово] - Добавить слово
/removeword [слово] - Удалить слово
/listwords - Чёрный список
/clearwords - Очистить список
/adddomain [домен] - Добавить домен
/removedomain [домен] - Удалить домен
/listdomains - Белый список

📢 **Приветствия:**
/testwelcome - Тест приветствия
/testfarewell - Тест прощания

🧹 **Очистка:**
/clear [количество] - Очистить чат

❓ /help - Эта справка
            """
            vk.messages.send(
                chat_id=chat_id, 
                message=help_text, 
                random_id=get_random_id()
            )
        
        # ---- НЕИЗВЕСТНАЯ КОМАНДА ----
        else:
            if text.startswith("/"):
                vk.messages.send(
                    chat_id=chat_id, 
                    message="❌ Неизвестная команда. Используйте /help.",
                    random_id=get_random_id()
                )
    
    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        print(f"[ERROR] {error_msg}")
        try:
            vk.messages.send(
                chat_id=chat_id, 
                message=error_msg, 
                random_id=get_random_id()
            )
        except:
            pass
    
    return None

# ============================================
# === WEBHOOK (ОБРАБОТЧИК ЗАПРОСОВ ОТ VK) ===
# ============================================

@app.route('/', methods=['POST'])
def webhook():
    """Главный обработчик запросов от VK"""
    try:
        data = request.get_json()
        print(f"[DEBUG] Получен запрос: {json.dumps(data, indent=2)[:500]}")
        
        # === ПОДТВЕРЖДЕНИЕ СЕРВЕРА ===
        if data.get('type') == 'confirmation':
            print(f"[INFO] Отправляем confirmation_token: {CONFIRMATION_TOKEN}")
            return CONFIRMATION_TOKEN
        
        # === НОВОЕ СООБЩЕНИЕ ===
        if data.get('type') == 'message_new':
            msg = data['object']['message']
            user_id = msg.get('from_id')
            chat_id = msg.get('peer_id')
            text = msg.get('text', '')
            event_id = msg.get('id')
            
            # Игнорируем сообщения от самого бота
            if user_id == -GROUP_ID:
                return 'ok'
            
            print(f"[INFO] Новое сообщение от {user_id} в чат {chat_id}: {text[:50]}")
            handle_message(user_id, chat_id, text, event_id)
        
        return 'ok'
    
    except Exception as e:
        print(f"[ERROR] В webhook: {str(e)}")
        return 'ok', 200

# ============================================
# === HEALTH CHECK (ДЛЯ UPTIMEROBOT) ===
# ============================================

@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности бота"""
    return jsonify({
        "status": "ok", 
        "time": time.time(),
        "group_id": GROUP_ID
    })

# ============================================
# === ЗАПУСК (ДЛЯ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ) ===
# ============================================

if __name__ == '__main__':
    print("🚀 Запуск бота (локальный режим)...")
    app.run(host='0.0.0.0', port=5000, debug=True)
