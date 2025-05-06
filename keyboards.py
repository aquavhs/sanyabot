from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Создает основную клавиатуру
    
    Args:
        is_admin (bool): Является ли пользователь администратором
    """
    keyboard = []
    if is_admin:
        keyboard = [
            [InlineKeyboardButton(text="📱 Подписки", callback_data="subscribe")],
            [InlineKeyboardButton(text="👨‍💼 Админ-панель", callback_data="admin_panel")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="📱 Подписки", callback_data="subscribe")]
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура выбора подписки
def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с тарифами подписок"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔹 День - 90₽", callback_data="sub_basic")],
            [InlineKeyboardButton(text="🔹 Неделя - 440₽", callback_data="sub_standard")],
            [InlineKeyboardButton(text="🔹 Месяц - 1620₽", callback_data="sub_premium")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
        ]
    )

# Клавиатура оплаты
def get_payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для оплаты"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
        ]
    )

def get_admin_keyboard(is_test_mode: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для админ-панели
    
    Args:
        is_test_mode (bool): Текущий режим работы (тестовый/реальный)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Переключить в тестовый режим" if not is_test_mode else "🔄 Переключить в реальный режим",
                callback_data="admin_test_mode"
            )],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="💰 Баланс", callback_data="admin_balance")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
            [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="back_to_main")]
        ]
    ) 