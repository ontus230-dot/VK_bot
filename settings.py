import database as db
import json
from config import DEFAULT_SETTINGS

class SettingsManager:
    def __init__(self, vk):
        self.vk = vk
    
    def show_settings(self, chat_id, admin_id):
        """Показывает текущие настройки чата"""
        settings = db.get_chat_settings(chat_id)
        
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
        """Изменяет настройку"""
        settings = db.get_chat_settings(chat_id)
        
        if key not in settings:
            return f"❌ Настройка '{key}' не найдена"
        
        # Преобразуем значение
        if isinstance(settings[key], bool):
            value = value.lower() in ['true', 'yes', '1', 'on', '✅', 'вкл', 'включить']
        elif isinstance(settings[key], int):
            try:
                value = int(value)
            except:
                return f"❌ Значение должно быть числом"
        
        settings[key] = value
        db.set_chat_settings(chat_id, settings)
        db.log_action("change_setting", admin_id, 0, chat_id, f"{key}={value}")
        
        return f"✅ Настройка '{key}' изменена на {value}"
    
    def reset_settings(self, chat_id, admin_id):
        """Сброс настроек к стандартным"""
        db.set_chat_settings(chat_id, dict(DEFAULT_SETTINGS))
        db.log_action("reset_settings", admin_id, 0, chat_id, "")
        return "✅ Настройки сброшены к стандартным"