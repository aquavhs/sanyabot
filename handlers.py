import logging
from aiogram import Bot, types
from aiogram.filters import Command
from aiogram.types import Message
from yoomoney import Client

from keyboards import get_main_keyboard, get_subscription_keyboard

class MessageHandler:
    def __init__(self, bot: Bot, yoomoney_client: Client):
        self.bot = bot
        self.yoomoney_client = yoomoney_client

    async def cmd_start(self, message: Message):
        """Обработчик команды /start"""
        await message.answer(
            "Привет! Я бот-эхо. Отправь мне любое сообщение, и я его повторю!",
            reply_markup=get_main_keyboard()
        )

    async def process_subscribe_button(self, callback_query: types.CallbackQuery):
        """Обработчик нажатия кнопки 'Подписки'"""
        # Удаляем сообщение с кнопкой
        await callback_query.message.delete()
        
        # Отправляем сообщение с описанием и кнопками
        await callback_query.message.answer(
            "Выберите подходящий вам тариф подписки:\n\n"
            "🔹 Базовая - доступ к основным функциям\n"
            "🔹 Стандартная - расширенный функционал\n"
            "🔹 Премиум - полный доступ ко всем возможностям",
            reply_markup=get_subscription_keyboard()
        )

    async def cancel_payment(self, callback_query: types.CallbackQuery):
        """Обработчик отмены оплаты"""
        await callback_query.message.delete()
        await callback_query.message.answer("Оплата отменена. Вы можете начать сначала, отправив команду /start")

    async def cmd_balance(self, message: Message):
        """Обработчик команды /balance"""
        try:
            user = self.yoomoney_client.account_info()
            await message.answer(f"Ваш баланс: {user.balance} {user.currency}")
        except Exception as e:
            logging.error(f"Ошибка при получении баланса: {e}")
            await message.answer("Произошла ошибка при получении баланса") 