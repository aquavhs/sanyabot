import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import os
from yoomoney import Client

from keyboards import get_main_keyboard, get_subscription_keyboard, get_admin_keyboard
from payment_handlers import PaymentHandler
from handlers import MessageHandler
from database import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
env_path = os.path.join(os.path.dirname(__file__), '.env')
logging.info(f"Путь к файлу .env: {env_path}")
logging.info(f"Файл .env существует: {os.path.exists(env_path)}")

# Читаем и выводим содержимое файла .env (без значений)
try:
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
        logging.info("Содержимое файла .env (только имена переменных):")
        for line in env_content.splitlines():
            if line.strip() and not line.strip().startswith('#'):
                var_name = line.split('=')[0].strip()
                logging.info(f"- {var_name}")
except Exception as e:
    logging.error(f"Ошибка при чтении файла .env: {e}")

load_dotenv(env_path)

# Получение токенов из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
YOOMONEY_TOKEN = os.getenv('YOOMONEY_ACCESS_TOKEN')
WALLET_NUMBER = os.getenv('YOOMONEY_RECEIVER')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))  # Список ID администраторов

# Отладочная информация
logging.info(f"BOT_TOKEN найден: {'Да' if BOT_TOKEN else 'Нет'}")
logging.info(f"YOOMONEY_TOKEN найден: {'Да' if YOOMONEY_TOKEN else 'Нет'}")
logging.info(f"WALLET_NUMBER найден: {'Да' if WALLET_NUMBER else 'Нет'}")

# Проверка наличия необходимых токенов
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not YOOMONEY_TOKEN:
    raise ValueError("YOOMONEY_TOKEN не найден в переменных окружения")
if not WALLET_NUMBER:
    raise ValueError("YOOMONEY_RECEIVER не найден в переменных окружения")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация клиента ЮMoney
yoomoney_client = Client(YOOMONEY_TOKEN)  # Убираем параметр token=

# Инициализация базы данных
db = Database()  # Создаст файл bot_database.db в текущей директории

# Словарь для хранения режимов работы для админов
admin_test_modes = {}

# Инициализация обработчиков
message_handler = MessageHandler(bot, yoomoney_client)
payment_handler = PaymentHandler(bot, yoomoney_client, WALLET_NUMBER, db)

# Функция проверки на админа
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Регистрация обработчиков
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    is_user_admin = is_admin(message.from_user.id)
    await message.answer(
        "👋 Добро пожаловать!\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(is_user_admin)
    )

@dp.callback_query(lambda c: c.data == "admin_panel")
async def process_admin_panel(callback_query: types.CallbackQuery):
    """Обработчик входа в админ-панель"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    # Получаем текущий режим для админа
    is_test_mode = admin_test_modes.get(callback_query.from_user.id, False)
    
    await callback_query.message.edit_text(
        "👨‍💼 Панель администратора\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(is_test_mode)
    )

@dp.callback_query(lambda c: c.data == "back_to_main")
async def process_back_to_main(callback_query: types.CallbackQuery):
    """Обработчик возврата в главное меню"""
    is_user_admin = is_admin(callback_query.from_user.id)
    await callback_query.message.edit_text(
        "👋 Главное меню\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(is_user_admin)
    )

@dp.callback_query(lambda c: c.data == "admin_test_mode")
async def process_admin_test_mode(callback_query: types.CallbackQuery):
    """Обработчик переключения тестового режима"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # Переключаем режим для админа
    admin_test_modes[callback_query.from_user.id] = not admin_test_modes.get(callback_query.from_user.id, False)
    current_mode = "тестовый" if admin_test_modes[callback_query.from_user.id] else "реальный"
    
    await callback_query.message.edit_text(
        f"👨‍💼 Панель администратора\n"
        f"Режим работы: {current_mode}\n"
        f"Выберите действие:",
        reply_markup=get_admin_keyboard(admin_test_modes[callback_query.from_user.id])
    )

# Добавляем заглушки для новых функций админ-панели
@dp.callback_query(lambda c: c.data == "admin_stats")
async def process_admin_stats(callback_query: types.CallbackQuery):
    """Обработчик просмотра статистики"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # TODO: Добавить реальную статистику
    await callback_query.answer("📊 Функция статистики в разработке", show_alert=True)

@dp.callback_query(lambda c: c.data == "admin_users")
async def process_admin_users(callback_query: types.CallbackQuery):
    """Обработчик просмотра пользователей"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # TODO: Добавить список пользователей
    await callback_query.answer("👥 Функция просмотра пользователей в разработке", show_alert=True)

@dp.callback_query(lambda c: c.data == "admin_balance")
async def process_admin_balance(callback_query: types.CallbackQuery):
    """Обработчик просмотра баланса"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    try:
        user = yoomoney_client.account_info()
        await callback_query.message.edit_text(
            f"💰 Баланс кошелька: {user.balance} {user.currency}\n\n"
            "👨‍💼 Панель администратора\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard(admin_test_modes.get(callback_query.from_user.id, False))
        )
    except Exception as e:
        logging.error(f"Ошибка при получении баланса: {e}")
        await callback_query.answer("❌ Ошибка при получении баланса", show_alert=True)

@dp.callback_query(lambda c: c.data == "admin_settings")
async def process_admin_settings(callback_query: types.CallbackQuery):
    """Обработчик настроек"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # TODO: Добавить настройки
    await callback_query.answer("⚙️ Функция настроек в разработке", show_alert=True)

@dp.callback_query(lambda c: c.data == "subscribe")
async def process_subscribe_button(callback_query: types.CallbackQuery):
    await message_handler.process_subscribe_button(callback_query)

@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def process_subscription_choice(callback_query: types.CallbackQuery):
    # Проверяем, является ли пользователь админом и включен ли для него тестовый режим
    is_test_mode = is_admin(callback_query.from_user.id) and admin_test_modes.get(callback_query.from_user.id, False)
    await payment_handler.process_subscription_choice(callback_query, test_mode=is_test_mode)

@dp.callback_query(lambda c: c.data.startswith("extend_"))
async def process_extend_subscription(callback_query: types.CallbackQuery):
    """Обработчик продления подписки"""
    await payment_handler.process_extend_subscription(callback_query)

@dp.callback_query(lambda c: c.data == "cancel_extend")
async def process_cancel_extend(callback_query: types.CallbackQuery):
    """Обработчик отмены продления подписки"""
    await payment_handler.process_cancel_extend(callback_query)

@dp.callback_query(lambda c: c.data == "cancel_payment")
async def cancel_payment(callback_query: types.CallbackQuery):
    await message_handler.cancel_payment(callback_query)

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    await message_handler.cmd_balance(message)

# Функция запуска бота
async def main():
    try:
        # Запускаем фоновые задачи
        await payment_handler.start_background_tasks()
        
        # Запускаем бота
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Останавливаем фоновые задачи при завершении работы
        await payment_handler.stop_background_tasks()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main()) 