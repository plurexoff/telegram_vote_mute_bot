import os
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Добавьте переменную окружения.")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище активных голосований
# Структура: {chat_id: {'votes': {user_id: option}, 'options': [...], 'message_id': int, 'end_time': datetime}}
active_votes = {}

# Настройки голосования
VOTE_DURATION = 300  # 5 минут в секундах


@dp.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для голосования с возможностью мьюта участников.\n\n"
        "📋 Доступные команды:\n"
        "/vote - Начать новое голосование\n"
        "/help - Помощь"
    )


@dp.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "ℹ️ *Инструкция по использованию:*\n\n"
        "1️⃣ Используйте /vote чтобы начать голосование\n"
        "2️⃣ Участники голосуют нажатием на кнопки\n"
        "3️⃣ После окончания времени подводятся итоги\n"
        "4️⃣ Участники, проголосовавшие определённым образом, могут быть замьючены\n\n"
        "⚠️ *Важно:* Бот должен быть администратором группы с правами на ограничение участников!"
    )
    await message.answer(help_text, parse_mode='Markdown')


@dp.message(Command(commands=['vote']))
async def cmd_vote(message: types.Message):
    """Создание нового голосования"""
    chat_id = message.chat.id

    # Проверяем, есть ли активное голосование
    if chat_id in active_votes:
        await message.answer("⚠️ В этом чате уже идёт голосование!")
        return

    # Создаём кнопки для голосования
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 За", callback_data="vote_yes")],
        [InlineKeyboardButton(text="👎 Против", callback_data="vote_no")],
        [InlineKeyboardButton(text="🤷 Воздержался", callback_data="vote_abstain")]
    ])

    vote_text = (
        "📊 *Голосование началось!*\n\n"
        f"⏱ Время: {VOTE_DURATION // 60} минут\n"
        "Выберите один из вариантов ниже:"
    )

    sent_message = await message.answer(vote_text, reply_markup=keyboard, parse_mode='Markdown')

    # Сохраняем информацию о голосовании
    active_votes[chat_id] = {
        'votes': {},
        'options': ['yes', 'no', 'abstain'],
        'message_id': sent_message.message_id,
        'end_time': datetime.now() + timedelta(seconds=VOTE_DURATION)
    }

    # Запускаем таймер для завершения голосования
    asyncio.create_task(end_vote_timer(chat_id))


@dp.callback_query(F.data.startswith('vote_'))
async def process_vote(callback: types.CallbackQuery):
    """Обработка голосов"""
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    if chat_id not in active_votes:
        await callback.answer("❌ Голосование не активно", show_alert=True)
        return

    # Определяем вариант голоса
    vote_option = callback.data.replace('vote_', '')

    # Сохраняем голос
    active_votes[chat_id]['votes'][user_id] = vote_option

    await callback.answer(f"✅ Ваш голос учтён!")


async def end_vote_timer(chat_id: int):
    """Таймер для автоматического завершения голосования"""
    await asyncio.sleep(VOTE_DURATION)

    if chat_id in active_votes:
        await finalize_vote(chat_id)


async def finalize_vote(chat_id: int):
    """Подведение итогов голосования"""
    if chat_id not in active_votes:
        return

    vote_data = active_votes.pop(chat_id)
    votes = vote_data['votes']

    # Подсчёт голосов
    yes_votes = sum(1 for v in votes.values() if v == 'yes')
    no_votes = sum(1 for v in votes.values() if v == 'no')
    abstain_votes = sum(1 for v in votes.values() if v == 'abstain')

    result_text = (
        "📊 *Голосование завершено!*\n\n"
        f"👍 За: {yes_votes}\n"
        f"👎 Против: {no_votes}\n"
        f"🤷 Воздержались: {abstain_votes}\n"
        f"\n👥 Всего проголосовало: {len(votes)}"
    )

    # Мьютим пользователей, проголосовавших "Против" (пример логики)
    muted_users = []
    for user_id, vote in votes.items():
        if vote == 'no':  # Мьютим тех, кто проголосовал "Против"
            try:
                # Мьютим пользователя на 5 минут
                until_date = datetime.now() + timedelta(minutes=5)
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=types.ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                muted_users.append(user_id)
            except Exception as e:
                logger.error(f"Не удалось замьютить пользователя {user_id}: {e}")

    if muted_users:
        result_text += f"\n\n🔇 Замьючено пользователей: {len(muted_users)}"

    await bot.send_message(chat_id, result_text, parse_mode='Markdown')


async def main():
    """Запуск бота"""
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
