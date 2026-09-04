from flask import Flask, request, jsonify
import vk_api
from vk_api.utils import get_random_id
import config
import database as db
from admin_commands import AdminCommands
from moderation import Moderation
from mute import MuteSystem
from welcome import WelcomeSystem
from custom_roles import CustomRoles
from settings import SettingsManager
import utils
import roles
import json
import time

app = Flask(__name__)

# Инициализация VK API
vk_session = vk_api.VkApi(token=config.VK_TOKEN)
vk = vk_session.get_api()

# Инициализация систем (как в main.py)
admin_cmd = AdminCommands(vk)
moderation = Moderation(vk)
mute_system = MuteSystem(vk)
welcome = WelcomeSystem(vk)
custom_roles = CustomRoles(vk)
settings_mgr = SettingsManager(vk)

def is_admin(user_id, chat_id):
    """Проверка прав администратора"""
    return user_id in [config.OWNER_ID, config.DEVELOPER_ID] or db.get_role(user_id, chat_id) is not None

def handle_message(user_id, chat_id, text, event_id=None):
    """
    Основная логика обработки сообщений
    Перенесена из main.py (цикл обработки команд)
    """
    # Проверка на бан
    if db.is_banned(user_id, chat_id):
        try:
            vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id, member_id=user_id)
        except:
            pass
        return None
    
    # Проверка на мут
    if mute_system.check_mute(user_id, chat_id):
        try:
            # Удаляем сообщение
            if event_id:
                vk.messages.delete(
                    message_id=event_id,
                    peer_id=2000000000 + chat_id,
                    delete_for_all=1
                )
            # Отправляем уведомление
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
                # Удаляем сообщение с нарушением
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
    
    # Проверка прав для админ-команд
    admin_commands = ["kick", "gkick", "ban", "gban", "unban", "mute", "unmute", 
                     "setrole", "gsetrole", "setnick", "gsetnick", "banlist", 
                     "baninfo", "searchban", "banstats", "clear", "link", "unlink",
                     "set", "resetsettings", "addword", "removeword", "addrole", 
                     "removerole", "setuserrole"]
    
    if cmd in admin_commands and not is_admin(user_id, chat_id):
        vk.messages.send(chat_id=chat_id, message="❌ Недостаточно прав", random_id=get_random_id())
        return None
    
    try:
        # === ВСЕ ВАШИ КОМАНДЫ (КОПИРУЙТЕ ИЗ main.py) ===
        
        # /id @user
        if cmd == "id" and len(parts) >= 2:
            target_id = utils.get_user_id_from_mention(parts[1])
            if target_id:
                vk.messages.send(chat_id=chat_id, message=f"🆔 ID: {target_id}", random_id=get_random_id())
        
        # /get @user
        elif cmd == "get" and len(parts) >= 2:
            target_id = utils.get_user_id_from_mention(parts[1])
            if target_id:
                result = admin_cmd.get_user_info_command(chat_id, target_id)
                vk.messages.send(chat_id=chat_id, message=result, random_id=get_random_id())
        
        # ... И ТАК ДАЛЕЕ - ВСЕ ВАШИ КОМАНДЫ ИЗ main.py ...
        # (полный список команд я не копирую для краткости, но вы переносите всё)
        # От /kick до /help - всё должно быть здесь
        
        # /help
        elif cmd == "help":
            help_text = """
📋 **КОМАНДЫ БОТА-МЕНЕДЖЕРА**

👤 Информация: /id, /get
👢 Кик: /kick, /gkick
🔨 Бан: /ban, /gban, /unban, /banlist, /baninfo, /mybans, /searchban, /banstats
🔇 Мут: /mute, /unmute, /muteinfo, /mutelist
🏷️ Ники: /setnick, /gsetnick
🎭 Роли: /setrole, /gsetrole, /addrole, /removerole, /listroles, /setuserrole
🔗 Связка: /link, /createlink, /unlink
⚙️ Настройки: /settings, /set, /resetsettings
🚫 Автомодерация: /addword, /removeword, /listwords, /clearwords, /adddomain, /removedomain, /listdomains
📢 Приветствия: /testwelcome, /testfarewell
🧹 Очистка: /clear
❓ /help - Справка
            """
            vk.messages.send(chat_id=chat_id, message=help_text, random_id=get_random_id())
        
        # Неизвестная команда
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
        vk.messages.send(chat_id=chat_id, message=error_msg, random_id=get_random_id())
    
    return None

# ==================== WEBHOOK ====================

@app.route('/', methods=['POST'])
def webhook():
    """Главный обработчик запросов от VK"""
    data = request.get_json()
    
    # Логируем входящий запрос (для отладки)
    print(f"[DEBUG] Received: {json.dumps(data, indent=2)}")
    
    # Проверка на подтверждение сервера
    if data.get('type') == 'confirmation':
        # ВАЖНО: верните строку из настроек Callback API вашего сообщества
        # Она выглядит как: "e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t9"
        return config.CONFIRMATION_TOKEN
    
    # Обработка нового сообщения
    if data.get('type') == 'message_new':
        msg = data['object']['message']
        user_id = msg['from_id']
        chat_id = msg.get('peer_id')
        text = msg.get('text', '')
        event_id = msg.get('id')
        
        # Вызываем логику обработки
        handle_message(user_id, chat_id, text, event_id)
    
    # Обязательно возвращаем 'ok' для VK
    return 'ok'

@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности"""
    return jsonify({"status": "ok", "time": time.time()})

# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    # Для локального тестирования
    app.run(host='0.0.0.0', port=5000, debug=True)