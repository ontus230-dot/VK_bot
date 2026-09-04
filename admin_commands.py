import vk_api
from vk_api.utils import get_random_id
import config
import database as db
import roles
import utils
from datetime import datetime

class AdminCommands:
    def __init__(self, vk):
        self.vk = vk
    
    def check_permission(self, user_id, chat_id, required_role=None):
        """Проверка прав пользователя"""
        if user_id == config.OWNER_ID or user_id == config.DEVELOPER_ID:
            return True
        
        user_role = db.get_role(user_id, chat_id)
        if not user_role:
            return False
        
        if required_role:
            return roles.can_manage(required_role, user_role)
        return True
    
    # ==================== ИНФОРМАЦИЯ ====================
    
    def get_user_info_command(self, chat_id, target_id):
        """/get @user - Информация о пользователе"""
        user = utils.get_user_info(self.vk, target_id)
        if not user:
            return "❌ Пользователь не найден"
        
        ban_info = db.get_ban_info(target_id)
        ban_status = "✅ Не в бане"
        if ban_info:
            until = ban_info[3]
            if until == "forever":
                ban_status = "🔨 В бане (навсегда)"
            elif until and datetime.now() < datetime.fromisoformat(until):
                ban_status = f"🔨 В бане до {until[:10]}"
        
        role = db.get_role(target_id, chat_id) or "Нет роли"
        nickname = db.get_nickname(target_id, chat_id) or "Не установлен"
        warns = db.get_warns(target_id, chat_id)
        
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
    
    # ==================== КИК ====================
    
    def kick(self, chat_id, admin_id, target_id, reason=""):
        """/kick @user [причина] - Кикнуть пользователя"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        target_role = db.get_role(target_id, chat_id) or "Младший модератор"
        admin_role = db.get_role(admin_id, chat_id) or "Младший модератор"
        
        if not roles.can_manage(target_role, admin_role):
            return "❌ Вы не можете кикнуть этого пользователя"
        
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id, member_id=admin_id)
            db.log_action("kick", admin_id, target_id, chat_id, reason)
            
            user_info = utils.get_user_info(self.vk, target_id)
            user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
            
            return f"👢 {user_name} кикнут: {reason if reason else 'Без причины'}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def gkick(self, chat_id, admin_id, target_id, reason=""):
        """/gkick @user - Глобальный кик из всех связанных бесед"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        linked = db.get_linked_chats()
        success = 0
        for cid in linked:
            try:
                self.vk.messages.removeChatUser(chat_id=cid, user_id=target_id, member_id=admin_id)
                success += 1
            except:
                pass
        
        db.log_action("gkick", admin_id, target_id, chat_id, reason)
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🌍 {user_name} кикнут из {success} бесед: {reason if reason else 'Без причины'}"
    
    # ==================== БАН ====================
    
    def ban(self, chat_id, admin_id, target_id, duration=0, reason=""):
        """/ban @user [срок] [причина] - Забанить"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        target_role = db.get_role(target_id, chat_id) or "Младший модератор"
        admin_role = db.get_role(admin_id, chat_id) or "Младший модератор"
        
        if not roles.can_manage(target_role, admin_role):
            return "❌ Вы не можете забанить этого пользователя"
        
        db.ban_user(target_id, chat_id, reason, admin_id, duration, is_global=False)
        
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id, member_id=admin_id)
        except:
            pass
        
        duration_str = "навсегда" if duration == -1 else f"{duration} дней" if duration > 0 else "навсегда"
        db.log_action("ban", admin_id, target_id, chat_id, f"{duration_str}: {reason}")
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🔨 {user_name} забанен ({duration_str}): {reason if reason else 'Без причины'}"
    
    def gban(self, chat_id, admin_id, target_id, duration=0, reason=""):
        """/gban @user [срок] - Глобальный бан во всех связанных беседах"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        target_role = db.get_role(target_id, chat_id) or "Младший модератор"
        admin_role = db.get_role(admin_id, chat_id) or "Младший модератор"
        
        if not roles.can_manage(target_role, admin_role):
            return "❌ Вы не можете забанить этого пользователя"
        
        linked = db.get_linked_chats()
        success = 0
        
        for cid in linked:
            db.ban_user(target_id, cid, reason, admin_id, duration, is_global=True)
            try:
                self.vk.messages.removeChatUser(chat_id=cid, user_id=target_id, member_id=admin_id)
                success += 1
            except:
                pass
        
        duration_str = "навсегда" if duration == -1 else f"{duration} дней" if duration > 0 else "навсегда"
        db.log_action("gban", admin_id, target_id, chat_id, f"{duration_str}: {reason} (в {success} чатах)")
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🌍 {user_name} забанен глобально ({duration_str}) в {success} беседах: {reason if reason else 'Без причины'}"
    
    def unban(self, chat_id, admin_id, target_id, reason=""):
        """/unban @user [причина] - Разбанить с причиной"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if not db.is_banned(target_id, chat_id):
            return f"❌ Пользователь не в бане"
        
        db.unban_user(target_id, chat_id)
        db.log_action("unban", admin_id, target_id, chat_id, reason)
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"✅ {user_name} разбанен. Причина: {reason if reason else 'По просьбе администрации'}"
    
    # ==================== БАНЛИСТ ====================
    
    def get_banlist(self, chat_id, admin_id, page=1, filter_type="all"):
        """/banlist [страница] [фильтр] - Список банов"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if filter_type == "active":
            bans = db.get_active_bans(chat_id)
        elif filter_type == "expired":
            bans = db.get_expired_bans(chat_id)
        elif filter_type == "global":
            bans = [b for b in db.get_all_bans(chat_id) if b[5] == 1]
        elif filter_type == "forever":
            bans = [b for b in db.get_all_bans(chat_id) if b[3] == "forever"]
        else:
            bans = db.get_all_bans(chat_id)
        
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
        
        stats = db.get_ban_stats()
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
            
            user_info = utils.get_user_info(self.vk, user_id)
            user_name = utils.format_user(user_info) if user_info else f"id{user_id}"
            
            admin_info = utils.get_user_info(self.vk, banned_by)
            admin_name = utils.format_user(admin_info) if admin_info else f"id{banned_by}"
            
            ban_date = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
            duration = utils.format_duration(until_date)
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
        """/baninfo @user - Подробная информация о бане"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if not db.is_banned(target_id, chat_id):
            return f"✅ Пользователь не в бане"
        
        history = db.get_ban_history(target_id)
        if not history:
            return f"✅ Пользователь не в бане"
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        current_ban = history[0]
        chat_id_ban = current_ban[0]
        reason = current_ban[1] or "Без причины"
        banned_by = current_ban[2]
        until_date = current_ban[3]
        timestamp = current_ban[4]
        is_global = current_ban[5]
        
        admin_info = utils.get_user_info(self.vk, banned_by)
        admin_name = utils.format_user(admin_info) if admin_info else f"id{banned_by}"
        
        ban_date = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        duration = utils.format_duration(until_date)
        remaining_text = utils.get_remaining_time(until_date)
        
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
        """/mybans - Мои баны"""
        history = db.get_ban_history(user_id)
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
        """/searchban [запрос] - Поиск банов"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        results = db.search_bans(query, chat_id)
        if not results:
            return f"🔍 По запросу '{query}' ничего не найдено"
        
        text = f"🔍 **Результаты поиска** (найдено: {len(results)}):\n"
        text += "─" * 30 + "\n"
        
        for ban in results[:20]:
            user_id = ban[0]
            reason = ban[1] or "Без причины"
            until_date = ban[3]
            is_global = ban[5]
            
            user_info = utils.get_user_info(self.vk, user_id)
            user_name = utils.format_user(user_info) if user_info else f"id{user_id}"
            
            duration = "Навсегда" if until_date == "forever" else until_date[:10]
            global_tag = " 🌍" if is_global else ""
            
            text += f"• {user_name}{global_tag}: {reason} → {duration}\n"
        
        return text
    
    def get_banstats(self, chat_id, admin_id):
        """/banstats - Статистика банов"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        stats = db.get_ban_stats()
        
        text = f"""
