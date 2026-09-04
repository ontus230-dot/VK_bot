import database as db
from datetime import datetime

class WelcomeSystem:
    def __init__(self, vk):
        self.vk = vk
    
    def send_welcome(self, chat_id, user_id):
        """Отправляет приветствие новому участнику"""
        settings = db.get_chat_settings(chat_id)
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
            random_id=0
        )
    
    def send_farewell(self, chat_id, user_id):
        """Отправляет прощание покидающему участнику"""
        settings = db.get_chat_settings(chat_id)
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
            random_id=0
        )