import asyncio
import logging
import datetime
from aiogram import Bot, types
from aiogram import Dispatcher
from yoomoney import Client, Quickpay
from keyboards import get_payment_keyboard, get_subscription_keyboard
from database import Database
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Словарь с ценами и названиями подписок
SUBSCRIPTION_PRICES = {
    "sub_basic": {
        "amount": 90,
        "name": "Подписка на день",
        "label": "basic_user",
        "duration": datetime.timedelta(days=1)
    },
    "sub_standard": {
        "amount": 440,
        "name": "Подписка на неделю",
        "label": "standard_user",
        "duration": datetime.timedelta(days=7)
    },
    "sub_premium": {
        "amount": 1620,
        "name": "Подписка на месяц",
        "label": "premium_user",
        "duration": datetime.timedelta(days=30)
    }
}

class PaymentHandler:
    def __init__(self, bot: Bot, yoomoney_client: Client, wallet_number: str, db: Database):
        self.bot = bot
        self.yoomoney_client = yoomoney_client
        self.wallet_number = wallet_number
        self.db = db
        self._check_subscriptions_task = None

    async def start_background_tasks(self):
        """Запускает фоновые задачи"""
        self._check_subscriptions_task = asyncio.create_task(self.check_expiring_subscriptions())

    async def stop_background_tasks(self):
        """Останавливает фоновые задачи"""
        if self._check_subscriptions_task:
            self._check_subscriptions_task.cancel()
            try:
                await self._check_subscriptions_task
            except asyncio.CancelledError:
                pass

    async def assign_user_label(self, user_id: int, username: str, subscription_type: str) -> None:
        """
        Присваивает индивидуальный label пользователю после успешной оплаты
        
        Args:
            user_id (int): ID пользователя в Telegram
            username (str): Имя пользователя
            subscription_type (str): Тип подписки (sub_basic, sub_standard, sub_premium)
        """
        try:
            # Получаем информацию о подписке
            sub_info = SUBSCRIPTION_PRICES[subscription_type]
            user_label = sub_info["label"]
            
            # Рассчитываем время начала и окончания подписки
            start_time = datetime.datetime.now()
            end_time = start_time + sub_info["duration"]
            
            # Сохраняем информацию в базу данных
            await self.db.create_user(
                user_id=user_id,
                username=username,
                label=user_label,
                subscription_start=start_time,
                subscription_end=end_time
            )
            
            # Отправляем единое сообщение с информацией о подписке и кнопкой
            await self.bot.send_message(
                chat_id=user_id,
                text=f"🎉 Поздравляем с успешной оплатой!\n\n"
                     f"📅 Подписка активна до: {end_time.strftime('%d.%m.%Y %H:%M')}\n\n"
                     f"Нажмите кнопку ниже, чтобы присоединиться к нашему каналу:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="📢 Присоединиться к каналу",
                            url="https://t.me/+4_Qb6pPctkRkNGMy"
                        )]
                    ]
                )
            )
            
            logging.info(f"Пользователю {user_id} присвоен label: {user_label}")
            
        except Exception as e:
            logging.error(f"Ошибка при присвоении label пользователю {user_id}: {e}")
            await self.bot.send_message(
                chat_id=user_id,
                text="Произошла ошибка при присвоении статуса. Пожалуйста, обратитесь в поддержку."
            )

    async def check_expiring_subscriptions(self):
        """Фоновая задача для проверки окончания подписок"""
        while True:
            try:
                # Получаем всех пользователей с активными подписками
                users = await self.db.get_all_users()
                now = datetime.datetime.now()
                
                for user in users:
                    if user.get("subscription_end"):
                        end_time = datetime.datetime.strptime(
                            user["subscription_end"],
                            "%d.%m.%Y %H:%M:%S"
                        )
                        
                        # Если до окончания подписки остался час
                        if (end_time - now).total_seconds() <= 3600:
                            await self.bot.send_message(
                                chat_id=user["user_id"],
                                text="⚠️ Внимание! Ваша подписка истекает через час.\n"
                                     "Чтобы продлить подписку, нажмите кнопку ниже:",
                                reply_markup=get_subscription_keyboard()
                            )
                
                # Проверяем каждые 5 минут
                await asyncio.sleep(300)
                
            except Exception as e:
                logging.error(f"Ошибка при проверке окончания подписок: {e}")
                await asyncio.sleep(60)  # При ошибке ждем минуту перед следующей попыткой

    async def process_subscription_choice(self, callback_query: types.CallbackQuery, test_mode: bool = False):
        """Обработчик выбора подписки"""
        try:
            # Получаем информацию о выбранной подписке
            subscription_type = callback_query.data
            selected_sub = SUBSCRIPTION_PRICES.get(subscription_type)
            
            if not selected_sub:
                await callback_query.answer("❌ Неверный тип подписки", show_alert=True)
                return
            
            # Пытаемся удалить сообщение с выбором подписки
            try:
                await callback_query.message.delete()
            except Exception as e:
                logging.warning(f"Не удалось удалить сообщение: {e}")

            # Проверяем наличие активной подписки
            user = await self.db.get_user(callback_query.from_user.id)
            if user and user.get("subscription_end"):
                end_time = datetime.datetime.strptime(
                    user["subscription_end"],
                    "%d.%m.%Y %H:%M:%S"
                )
                if end_time > datetime.datetime.now():
                    # Если подписка активна, предлагаем продлить
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="✅ Продлить",
                                    callback_data=f"extend_{subscription_type}"
                                ),
                                InlineKeyboardButton(
                                    text="❌ Отмена",
                                    callback_data="cancel_extend"
                                )
                            ]
                        ]
                    )
                    await callback_query.message.answer(
                        f"У вас уже есть активная подписка до: {end_time.strftime('%d.%m.%Y %H:%M')}\n"
                        "Хотите продлить?",
                        reply_markup=keyboard
                    )
                    return
            
            if test_mode:
                # Тестовый режим - симулируем успешную оплату
                await callback_query.message.answer(
                    f"🧪 Тестовый режим\n"
                    f"Выбрана подписка: {selected_sub['name']}\n"
                    f"Сумма: {selected_sub['amount']}₽\n\n"
                    f"✅ Оплата успешно симулирована!"
                )
                
                # Рассчитываем время начала и окончания подписки
                start_time = datetime.datetime.now()
                end_time = start_time + selected_sub["duration"]
                
                # Обновляем статус пользователя в базе данных
                await self.db.create_user(
                    user_id=callback_query.from_user.id,
                    username=callback_query.from_user.username or "Unknown",
                    label=selected_sub['label'],
                    subscription_start=start_time,
                    subscription_end=end_time
                )
                
                # Отправляем сообщение о присвоении статуса
                await callback_query.message.answer(
                    f"✅ Вам присвоен статус: {selected_sub['label']}\n"
                    f"Подписка активна до: {end_time.strftime('%d.%m.%Y %H:%M')}"
                )
                
                # Отправляем кнопку для присоединения к каналу
                await callback_query.message.answer(
                    "🎉 Поздравляем с успешной оплатой!\n"
                    "Нажмите кнопку ниже, чтобы присоединиться к нашему каналу:",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text="📢 Присоединиться к каналу",
                                url="https://t.me/+9dOYr5Z3XMk3YjQy"
                            )]
                        ]
                    )
                )
                return
            
            # Реальный режим - создаем форму для оплаты через ЮMoney
            quickpay = Quickpay(
                receiver=self.wallet_number,
                quickpay_form="shop",
                targets=f"Оплата {selected_sub['name']}",
                paymentType="AC",
                sum=selected_sub['amount'],
                label=f"{callback_query.from_user.id}_{callback_query.data}"
            )
            
            # Отправляем сообщение с информацией об оплате
            await callback_query.message.answer(
                f"💳 Для оплаты {selected_sub['name']} на сумму {selected_sub['amount']}₽, "
                "нажмите кнопку 'Оплатить' ниже.\n\n"
                "⏳ После оплаты бот автоматически проверит статус платежа.\n"
                "Время ожидания: 10 минут",
                reply_markup=get_payment_keyboard(quickpay.redirected_url)
            )
            
            # Запускаем автоматическую проверку оплаты
            asyncio.create_task(self.check_payment(
                label=f"{callback_query.from_user.id}_{callback_query.data}",
                chat_id=callback_query.message.chat.id
            ))
            
        except Exception as e:
            logging.error(f"Ошибка при создании формы оплаты: {e}")
            await callback_query.message.answer("Произошла ошибка при создании формы оплаты. Попробуйте позже.")

    async def process_extend_subscription(self, callback_query: types.CallbackQuery):
        """Обработчик продления подписки"""
        try:
            subscription_type = callback_query.data.replace("extend_", "")
            selected_sub = SUBSCRIPTION_PRICES.get(subscription_type)
            
            if not selected_sub:
                await callback_query.answer("❌ Неверный тип подписки", show_alert=True)
                return

            # Создаем форму для оплаты через ЮMoney
            quickpay = Quickpay(
                receiver=self.wallet_number,
                quickpay_form="shop",
                targets=f"Продление {selected_sub['name']}",
                paymentType="AC",
                sum=selected_sub['amount'],
                label=f"{callback_query.from_user.id}_extend_{subscription_type}"
            )
            
            # Отправляем сообщение с информацией об оплате
            await callback_query.message.edit_text(
                f"💳 Для продления {selected_sub['name']} на сумму {selected_sub['amount']}₽, "
                "нажмите кнопку 'Оплатить' ниже.\n\n"
                "⏳ После оплаты бот автоматически проверит статус платежа.\n"
                "Время ожидания: 10 минут",
                reply_markup=get_payment_keyboard(quickpay.redirected_url)
            )
            
            # Запускаем автоматическую проверку оплаты
            asyncio.create_task(self.check_payment(
                label=f"{callback_query.from_user.id}_extend_{subscription_type}",
                chat_id=callback_query.message.chat.id,
                is_extension=True
            ))

        except Exception as e:
            logging.error(f"Ошибка при создании формы продления: {e}")
            await callback_query.message.answer("Произошла ошибка при создании формы продления. Попробуйте позже.")

    async def process_cancel_extend(self, callback_query: types.CallbackQuery):
        """Обработчик отмены продления подписки"""
        await callback_query.message.edit_text("❌ Продление подписки отменено.")

    async def check_payment(self, label: str, chat_id: int, is_extension: bool = False) -> bool:
        """Функция для проверки статуса платежа"""
        try:
            # Максимальное время ожидания - 10 минут
            max_attempts = 30  # 30 попыток по 20 секунд
            attempts = 0
            
            while attempts < max_attempts:
                # Получаем историю операций за последние 10 минут
                history = self.yoomoney_client.operation_history(
                    label=label,
                    from_date=datetime.datetime.now() - datetime.timedelta(minutes=10)
                )
                
                # Проверяем каждую операцию
                for operation in history.operations:
                    if operation.status == "success" and operation.label == label:
                        # Получаем user_id и тип подписки из label
                        label_parts = label.split("_")
                        if len(label_parts) >= 2:
                            user_id = int(label_parts[0])
                            subscription_type = "_".join(label_parts[1:])  # Объединяем оставшиеся части
                            
                            # Получаем информацию о пользователе
                            user = await self.db.get_user(user_id)
                            username = user["username"] if user else "Unknown"
                            
                            if is_extension:
                                # Если это продление, обновляем дату окончания подписки
                                current_end = datetime.datetime.strptime(
                                    user["subscription_end"],
                                    "%d.%m.%Y %H:%M:%S"
                                )
                                new_end = current_end + SUBSCRIPTION_PRICES[subscription_type]["duration"]
                                
                                await self.db.update_user_subscription(
                                    user_id=user_id,
                                    subscription_end=new_end
                                )
                                
                                await self.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"✅ Подписка успешно продлена!\n"
                                         f"Новая дата окончания: {new_end.strftime('%d.%m.%Y %H:%M')}"
                                )
                            else:
                                # Присваиваем label пользователю
                                await self.assign_user_label(user_id, username, subscription_type)
                            return True
                
                # Увеличиваем счетчик попыток
                attempts += 1
                
                # Ждем 20 секунд перед следующей проверкой
                await asyncio.sleep(20)
                
            # Если оплата не поступила за 10 минут
            await self.bot.send_message(
                chat_id=chat_id,
                text="❌ Время ожидания оплаты истекло. Пожалуйста, попробуйте оплатить снова."
            )
            return False
            
        except Exception as e:
            logging.error(f"Ошибка при проверке платежа: {e}")
            await self.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при проверке оплаты. Попробуйте позже."
            )
            return False

    async def process_check_payment(self, callback_query: types.CallbackQuery):
        """Обработчик кнопки 'Я оплатил'"""
        try:
            # Получаем label из callback_data
            label = callback_query.data.replace("check_payment_", "")
            
            # Проверяем статус платежа
            history = self.yoomoney_client.operation_history(
                label=label,
                from_date=datetime.datetime.now() - datetime.timedelta(minutes=30)
            )
            
            # Проверяем каждую операцию
            for operation in history.operations:
                if operation.status == "success" and operation.label == label:
                    # Если найдена успешная операция, отправляем сообщение
                    await callback_query.message.edit_text(
                        "✅ Оплата успешно получена! Ваша подписка активирована.",
                        reply_markup=None
                    )
                    return
            
            # Если оплата не найдена
            await callback_query.answer(
                "❌ Оплата пока не поступила. Если вы уже оплатили, подождите немного и попробуйте снова.",
                show_alert=True
            )
                
        except Exception as e:
            logging.error(f"Ошибка при проверке оплаты: {e}")
            await callback_query.answer(
                "Произошла ошибка при проверке оплаты. Попробуйте позже.",
                show_alert=True
            )

    def register_handlers(self, dp: Dispatcher):
        """Регистрация обработчиков"""
        dp.register_callback_query_handler(
            self.process_subscription_choice,
            lambda c: c.data in SUBSCRIPTION_PRICES.keys()
        )
        dp.register_callback_query_handler(
            self.process_extend_subscription,
            lambda c: c.data.startswith("extend_")
        )
        dp.register_callback_query_handler(
            self.process_cancel_extend,
            lambda c: c.data == "cancel_extend"
        )
        dp.register_callback_query_handler(
            self.process_check_payment,
            lambda c: c.data == "check_payment"
        ) 
