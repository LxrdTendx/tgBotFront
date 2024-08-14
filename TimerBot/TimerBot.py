import logging
from datetime import datetime, timedelta
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Дата и время до которого нужно отсчитывать (16 августа 2024 года)
target_date = datetime(2024, 8, 16, 0, 0, 0)


async def countdown(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None) -> None:
    chat_id = update.effective_chat.id

    if message_id is None:
        # Если message_id нет, отправляем новое сообщение
        message = await context.bot.send_message(chat_id=chat_id, text="Обратный отсчёт начат...")
        message_id = message.message_id
    else:
        # Если message_id есть, редактируем уже существующее сообщение
        message = await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                      text="Обратный отсчёт начат...")

    while True:
        now = datetime.now()
        remaining_time = target_date - now

        if remaining_time <= timedelta(0):
            await message.edit_text("Событие наступило!")
            break

        days, seconds = remaining_time.days, remaining_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        countdown_text = f"До события осталось: {days} дней, {hours:02}:{minutes:02}:{seconds:02}"

        try:
            await message.edit_text(countdown_text)
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {e}")
            break

        await asyncio.sleep(60)  # Задержка на 1 секунду для обновления каждую секунду


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает таймер, отправляя новое сообщение."""
    chat_id = update.effective_chat.id

    # Останавливаем текущий таймер, если он существует
    if 'task' in context.chat_data:
        context.chat_data['task'].cancel()

    # Запуск нового таймера
    task = asyncio.create_task(countdown(update, context))
    context.chat_data['task'] = task


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение о неизвестной команде."""
    await update.message.reply_text("Извините, я не знаю такую команду. Попробуйте /start.")


def main() -> None:
    """Запуск бота."""
    application = Application.builder().token("7360747408:AAHR6iS_ySoSscGJ2bWuFutZN5ZQiTXh8ok").build()

    # Обработка команды /start
    application.add_handler(CommandHandler("timer", start))

    # Обработка всех неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()
