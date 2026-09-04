import database as db
from datetime import datetime

class MuteSystem:
    def __init__(self, vk):
        self.vk = vk
    
    def mute(self, chat_id, admin_id, user_id, minutes, reason=""):
        """Замутить пользователя"""
        db.mute_user(user_id, chat_id, minutes, admin_id, reason)
        db.log_action("mute", admin_id, user_id, chat_id, f"{minutes} мин: {reason}")
        
        user_info = utils.get_user_info(self.vk, user_id)
        user_name = utils.format_user(user_info) if user_info else f"id{user_id}"
        
        return f"🔇 {user_name} замучен на {minutes} минут: {reason if reason else 'Без причины'}"
    
    def unmute(self, chat_id, admin_id, user_id):
        """Размутить пользователя"""
        db.unmute_user(user_id, chat_id)
        db.log_action("unmute", admin_id, user_id, chat_id, "")
        
        user_info = utils.get_user_info(self.vk, user_id)
        user_name = utils.format_user(user_info) if user_info else f"id{user_id}"
        
        return f"🔊 {user_name} размучен"
    
    def check_mute(self, user_id, chat_id):
        """Проверяет, не в муте ли пользователь"""
        return db.is_muted(user_id, chat_id)
    
    def get_mute_info(self, user_id, chat_id):
        """Получает информацию о муте"""
        until = db.get_mute_time(user_id, chat_id)
        if until:
            remaining = int((until - datetime.now()).total_seconds() / 60)
            return f"⏱ Осталось {remaining} минут"
        return "Не в муте"
    
    def get_mute_list(self, chat_id):
        """Получает список замученных пользователей"""
        mutes = db.get_all_mutes(chat_id)
        if not mutes:
            return "📋 В муте никого нет"
        
        text = "📋 **Список замученных:**\n"
        for user_id, until_date, muted_by, reason in mutes[:20]:
            user_info = utils.get_user_info(self.vk, user_id)
            user_name = utils.format_user(user_info) if user_info else f"id{user_id}"
            
            remaining = (datetime.fromisoformat(until_date) - datetime.now())
            minutes = int(remaining.total_seconds() / 60)
            
            text += f"• {user_name} - {minutes} мин ({reason or 'Без причины'})\n"
        
        return text