📊 **Статистика банов:**
• Всего банов: {stats['total']}
• Активных: {stats['active']}
• Глобальных: {stats['global']}
• Навсегда: {stats['forever']}
        """
        return text
    
    # ==================== НИКИ ====================
    
    def set_nick(self, chat_id, admin_id, target_id, nickname):
        """/setnick @user [ник] - Установить ник"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        db.set_nickname(target_id, chat_id, nickname)
        db.log_action("setnick", admin_id, target_id, chat_id, nickname)
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"✅ {user_name} установлен ник: {nickname}"
    
    def gset_nick(self, admin_id, target_id, nickname):
        """/gsetnick @user [ник] - Глобальный ник"""
        if admin_id != config.OWNER_ID and admin_id != config.DEVELOPER_ID:
            return "❌ Только владелец/разработчик может устанавливать глобальный ник"
        
        linked = db.get_linked_chats()
        for cid in linked:
            db.set_nickname(target_id, cid, nickname)
        
        db.log_action("gsetnick", admin_id, target_id, 0, nickname)
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🌍 {user_name} установлен глобальный ник: {nickname}"
    
    # ==================== РОЛИ ====================
    
    def set_role(self, chat_id, admin_id, target_id, role):
        """/setrole @user [роль] - Назначить роль"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        if role not in roles.ALL_ROLES:
            return f"❌ Роль '{role}' не найдена.\nДоступные роли:\n" + "\n".join(roles.ALL_ROLES[:15])
        
        admin_role = db.get_role(admin_id, chat_id) or "Младший модератор"
        if not roles.can_manage(role, admin_role):
            return "❌ Вы не можете назначить роль выше вашей"
        
        db.set_role(target_id, chat_id, role, admin_id)
        db.log_action("setrole", admin_id, target_id, chat_id, role)
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"✅ {user_name} назначена роль: {role}"
    
    def gset_role(self, admin_id, target_id, role):
        """/gsetrole @user [роль] - Глобальная роль"""
        if admin_id != config.OWNER_ID and admin_id != config.DEVELOPER_ID:
            return "❌ Только владелец/разработчик может назначать глобальные роли"
        
        if role not in roles.ALL_ROLES:
            return f"❌ Роль '{role}' не найдена"
        
        linked = db.get_linked_chats()
        for cid in linked:
            db.set_role(target_id, cid, role, admin_id)
        
        db.log_action("gsetrole", admin_id, target_id, 0, role)
        
        user_info = utils.get_user_info(self.vk, target_id)
        user_name = utils.format_user(user_info) if user_info else f"id{target_id}"
        
        return f"🌍 {user_name} назначена глобальная роль: {role}"
    
    # ==================== СВЯЗКА БЕСЕД ====================
    
    def link(self, chat_id, admin_id, target_chat_id):
        """/link [номер] - Связать беседы"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        linked = db.get_linked_chats()
        if chat_id not in linked:
            linked.append(chat_id)
        if target_chat_id not in linked:
            linked.append(target_chat_id)
        
        db.link_chats(linked)
        db.log_action("link", admin_id, 0, chat_id, f"Связано с {target_chat_id}")
        
        return f"🔗 Беседы {chat_id} и {target_chat_id} связаны"
    
    def createlink(self, admin_id, chat_ids_str):
        """/createlink [номера через запятую] - Создать связку"""
        if admin_id != config.OWNER_ID and admin_id != config.DEVELOPER_ID:
            return "❌ Только владелец/разработчик может создавать связки"
        
        chat_ids = [int(x.strip()) for x in chat_ids_str.split(',')]
        db.link_chats(chat_ids)
        db.log_action("createlink", admin_id, 0, 0, f"Создана связка: {chat_ids}")
        
        return f"✅ Создана новая связка бесед: {chat_ids}"
    
    def unlink(self, chat_id, admin_id):
        """/unlink - Отвязать беседу"""
        if not self.check_permission(admin_id, chat_id):
            return "❌ Недостаточно прав"
        
        db.unlink_chat(chat_id)
        db.log_action("unlink", admin_id, 0, chat_id, "")
        
        return f"✅ Беседа {chat_id} отвязана"
    
    # ==================== ОЧИСТКА ====================
    
    def clear_chat(self, chat_id, admin_id, count=100):
        """/clear [количество] - Очистить чат"""
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
            
            db.log_action("clear", admin_id, 0, chat_id, f"{deleted} сообщений")
            return f"🧹 Удалено {deleted} сообщений"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"