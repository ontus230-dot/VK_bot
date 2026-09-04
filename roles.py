# Иерархия ролей (чем меньше число, тем выше статус)
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
    """Проверяет, может ли менеджер управлять целью"""
    return get_role_level(manager_role) < get_role_level(target_role)

def get_default_role():
    return "Младший модератор"

def get_higher_roles(role):
    """Возвращает список ролей выше указанной"""
    level = get_role_level(role)
    return [r for r, l in ROLE_HIERARCHY.items() if l < level]

def get_lower_roles(role):
    """Возвращает список ролей ниже указанной"""
    level = get_role_level(role)
    return [r for r, l in ROLE_HIERARCHY.items() if l > level]