import database as db
import roles
from config import OWNER_ID, DEVELOPER_ID

class CustomRoles:
    def __init__(self, vk):
        self.vk = vk
    
    def add_role(self, chat_id, admin_id, role_name, priority, permissions=None):
        """Создаёт новую кастомную роль"""
        if admin_id not in [OWNER_ID, DEVELOPER_ID]:
            return "❌ Только владелец/разработчик может создавать роли"
        
        if db.get_custom_role(chat_id, role_name):
            return f"❌ Роль '{role_name}' уже существует"
        
        existing = db.get_all_custom_roles(chat_id)
        for name, prio in existing:
            if prio == priority:
                return f"❌ Приоритет {priority} уже занят ролью '{name}'"
        
        db.add_custom_role(chat_id, role_name, priority, admin_id, permissions or {})
        db.log_action("add_role", admin_id, 0, chat_id, f"{role_name} (приоритет {priority})")
        
        return f"✅ Роль '{role_name}' создана с приоритетом {priority}"
    
    def remove_role(self, chat_id, admin_id, role_name):
        """Удаляет кастомную роль"""
        if admin_id not in [OWNER_ID, DEVELOPER_ID]:
            return "❌ Только владелец/разработчик может удалять роли"
        
        if not db.get_custom_role(chat_id, role_name):
            return f"❌ Роль '{role_name}' не найдена"
        
        db.remove_custom_role(chat_id, role_name)
        db.log_action("remove_role", admin_id, 0, chat_id, role_name)
        
        return f"✅ Роль '{role_name}' удалена"
    
    def list_roles(self, chat_id):
        """Показывает все роли в чате"""
        custom = db.get_all_custom_roles(chat_id)
        default_roles = roles.ALL_ROLES
        
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
        """Назначает кастомную роль пользователю"""
        role_data = db.get_custom_role(chat_id, role_name)
        if not role_data:
            return f"❌ Роль '{role_name}' не найдена"
        
        admin_role = db.get_role(admin_id, chat_id)
        role_priority = role_data[2]
        
        if admin_role:
            admin_priority = roles.get_role_priority(admin_role)
            if admin_priority >= role_priority:
                return "❌ Вы не можете назначить роль выше вашей"
        
        db.set_role(user_id, chat_id, role_name, admin_id)
        db.log_action("set_custom_role", admin_id, user_id, chat_id, role_name)
        
        user_info = utils.get_user_info(self.vk, user_id)
        user_name = utils.format_user(user_info) if user_info else f"id{user_id}"
        
        return f"✅ {user_name} назначена роль '{role_name}'"