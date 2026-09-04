import re
import utils
import database as db
from datetime import datetime

class Moderation:
    def __init__(self, vk):
        self.vk = vk
        self.user_last_msg = {}
    
    def check_message(self, chat_id, user_id, text):
        """Проверяет сообщение на нарушения"""
        settings = db.get_chat_settings(chat_id)
        violations = []
        
        # 1. Проверка на мат
        if settings.get("antimat_enabled", True):
            bad_words = db.get_bad_words(chat_id) + settings.get("mat_words", [])
            for word in bad_words:
                if word.lower() in text.lower():
                    violations.append(("мат", settings.get("antimat_action", "warn"), word))
                    break
        
        # 2. Проверка на спам (повтор сообщений)
        if settings.get("antispam_enabled", True):
            key = f"{chat_id}_{user_id}"
            now = datetime.now()
            if key in self.user_last_msg:
                last_time = self.user_last_msg[key]
                seconds = (now - last_time).total_seconds()
                if seconds < settings.get("antispam_seconds", 3):
                    violations.append(("спам", "warn", f"{int(seconds)}с"))
            self.user_last_msg[key] = now
        
        # 3. Проверка на ссылки
        if settings.get("antilink_enabled", True):
            urls = re.findall(r'https?://[^\s]+', text)
            if urls:
                allowed = db.get_allowed_domains(chat_id) + settings.get("allowed_domains", [])
                for url in urls:
                    # Очищаем URL от параметров
                    clean_url = re.sub(r'https?://(www\.)?', '', url).split('/')[0].lower()
                    # Убираем порты
                    clean_url = clean_url.split(':')[0]
                    
                    # Проверяем, разрешён ли домен
                    is_allowed = False
                    for domain in allowed:
                        if domain.lower() in clean_url or clean_url.endswith(domain.lower()):
                            is_allowed = True
                            break
                    
                    if not is_allowed:
                        violations.append(("ссылка", settings.get("antilink_action", "warn"), clean_url))
                        break
        
        # 4. Проверка на капс
        if settings.get("anticaps_enabled", True):
            letters = sum(c.isalpha() for c in text if c.isalpha())
            if letters > 5:  # Минимум 5 букв для проверки
                caps = sum(c.isupper() for c in text if c.isalpha())
                caps_percent = (caps / letters) * 100
                if caps_percent >= settings.get("caps_limit", 70):
                    violations.append(("капс", settings.get("anticaps_action", "warn"), f"{int(caps_percent)}%"))
        
        return violations
    
    def handle_violation(self, chat_id, admin_id, user_id, violation_type, action, detail):
        """Обрабатывает нарушение"""
        settings = db.get_chat_settings(chat_id)
        
        if action == "warn":
            count = db.add_warn(user_id, chat_id)
            max_warns = settings.get("max_warns", 3)
            
            if count >= max_warns:
                auto_action = settings.get("warn_action", "mute")
                if auto_action == "mute":
                    duration = settings.get("auto_mute_duration", 10)
                    db.mute_user(user_id, chat_id, duration, admin_id, f"Автомут после {count} предупреждений")
                    self.vk.messages.send(
                        chat_id=chat_id,
                        message=f"⚠️ Пользователь замучен на {duration} минут (автоматически)",
                        random_id=0
                    )
                    db.log_action("auto_mute", admin_id, user_id, chat_id, f"{duration} мин, {violation_type}")
                elif auto_action == "ban":
                    db.ban_user(user_id, chat_id, f"Автобан после {count} предупреждений", admin_id, -1)
                    self.vk.messages.send(
                        chat_id=chat_id,
                        message=f"🔨 Пользователь забанен (автоматически)",
                        random_id=0
                    )
                    db.log_action("auto_ban", admin_id, user_id, chat_id, f"{violation_type}")
            else:
                self.vk.messages.send(
                    chat_id=chat_id,
                    message=f"⚠️ Предупреждение {count}/{max_warns} за {violation_type}: {detail}",
                    random_id=0
                )
                db.log_action("warn", admin_id, user_id, chat_id, f"{violation_type}: {detail}")
        
        elif action == "mute":
            duration = settings.get("auto_mute_duration", 10)
            db.mute_user(user_id, chat_id, duration, admin_id, f"{violation_type}: {detail}")
            self.vk.messages.send(
                chat_id=chat_id,
                message=f"🔇 Пользователь замучен на {duration} минут за {violation_type}",
                random_id=0
            )
            db.log_action("mute", admin_id, user_id, chat_id, f"{duration} мин, {violation_type}: {detail}")
        
        elif action == "ban":
            db.ban_user(user_id, chat_id, f"{violation_type}: {detail}", admin_id, -1)
            self.vk.messages.send(
                chat_id=chat_id,
                message=f"🔨 Пользователь забанен за {violation_type}",
                random_id=0
            )
            db.log_action("ban", admin_id, user_id, chat_id, f"{violation_type}: {detail}")
    
    def clear_user_messages(self, chat_id, user_id, count=10):
        """Удаляет сообщения пользователя"""
        try:
            history = self.vk.messages.getHistory(chat_id=chat_id, count=count)
            deleted = 0
            for msg in history['items']:
                if msg['from_id'] == user_id:
                    try:
                        self.vk.messages.delete(
                            message_id=msg['id'],
                            peer_id=2000000000 + chat_id,
                            delete_for_all=1
                        )
                        deleted += 1
                    except:
                        pass
            return deleted
        except:
            return 0