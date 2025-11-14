import os
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

active_votes = {}
message_tasks = {}

VOTE_DURATION = 300
MUTE_DURATION = 18000
VOTES_NEEDED_MUTE = 3
VOTES_NEEDED_BAN = 3
AUTO_DELETE_TIMEOUT = 300  # Удалять сообщения через 5 минут (можно менять)


async def auto_delete_message(chat_id: int, message_id: int, delay: int):
    """Автоматически удаляет сообщение через delay секунд"""
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Сообщение {message_id} удалено из чата {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")


@dp.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    response = await message.answer(
        "Привет! Я модератор для голосования в вашей группе.\n\n"
        "Доступные команды:\n"
        "/vote_mute - Голосование о мьюте (ответьте на сообщение)\n"
        "/vote_ban - Голосование о бане (ответьте на сообщение)\n"
        "/help - Справка"
    )
    # Запускаем автоудаление этого сообщения
    asyncio.create_task(auto_delete_message(message.chat.id, response.message_id, AUTO_DELETE_TIMEOUT))


@dp.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    help_text = (
        "Справка по командам:\n\n"
        "МЬЮТ (временное ограничение):\n"
        "1. Ответьте на сообщение пользователя\n"
        "2. Напишите /vote_mute\n"
        "3. Участники голосуют (нужно 3 голоса)\n"
        "4. Пользователь замьючивается на 5 минут\n\n"
        "БАН (удаление из группы):\n"
        "1. Ответьте на сообщение пользователя\n"
        "2. Напишите /vote_ban\n"
        "3. Участники голосуют (нужно 5 голосов)\n"
        "4. Пользователь удаляется из группы\n\n"
        f"Параметры:\n"
        f"• Длительность голосования: {VOTE_DURATION // 60} мин\n"
        f"• Голосов для мьюта: {VOTES_NEEDED_MUTE}\n"
        f"• Голосов для бана: {VOTES_NEEDED_BAN}"
    )
    response = await message.answer(help_text)
    # Запускаем автоудаление этого сообщения
    asyncio.create_task(auto_delete_message(message.chat.id, response.message_id, AUTO_DELETE_TIMEOUT))


async def start_vote(message: types.Message, vote_type: str):
    chat_id = message.chat.id
    
    if chat_id in active_votes:
        response = await message.answer("В этом чате уже идёт голосование. Подождите окончания.")
        asyncio.create_task(auto_delete_message(chat_id, response.message_id, 30))
        return
    
    if not message.reply_to_message:
        cmd_name = "/vote_mute" if vote_type == "mute" else "/vote_ban"
        response = await message.answer(f"Используйте reply на сообщение пользователя и напишите {cmd_name}")
        asyncio.create_task(auto_delete_message(chat_id, response.message_id, 30))
        return
    
    target_user = message.reply_to_message.from_user
    target_user_id = target_user.id
    target_user_name = target_user.first_name or f"user_{target_user_id}"
    
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=target_user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            response = await message.answer("Нельзя голосовать против администратора.")
            asyncio.create_task(auto_delete_message(chat_id, response.message_id, 30))
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса: {e}")
    
    if target_user_id == message.from_user.id:
        response = await message.answer("Нельзя голосовать против себя.")
        asyncio.create_task(auto_delete_message(chat_id, response.message_id, 30))
        return
    
    if vote_type == "mute":
        votes_needed = VOTES_NEEDED_MUTE
        type_text = "мьюте"
        title = "Голосование о мьюте"
    else:
        votes_needed = VOTES_NEEDED_BAN
        type_text = "бане"
        title = "Голосование о бане"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За", callback_data=f"vote_yes_{vote_type}_{target_user_id}")],
        [InlineKeyboardButton(text="Против", callback_data=f"vote_no_{vote_type}_{target_user_id}")],
        [InlineKeyboardButton(text="Воздержался", callback_data=f"vote_abstain_{vote_type}_{target_user_id}")]
    ])
    
    vote_text = (
        f"{title}\n\n"
        f"Пользователь: {target_user_name}\n"
        f"Время: {VOTE_DURATION // 60} минут\n"
        f"Нужно голосов: {votes_needed}\n\n"
        "Выберите вариант:"
    )
    
    sent_message = await message.answer(vote_text, reply_markup=keyboard)
    
    # Удалим исходную команду
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить исходное сообщение: {e}")
    
    active_votes[chat_id] = {
        'type': vote_type,
        'target_user_id': target_user_id,
        'target_user_name': target_user_name,
        'votes_yes': 0,
        'votes_no': 0,
        'votes_abstain': 0,
        'voters': set(),
        'message_id': sent_message.message_id,
        'end_time': datetime.now() + timedelta(seconds=VOTE_DURATION),
        'votes_needed': votes_needed
    }
    
    asyncio.create_task(end_vote_timer(chat_id))


@dp.message(Command(commands=['vote_mute']))
async def cmd_vote_mute(message: types.Message):
    await start_vote(message, "mute")


@dp.message(Command(commands=['vote_ban']))
async def cmd_vote_ban(message: types.Message):
    await start_vote(message, "ban")


@dp.callback_query(F.data.startswith('vote_'))
async def process_vote(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    if chat_id not in active_votes:
        await callback.answer("Голосование не активно", show_alert=True)
        return
    
    vote_data = active_votes[chat_id]
    
    if user_id in vote_data['voters']:
        await callback.answer("Вы уже проголосовали", show_alert=True)
        return
    
    parts = callback.data.split('_')
    vote_option = parts[1]
    vote_type = parts[2]
    target_user_id = int(parts[3])
    
    if target_user_id != vote_data['target_user_id']:
        await callback.answer("Это голосование неактуально", show_alert=True)
        return
    
    if vote_type != vote_data['type']:
        await callback.answer("Это голосование неактуально", show_alert=True)
        return
    
    if vote_option == 'yes':
        vote_data['votes_yes'] += 1
        text = f"За {vote_data['type']}"
    elif vote_option == 'no':
        vote_data['votes_no'] += 1
        text = "Против"
    else:
        vote_data['votes_abstain'] += 1
        text = "Воздержался"
    
    vote_data['voters'].add(user_id)
    
    if vote_data['type'] == 'mute':
        type_name = "мьюте"
    else:
        type_name = "бане"
    
    current_text = (
        f"Голосование о {type_name}\n\n"
        f"Пользователь: {vote_data['target_user_name']}\n"
        f"Время: {VOTE_DURATION // 60} минут\n\n"
        f"За: {vote_data['votes_yes']}\n"
        f"Против: {vote_data['votes_no']}\n"
        f"Воздержались: {vote_data['votes_abstain']}\n"
        f"Всего голосов: {len(vote_data['voters'])}\n\n"
        f"Нужно голосов: {vote_data['votes_needed']}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За", callback_data=f"vote_yes_{vote_data['type']}_{target_user_id}")],
        [InlineKeyboardButton(text="Против", callback_data=f"vote_no_{vote_data['type']}_{target_user_id}")],
        [InlineKeyboardButton(text="Воздержался", callback_data=f"vote_abstain_{vote_data['type']}_{target_user_id}")]
    ])
    
    await callback.message.edit_text(current_text, reply_markup=keyboard)
    await callback.answer(f"Выбрано: {text}", show_alert=False)


async def end_vote_timer(chat_id: int):
    await asyncio.sleep(VOTE_DURATION)
    
    if chat_id in active_votes:
        await finalize_vote(chat_id)


async def finalize_vote(chat_id: int):
    if chat_id not in active_votes:
        return
    
    vote_data = active_votes.pop(chat_id)
    target_user_id = vote_data['target_user_id']
    target_user_name = vote_data['target_user_name']
    vote_type = vote_data['type']
    
    votes_yes = vote_data['votes_yes']
    votes_no = vote_data['votes_no']
    votes_abstain = vote_data['votes_abstain']
    total_votes = len(vote_data['voters'])
    votes_needed = vote_data['votes_needed']
    
    if vote_type == 'mute':
        type_name = "мьюте"
        type_action = "мьют"
    else:
        type_name = "бане"
        type_action = "бан"
    
    result_text = (
        f"Голосование завершено\n\n"
        f"Пользователь: {target_user_name}\n\n"
        f"За: {votes_yes}\n"
        f"Против: {votes_no}\n"
        f"Воздержались: {votes_abstain}\n"
        f"Всего: {total_votes}"
    )
    
    if votes_yes >= votes_needed:
        if vote_type == 'mute':
            result_text += f"\n\nРЕЗУЛЬТАТ: Мьют активирован\n{target_user_name} замьючен на {MUTE_DURATION // 60} минут"
            
            try:
                until_date = datetime.now() + timedelta(seconds=MUTE_DURATION)
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=target_user_id,
                    permissions=types.ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                logger.info(f"Пользователь {target_user_id} замьючен в чате {chat_id}")
            except Exception as e:
                result_text += f"\nОшибка при мьюте: {str(e)}"
                logger.error(f"Не удалось замьютить пользователя {target_user_id}: {e}")
        
        else:
            result_text += f"\n\nРЕЗУЛЬТАТ: Бан активирован\n{target_user_name} удален из группы"
            
            try:
                await bot.ban_chat_member(
                    chat_id=chat_id,
                    user_id=target_user_id
                )
                logger.info(f"Пользователь {target_user_id} забанен в чате {chat_id}")
            except Exception as e:
                result_text += f"\nОшибка при бане: {str(e)}"
                logger.error(f"Не удалось забанить пользователя {target_user_id}: {e}")
    else:
        result_text += f"\n\nРЕЗУЛЬТАТ: {type_action.upper()} не активирован\nНедостаточно голосов ({votes_yes} из {votes_needed})"
    
    response = await bot.send_message(chat_id, result_text)
    
    # Удалим сообщение с результатом через время
    asyncio.create_task(auto_delete_message(chat_id, response.message_id, AUTO_DELETE_TIMEOUT))


async def main():
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
