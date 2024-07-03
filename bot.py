from datetime import datetime

import requests
import telegram
from telegram.constants import ParseMode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, \
    InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
import json
import os
import asyncio
import httpx

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# URL вашего Django API
DJANGO_API_URL = 'http://127.0.0.1:8000/'
DJANGO_MEDIA_URL = 'http://localhost:8000/api'

# Директория для хранения фотографий
PHOTO_DIR = 'photos'

if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

reply_keyboard_main = [
    [KeyboardButton("/info")],
    [KeyboardButton("/start")],
    [KeyboardButton("/choice")],
]
reply_markup_kb_main = ReplyKeyboardMarkup(reply_keyboard_main, resize_keyboard=True, one_time_keyboard=False)


async def welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_keyboard = [
        [KeyboardButton("/info")],
        [KeyboardButton("/start")],
        [KeyboardButton("/choice")]
    ]
    reply_markup_kb = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_text(
        "Добро пожаловать! Я бот-помощник по передаче фронт работ. Вот что я умею: \n"
        "/info — Для вызова информации всех команд\n"
        "/start — Для начала работы\n"
        "/choice — Для смены организации\n",
        reply_markup=reply_markup_kb
    )


async def choose_organization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Получаем список организаций
    response = requests.get(f'{DJANGO_API_URL}organizations/')
    if response.status_code == 200:
        organizations = response.json()
        # Создание кнопок в колонку
        keyboard = [
            [InlineKeyboardButton(org['organization'], callback_data=f'org_{org["id"]}')] for org in organizations
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите вашу организацию:', reply_markup=reply_markup)
        context.user_data['stage'] = 'choose_organization'
    else:
        await update.message.reply_text('Ошибка при получении списка организаций. Попробуйте снова.')


# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    password = context.args[0] if context.args else None

    response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
    logger.info(f"Ответ от API при проверке пользователя: {response.status_code}, {response.text}")
    if response.status_code == 404:
        if str(password).lower() == 'secret_password':
            context.user_data['is_authorized'] = True
            await update.message.reply_text('Пожалуйста, представьтесь. Введите ваше ФИО:')
            context.user_data['stage'] = 'get_full_name'
        else:
            await update.message.reply_text('Пожалуйста, введите пароль для авторизации командой /start [пароль]:')
            context.user_data['stage'] = 'get_password'
    else:
        user_data = response.json()
        if user_data['is_authorized']:
            if user_data['organization_id']:
                await send_main_menu(update.message.chat.id, context, user_data['full_name'], user_data['organization_id'])
            else:
                await update.message.reply_text('Пожалуйста, выберите организацию командой /choice.')
        else:
            if str(password).lower() == 'secret_password':
                user_data['is_authorized'] = True
                requests.put(f'{DJANGO_API_URL}users/{user_id}/', json=user_data)
                await update.message.reply_text('Пожалуйста, представьтесь. Введите ваше ФИО:')
                context.user_data['stage'] = 'get_full_name'
            else:
                await update.message.reply_text('Пожалуйста, введите пароль для авторизации:')
                context.user_data['stage'] = 'get_password'


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text

    stage = context.user_data.get('stage')
    if stage == 'get_full_name':
        full_name = text
        context.user_data['full_name'] = full_name

        # Создаем пользователя в базе данных
        user_data = {
            'chat_id': user_id,
            'full_name': full_name,
            'is_authorized': context.user_data.get('is_authorized', False),
            'organization': None  # Передаем organization как None
        }
        logger.info(f"Отправка данных в API для создания пользователя: {json.dumps(user_data, indent=2)}")
        response = requests.post(f'{DJANGO_API_URL}users/', json=user_data)
        logger.info(f"Ответ от API при создании пользователя: {response.status_code}, {response.text}")
        if response.status_code == 201:
            response = requests.get(f'{DJANGO_API_URL}organizations/')
            if response.status_code == 200:
                organizations = response.json()
                # Создание кнопок в колонку
                keyboard = [
                    [InlineKeyboardButton(org['organization'], callback_data=f'org_{org["id"]}')] for org in
                    organizations
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text('Выберите вашу организацию:', reply_markup=reply_markup)
                context.user_data['stage'] = 'choose_organization'
            else:
                await update.message.reply_text('Ошибка при получении списка организаций. Попробуйте снова.')
        else:
            await update.message.reply_text('Ошибка при создании пользователя. Попробуйте снова.')

    elif stage == 'get_password':
        if text == 'secret_password':
            response = requests.get(f'{DJANGO_API_URL}users/{user_id}/')
            if response.status_code == 200:
                user_data = response.json()
                user_data['is_authorized'] = True
                response = requests.put(f'{DJANGO_API_URL}users/{user_id}/', json=user_data)
                if response.status_code == 200:
                    await update.message.reply_text(f'Вы успешно авторизованы, {user_data["full_name"]}!')
                    await update.message.reply_text('Пожалуйста, представьтесь. Введите ваше ФИО:')
                    context.user_data['stage'] = 'get_full_name'
                else:
                    await update.message.reply_text('Ошибка при обновлении данных. Попробуйте снова.')
            else:
                # Создание нового пользователя если не существует
                context.user_data['is_authorized'] = True
                await update.message.reply_text('Пожалуйста, представьтесь. Введите ваше ФИО:')
                context.user_data['stage'] = 'get_full_name'
        else:
            await update.message.reply_text('Неверный пароль, попробуйте еще раз:')



    elif stage and stage.startswith('rework_'):
        front_id = int(stage.split('_')[1])
        boss_response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
        if boss_response.status_code == 200:
            boss_data = boss_response.json()
            boss_id = boss_data['id']
            boss_name = boss_data['full_name']
            front_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
            if front_response.status_code == 200:
                front_data = front_response.json()

                # Обновляем необходимые поля, оставляя остальные без изменений
                updated_data = front_data
                updated_data.update({
                    'status': 'in_process',
                    'remarks': text,
                    'boss': boss_id
                })

                logger.info(

                    f"Отправка данных в API для обновления записи FrontTransfer: {json.dumps(updated_data, indent=2)}")

                response = requests.put(f'{DJANGO_API_URL}fronttransfers/{front_id}/', json=updated_data)
                logger.info(
                    f"Ответ от API при обновлении записи FrontTransfer: {response.status_code}, {response.text}")
                if response.status_code == 200:
                    sender_chat_id = front_data['sender_chat_id']

                    # Получаем названия объекта, вида работ и блока/секции
                    object_name = "неизвестно"
                    block_section_name = "неизвестно"
                    work_type_name = "неизвестно"
                    object_response = requests.get(f'{DJANGO_API_URL}objects/{front_data["object_id"]}/')

                    if object_response.status_code == 200:
                        object_name = object_response.json().get('name', "неизвестно")

                    block_section_response = requests.get(
                        f'{DJANGO_API_URL}blocksections/{front_data["block_section_id"]}/')

                    if block_section_response.status_code == 200:
                        block_section_name = block_section_response.json().get('name', "неизвестно")

                    work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front_data["work_type_id"]}/')

                    if work_type_response.status_code == 200:
                        work_type_name = work_type_response.json().get('name', "неизвестно")

                    notification_text = (
                        f"\U0000274C Генеральный подрядчик *{boss_name}* отклонил передачу фронт работ:\n"
                        f"\n\n*Объект:* {object_name}\n"
                        f"*Секция/Блок:* {block_section_name}\n"
                        f"*Этаж:* {front_data.get('floor', 'неизвестно')}\n"
                        f"*Вид работ:* {work_type_name}\n"
                        f"*Причина:* {text}\n"
                        "\n\n_Вы можете повторно передать фронт с учетом замечаний._"
                    )

                    keyboard = [
                        [InlineKeyboardButton("Передать фронт заново", callback_data='transfer')],

                    ]

                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await context.bot.send_message(
                        chat_id=sender_chat_id,
                        text=notification_text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup

                    )

                    keyboard2 = [

                        [InlineKeyboardButton("Просмотр фронт работ", callback_data='view_fronts')],

                    ]

                    reply_markup2 = InlineKeyboardMarkup(keyboard2)
                    await update.message.reply_text('Комментарий отправлен подрядчику. Фронт отправлен в хранилище.',

                                                    reply_markup=reply_markup2)

                else:
                    await update.message.reply_text(f'Ошибка при обновлении статуса фронта: {response.text}')
            else:
                await update.message.reply_text('Ошибка при получении деталей фронта. Попробуйте снова.')
        else:
            await update.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')
        context.user_data['stage'] = None

    elif stage and stage.startswith('decline_'):
        front_id = int(stage.split('_')[1])
        user_chat_id = update.message.from_user.id
        user_name = requests.get(f'{DJANGO_API_URL}users/chat/{user_chat_id}/').json()['full_name']
        decline_reason = text

        # Обновляем статус фронта на "отклонен"
        front_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
        if front_response.status_code == 200:
            front_data = front_response.json()
            boss_id = front_data['boss_id']
            sender_chat_id = front_data['sender_chat_id']

            # Получаем chat_id босса по его id
            boss_response = requests.get(f'{DJANGO_API_URL}users/{boss_id}/')
            if boss_response.status_code == 200:
                boss_chat_id = boss_response.json()['chat_id']
            else:
                await update.message.reply_text('Ошибка при получении chat_id ген подрядчика.')
                return

            # Получаем названия объекта, вида работ и блока/секции
            object_response = requests.get(f'{DJANGO_API_URL}objects/{front_data["object_id"]}/')
            work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front_data["work_type_id"]}/')
            block_section_response = requests.get(
                f'{DJANGO_API_URL}blocksections/{front_data["block_section_id"]}/')

            if object_response.status_code == 200:
                object_name = object_response.json().get('name', 'Неизвестный объект')
            else:
                object_name = 'Неизвестный объект'

            if work_type_response.status_code == 200:
                work_type_name = work_type_response.json().get('name', 'Неизвестный вид работ')
            else:
                work_type_name = 'Неизвестный вид работ'

            if block_section_response.status_code == 200:
                block_section_name = block_section_response.json().get('name', 'Неизвестный блок/секция')
            else:
                block_section_name = 'Неизвестный блок/секция'

            # Получаем данные об организации отправителя
            sender_response = requests.get(f'{DJANGO_API_URL}users/{front_data["sender_id"]}/')
            if sender_response.status_code == 200:
                sender_data = sender_response.json()
                organization_id = sender_data['organization_id']
                organization_response = requests.get(f'{DJANGO_API_URL}organizations/{organization_id}/')

                if organization_response.status_code == 200:
                    organization_name = organization_response.json().get('organization', 'неизвестно')
                else:
                    organization_name = 'неизвестно'
            # Получаем данные о новом виде работ
            next_work_type_id = front_data['next_work_type_id']
            if next_work_type_id:
                next_work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{next_work_type_id}/')
                if next_work_type_response.status_code == 200:
                    next_work_type_name = next_work_type_response.json().get('name', 'Не указан')
                else:
                    next_work_type_name = 'Не указан'
            else:
                next_work_type_name = 'Не указан'

            updated_data = {
                'sender_id': front_data['sender_id'],
                'sender_chat_id': front_data['sender_chat_id'],
                'object_id': front_data['object_id'],
                'work_type_id': front_data['work_type_id'],
                'block_section_id': front_data['block_section_id'],
                'floor': front_data['floor'],
                'status': 'in_process',
                'remarks': decline_reason,
                'created_at': front_data['created_at'],
                'approval_at': front_data['approval_at'],
                'boss_id': boss_id,
                'receiver_id': front_data['receiver_id'],
                'next_work_type_id': front_data['next_work_type_id'],
                'photo_ids': front_data['photo_ids'],
            }

            response = requests.put(f'{DJANGO_API_URL}fronttransfers/{front_id}/', json=updated_data)
            if response.status_code == 200:
                # Уведомление ген подрядчика и создателя
                notification_text = (
                    f"\U0000274C Фронт работ отклонен *{user_name}*:\n"
                    f"\n\n*Объект:* {object_name}\n"
                    f"*Секция/Блок:* {block_section_name}\n"
                    f"*Этаж:* {front_data['floor']}\n\n"
                    f"*Вид работ:* {work_type_name}\n"
                    f"*Новый вид работ:* {next_work_type_name}\n"
                    f"*Причина отклонения:* {decline_reason}\n"

                )
                notification_text2 = (
                    f"\U0000274C Фронт работ отклонен *{user_name}*:\n"
                    f"\n\n*Объект:* {object_name}\n"
                    f"*Секция/Блок:* {block_section_name}\n"
                    f"*Этаж:* {front_data['floor']}\n\n"
                    f"*Вид работ:* {work_type_name}\n"
                    f"*Новый вид работ:* {next_work_type_name}\n"
                    f"*Причина отклонения:* {decline_reason}\n"
                    "\n\n_Исправьте замечания и повторно передайте фронт через команду /start_"
                )

                await context.bot.send_message(
                    chat_id=boss_chat_id,
                    text=notification_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                await context.bot.send_message(
                    chat_id=sender_chat_id,
                    text=notification_text2,
                    parse_mode=ParseMode.MARKDOWN
                )
                await update.message.reply_text('Фронт успешно отклонен и уведомления отправлены.')

            else:
                await update.message.reply_text(f'Ошибка при обновлении статуса фронта: {response.text}')
        else:
            await update.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.')
        context.user_data['stage'] = None
    else:
        response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
        if response.status_code == 404:
            await update.message.reply_text('Пожалуйста, представьтесь. Введите ваше ФИО:')
            context.user_data['stage'] = 'get_full_name'
        else:
            user_data = response.json()
            if user_data['is_authorized']:
                if user_data['organization_id']:
                    await welcome_message(update, context)
                else:
                    await update.message.reply_text('Пожалуйста, выберите организацию командой /choice.')
            else:
                await update.message.reply_text('Пожалуйста, введите пароль для авторизации:')
                context.user_data['stage'] = 'get_password'


async def send_main_menu(chat_id, context: ContextTypes.DEFAULT_TYPE, full_name: str, organization_id: int) -> None:
    if not organization_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Вы не выбрали организацию. Пожалуйста, выберите её командой /choice."
        )
        return

    # Получаем имя организации по ID
    response = requests.get(f'{DJANGO_API_URL}organizations/{organization_id}/')
    if response.status_code == 200:
        organization_data = response.json()
        organization_name = organization_data['organization']
        is_general_contractor = organization_data.get('is_general_contractor', False)
    else:
        organization_name = "Неизвестная организация"
        is_general_contractor = False

    if is_general_contractor:
        keyboard = [
            [InlineKeyboardButton("Просмотр фронт работ", callback_data='view_fronts')],
            [InlineKeyboardButton("Выдать фронт", callback_data='issue_front')],

        ]
    else:
        keyboard = [
            [InlineKeyboardButton("Передать фронт", callback_data='transfer')],
            [InlineKeyboardButton("Принять фронт", callback_data='accept')],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text=f'Здравствуйте, {full_name} из организации "{organization_name}"! Выберите действие:',
        reply_markup=reply_markup
    )
    context.user_data['main_menu_message_id'] = message.message_id


async def choose_work_type(query: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения
    response = requests.get(f'{DJANGO_API_URL}worktypes/')
    if response.status_code == 200:
        work_types = response.json()
        keyboard = [
            [InlineKeyboardButton(work['name'], callback_data=f'work_{work["id"]}')] for work in work_types
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Выберите тип работ:', reply_markup=reply_markup)
        context.user_data['object_id'] = object_id
        context.user_data['stage'] = 'choose_work_type'
    else:
        await query.message.reply_text('Ошибка при получении списка типов работ. Попробуйте снова.')


async def choose_block_section(query: Update, context: ContextTypes.DEFAULT_TYPE, work_type_id: int) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения
    object_id = context.user_data['object_id']
    response = requests.get(f'{DJANGO_API_URL}objects/{object_id}/blocksections/')
    if response.status_code == 200:
        block_sections = response.json()
        keyboard = [
            [InlineKeyboardButton(block['name'], callback_data=f'block_{block["id"]}')] for block in block_sections
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Выберите блок или секцию:', reply_markup=reply_markup)
        context.user_data['work_type_id'] = work_type_id
        context.user_data['stage'] = 'choose_block_section'
    else:
        await query.message.reply_text('Ошибка при получении списка блоков или секций. Попробуйте снова.')


async def choose_floor(query: Update, context: ContextTypes.DEFAULT_TYPE, block_section_id: int) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения
    response = requests.get(f'{DJANGO_API_URL}blocksections/{block_section_id}/')
    if response.status_code == 200:
        block_section = response.json()
        number_of_floors = block_section['number_of_floors']
        keyboard = [[InlineKeyboardButton(f'{i} этаж', callback_data=f'floor_{i}')] for i in
                    range(-2, number_of_floors + 1)]
        keyboard.append([InlineKeyboardButton('Кровля', callback_data='floor_roof')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Выберите этаж:', reply_markup=reply_markup)
        context.user_data['block_section_id'] = block_section_id
        context.user_data['stage'] = 'choose_floor'
    else:
        await query.message.reply_text('Ошибка при получении информации о блоке или секции. Попробуйте снова.')


async def confirm_transfer_data(query: Update, context: ContextTypes.DEFAULT_TYPE, floor: str) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения
    floor_number = floor if floor != 'roof' else 'Кровля'
    context.user_data['floor'] = floor_number

    # Получаем названия объектов, видов работ и блоков/секций
    object_id = context.user_data['object_id']
    work_type_id = context.user_data['work_type_id']
    block_section_id = context.user_data['block_section_id']

    object_name = requests.get(f'{DJANGO_API_URL}objects/{object_id}/').json()['name']
    work_type_name = requests.get(f'{DJANGO_API_URL}worktypes/{work_type_id}/').json()['name']
    block_section_name= requests.get(f'{DJANGO_API_URL}blocksections/{block_section_id}/').json()['name']

    transfer_info = (
        f"Объект: {object_name}\n"
        f"Вид работ: {work_type_name}\n"
        f"Блок/Секция: {block_section_name}\n"
        f"Этаж: {floor_number}\n"
    )

    keyboard = [
        [InlineKeyboardButton("\U00002705 Да", callback_data='confirm_yes')],
        [InlineKeyboardButton("\U0000274C Нет", callback_data='confirm_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f'Подтвердите данные:\n{transfer_info}', reply_markup=reply_markup)


async def handle_transfer_confirmation(query: Update, context: ContextTypes.DEFAULT_TYPE, confirmed: bool) -> None:
    if confirmed:
        user_chat_id = str(query.from_user.id)  # Преобразуем в строку

        # Получаем данные пользователя по chat_id
        response = requests.get(f'{DJANGO_API_URL}users/chat/{user_chat_id}/')
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data['id']
        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')
            return

        transfer_data = {
            'sender_id': user_id,  # Изменено на sender_id
            'sender_chat_id': user_chat_id,
            'object_id': context.user_data['object_id'],  # Изменено на object_id
            'work_type_id': context.user_data['work_type_id'],  # Изменено на work_type_id
            'block_section_id': context.user_data['block_section_id'],  # Изменено на block_section_id
            'floor': context.user_data['floor'],
            'created_at': datetime.now().isoformat(),
            'approval_at': datetime.now().isoformat(),
            'status': 'transferred',
            'photos': []
        }
        logger.info(f"Отправка данных в API для создания передачи фронта: {json.dumps(transfer_data, indent=2)}")
        response = requests.post(f'{DJANGO_API_URL}fronttransfers/', json=transfer_data)
        logger.info(f"Ответ от API при создании передачи фронта: {response.status_code}, {response.text}")
        if response.status_code == 200:
            transfer = response.json()
            context.user_data['transfer_id'] = transfer['id']
            context.user_data['photos'] = []  # Сброс списка фотографий
            context.user_data.pop('last_photo_message_id', None)  # Сброс идентификатора последнего сообщения

            # Удаляем только кнопки
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                'Этаж успешно выбран! Пожалуйста, прикрепите фотографии (до 10 штук) или нажмите /done:')
            context.user_data['stage'] = 'attach_photos'

            # Оповещение главных подрядчиков
            transfer_data.update({
                'object_name': requests.get(f'{DJANGO_API_URL}objects/{context.user_data["object_id"]}/').json()['name'],
                'work_type_name': requests.get(f'{DJANGO_API_URL}worktypes/{context.user_data["work_type_id"]}/').json()['name'],
                'block_section_name': requests.get(f'{DJANGO_API_URL}blocksections/{context.user_data["block_section_id"]}/').json()['name'],
            })
            logger.info(f"Передача данных в notify_general_contractors: {json.dumps(transfer_data, indent=2)}")
            # await notify_general_contractors(context, transfer_data)
        else:
            await query.message.reply_text('Ошибка при создании передачи фронта. Попробуйте снова.')
    else:
        await query.message.delete()
        user_id = query.from_user.id
        response = requests.get(f'{DJANGO_API_URL}users/{user_id}/')
        if response.status_code == 200:
            user_data = response.json()
            full_name = user_data.get('full_name', 'Пользователь')
            organization_id = user_data.get('organization', None)
            if organization_id:
                await query.message.reply_text('Передача отменена.', reply_markup=reply_markup_kb_main)
                await send_main_menu(query.message.chat.id, context, full_name, organization_id)
            else:
                await query.message.reply_text(
                    'Ошибка: у вас не выбрана организация. Пожалуйста, выберите организацию командой /choice.')
        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')


async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('stage') == 'attach_photos':
        transfer_id = context.user_data.get('transfer_id')
        if transfer_id is None:
            await update.message.reply_text('Ошибка: идентификатор передачи фронта не найден. Попробуйте снова.')
            return

        photos = context.user_data.get('photos', [])
        file_id = update.message.photo[-1].file_id
        photos.append(file_id)
        context.user_data['photos'] = photos

        # Удаляем предыдущее сообщение об успешной загрузке, если оно существует
        if 'last_photo_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.message.chat.id,
                    message_id=context.user_data['last_photo_message_id']
                )
            except telegram.error.BadRequest as e:
                if str(e) != "Message to delete not found":
                    raise

        if len(photos) < 10:
            reply_keyboard = [
                [KeyboardButton("/done")]
            ]
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

            message = await update.message.reply_text(
                f'Фотография {len(photos)} из 10 успешно загружена. Прикрепите ещё или нажмите /done для завершения.',
                reply_markup=reply_markup
            )
            context.user_data['last_photo_message_id'] = message.message_id
        else:
            await finalize_photo_upload(update, context)


async def handle_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('stage') == 'attach_photos':
        await finalize_photo_upload(update, context)


async def finalize_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transfer_id = context.user_data.get('transfer_id')
    photos = context.user_data.get('photos', [])

    # Получаем текущие данные о фронте
    front_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{transfer_id}/')
    if front_response.status_code == 200:
        front_data = front_response.json()
        # Обновляем поля, включая фото и статус
        update_data = {
            'sender_id': front_data.get('sender_id'),
            'object_id': front_data.get('object_id'),
            'work_type_id': front_data.get('work_type_id'),
            'block_section_id': front_data.get('block_section_id'),
            'floor': front_data.get('floor'),
            'status': 'transferred',
            'created_at': front_data.get('created_at'),
            'approval_at': front_data.get('approval_at'),
            'sender_chat_id': front_data.get('sender_chat_id'),
            'photo_ids': photos,
        }

        response = requests.put(f'{DJANGO_API_URL}fronttransfers/{transfer_id}/', json=update_data)
        logger.info(f"Ответ от API при обновлении передачи фронта: {response.status_code}, {response.text}")
        if response.status_code == 200:
            await update.message.reply_text('Фотографии успешно загружены. Передача фронта завершена!', reply_markup=reply_markup_kb_main)
            context.user_data['stage'] = None

            # Уведомляем ген подрядчиков
            transfer_data = {
                'object_name': requests.get(f'{DJANGO_API_URL}objects/{front_data["object_id"]}/').json()['name'],
                'work_type_name': requests.get(f'{DJANGO_API_URL}worktypes/{front_data["work_type_id"]}/').json()['name'],
                'block_section_name': requests.get(f'{DJANGO_API_URL}blocksections/{front_data["block_section_id"]}/').json()['name'],
                'floor': front_data['floor'],
                'sender_chat_id': front_data['sender_chat_id']
            }
            await notify_general_contractors(context, transfer_data)

            # Отправляем сообщение с главным меню
            user_id = str(update.message.from_user.id)
            response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
            if response.status_code == 200:
                user_data = response.json()
                full_name = user_data.get('full_name', 'Пользователь')
                organization_id = user_data.get('organization_id', None)
                if organization_id:
                    await send_main_menu(update.message.chat.id, context, full_name, organization_id)
                else:
                    await update.message.reply_text(
                        'Ошибка: у вас не выбрана организация. Пожалуйста, выберите организацию командой /choice.')
            else:
                await update.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')
        else:
            await update.message.reply_text(f'Ошибка при загрузке фотографий: {response.text}')
    else:
        await update.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.')



async def view_fronts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.message.delete()
    response = requests.get(f'{DJANGO_API_URL}fronttransfers/?status=transferred')
    if response.status_code == 200:
        fronts = response.json()
        if fronts:
            keyboard = []
            for front in fronts:
                # Получаем имена объектов, видов работ и блоков/секций
                object_response = requests.get(f'{DJANGO_API_URL}objects/{front["object_id"]}/')
                work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front["work_type_id"]}/')
                block_section_response = requests.get(f'{DJANGO_API_URL}blocksections/{front["block_section_id"]}/')

                if object_response.status_code == 200 and work_type_response.status_code == 200 and block_section_response.status_code == 200:
                    object_name = object_response.json()['name']
                    work_type_name = work_type_response.json()['name']
                    block_section_name = block_section_response.json()['name']

                    button_text = f"{object_name} - {work_type_name} - {block_section_name} - {front['floor']}"
                    callback_data = f"front_{front['id']}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
                else:
                    # Обработка ошибок при получении данных
                    await update.callback_query.message.reply_text("Ошибка при получении данных. Попробуйте снова.")
                    return

            keyboard.append([InlineKeyboardButton("↻ Обновить", callback_data='view_fronts')])
            keyboard.append([InlineKeyboardButton("Назад", callback_data='main_menu')])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.message.reply_text("Список текущих фронтов работ:", reply_markup=reply_markup)
        else:
            await update.callback_query.message.reply_text("Нет доступных фронтов работ со статусом 'передано'.")
    else:
        await update.callback_query.message.reply_text("Ошибка при получении списка фронтов работ. Попробуйте снова.")


async def view_front_details(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения
    response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
    if response.status_code == 200:
        front = response.json()
        sender_chat_id = front['sender_chat_id']  # Используем sender_chat_id

        sender_response = requests.get(f'{DJANGO_API_URL}users/chat/{sender_chat_id}/')
        if sender_response.status_code == 200:

            sender_response_id_org =  sender_response.json()["organization_id"]
            org_response = requests.get(f'{DJANGO_API_URL}organizations/{sender_response_id_org}/').json()["organization"]

            sender_full_name = sender_response.json()["full_name"]

            # Получаем имена объекта, вида работ и блока/секции
            object_response = requests.get(f'{DJANGO_API_URL}objects/{front["object_id"]}/')
            work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front["work_type_id"]}/')
            block_section_response = requests.get(f'{DJANGO_API_URL}blocksections/{front["block_section_id"]}/')

            if object_response.status_code == 200 and work_type_response.status_code == 200 and block_section_response.status_code == 200:
                object_name = object_response.json()['name']
                work_type_name = work_type_response.json()['name']
                block_section_name = block_section_response.json()['name']
            else:
                await query.message.reply_text("Ошибка при получении данных. Попробуйте снова.")
                return

            message_text = (
                f"*Отправитель:* {sender_full_name}\n"
                f"*Организация:* {org_response}\n"
                f"*Объект:* {object_name}\n"
                f"*Вид работ:* {work_type_name}\n"
                f"*Блок/Секция:* {block_section_name}\n"
                f"*Этаж:* {front['floor']}\n"
                f"*Дата передачи (МСК):* {front['created_at']}"
            )

            # Список InputMediaPhoto для отправки группой
            media_group = []

            # Кнопка "На доработку"
            keyboard = [
                [InlineKeyboardButton("\U0000274C Доработка", callback_data=f"rework_{front_id}"),
                 InlineKeyboardButton("👥 Передать", callback_data=f"transfer_{front_id}"),
                 InlineKeyboardButton("\U00002705 Принять", callback_data=f"approve_{front_id}")],
                [InlineKeyboardButton("К списку фронтов", callback_data='view_fronts')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправка фотографий
            photo_ids = front.get('photo_ids', [])
            for idx, photo_id in enumerate(photo_ids):
                if photo_id:
                    if idx == 0:
                        media_group.append(
                            InputMediaPhoto(media=photo_id, caption=message_text, parse_mode=ParseMode.MARKDOWN))
                    else:
                        media_group.append(InputMediaPhoto(media=photo_id))

            # Если есть фото, отправляем группу медиа
            if media_group:
                await context.bot.send_media_group(chat_id=query.message.chat.id, media=media_group)

                # Отправляем кнопки после попытки отправки медиа группы
                await context.bot.send_message(
                    chat_id=query.message.chat.id,
                    text="Выберите действие:",
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat.id,
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN
                )

                # Отправляем кнопки после попытки отправки медиа группы
                await context.bot.send_message(
                    chat_id=query.message.chat.id,
                    text="Выберите действие:",
                    reply_markup=reply_markup
                )
        else:
            await query.message.reply_text("Ошибка при получении данных отправителя.")
    else:
        await query.message.reply_text("Ошибка при получении деталей фронта работ.")


async def handle_rework(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    await query.message.reply_text('Пожалуйста, введите причину доработки:')
    context.user_data['stage'] = f'rework_{front_id}'



async def approve_front(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    try:
        await query.message.delete()
    except telegram.error.BadRequest:
        logger.warning("Message to delete not found")

    user_id = query.message.chat.id

    # Получаем данные фронта
    response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
    if response.status_code == 200:
        front = response.json()

        # Получаем данные генерального подрядчика
        boss_response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
        if boss_response.status_code == 200:
            boss_data = boss_response.json()
            boss_name = boss_data['full_name']
            boss_id = boss_data['id']

            # Обновляем статус фронта на "approved"
            update_data = {
                'status': 'approved',
                'approval_at': datetime.now().isoformat(),
                'boss_id': boss_id,
                'object_id': front['object_id'],
                'work_type_id': front['work_type_id'],
                'block_section_id': front['block_section_id'],
                'floor': front['floor'],
                'sender_id': front['sender_id'],
                'created_at': front['created_at'],
                'sender_chat_id': front['sender_chat_id']
            }
            response = requests.put(f'{DJANGO_API_URL}fronttransfers/{front_id}/', json=update_data)
            if response.status_code == 200:
                # Уведомляем отправителя
                sender_chat_id = front['sender_chat_id']

                # Получаем названия объекта, вида работ и блока/секции
                object_name = "неизвестно"
                block_section_name = "неизвестно"
                work_type_name = "неизвестно"

                if 'object_name' in front:
                    object_name = front['object_name']
                else:
                    object_response = requests.get(f'{DJANGO_API_URL}objects/{front["object_id"]}/')
                    if object_response.status_code == 200:
                        object_name = object_response.json().get('name', "неизвестно")

                if 'block_section_name' in front:
                    block_section_name = front['block_section_name']
                else:
                    block_section_response = requests.get(
                        f'{DJANGO_API_URL}blocksections/{front["block_section_id"]}/')
                    if block_section_response.status_code == 200:
                        block_section_name = block_section_response.json().get('name', "неизвестно")

                if 'work_type_name' in front:
                    work_type_name = front['work_type_name']
                else:
                    work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front["work_type_id"]}/')
                    if work_type_response.status_code == 200:
                        work_type_name = work_type_response.json().get('name', "неизвестно")

                notification_text = (
                    f"\U00002705 Ваш фронт работ был принят генеральным подрядчиком *{boss_name}*:\n"
                    f"\n\n*Объект:* {object_name}\n"
                    f"*Секция/Блок:* {block_section_name}\n"
                    f"*Этаж:* {front.get('floor', 'неизвестно')}\n"
                    f"*Вид работ:* {work_type_name}\n"
                )
                await context.bot.send_message(
                    chat_id=sender_chat_id,
                    text=notification_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                await query.message.reply_text('Фронт успешно принят.', reply_markup=reply_markup_kb_main)
                # Получаем данные пользователя для отображения главного меню
                response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
                if response.status_code == 200:
                    user_data = response.json()
                    full_name = user_data.get('full_name', 'Пользователь')
                    organization_id = user_data.get('organization_id', None)
                    await send_main_menu(user_id, context, full_name, organization_id)
                else:
                    await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')
            else:
                await query.message.reply_text('Ошибка при обновлении статуса фронта. Попробуйте снова.')
        else:
            await query.message.reply_text('Ошибка при получении данных генерального подрядчика. Попробуйте снова.')
    else:
        await query.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.')



async def handle_transfer(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    await query.message.delete()
    context.user_data['transfer_front_id'] = front_id
    response = requests.get(f'{DJANGO_API_URL}organizations/')
    if response.status_code == 200:
        organizations = response.json()
        keyboard = [
            [InlineKeyboardButton(org['organization'], callback_data=f'transfer_org_{org["id"]}')] for org in
            organizations
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Выберите организацию:', reply_markup=reply_markup)
        context.user_data['stage'] = 'choose_transfer_organization'
    else:
        await query.message.reply_text('Ошибка при получении списка организаций. Попробуйте снова.')


async def choose_transfer_user(query: Update, context: ContextTypes.DEFAULT_TYPE, org_id: int) -> None:
    await query.message.delete()
    context.user_data['transfer_org_id'] = org_id

    # Получаем ID пользователя, которому принадлежит фронт
    front_id = context.user_data['transfer_front_id']
    front_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
    if front_response.status_code == 200:
        front_data = front_response.json()
        current_user_id = front_data['sender_id']  # Получаем ID отправителя фронта

        # Получаем список пользователей и фильтруем их по организации
        response = requests.get(f'{DJANGO_API_URL}users/')
        if response.status_code == 200:
            users = response.json()

            # Фильтрация пользователей по организации
            filtered_users = [user for user in users if user['organization_id'] == org_id]

            # Исключаем отправителя фронта из списка пользователей
            # filtered_users = [user for user in filtered_users if user['id'] != current_user_id]

            if filtered_users:
                keyboard = [
                    [InlineKeyboardButton(user['full_name'], callback_data=f'transfer_user_{user["chat_id"]}')] for user in filtered_users
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text('Выберите пользователя:', reply_markup=reply_markup)
                context.user_data['stage'] = 'choose_transfer_user'
            else:
                await query.message.reply_text('В этой организации нет доступных пользователей.',
                                               reply_markup=InlineKeyboardMarkup([
                                                   [InlineKeyboardButton("Назад", callback_data='transfer_')]
                                               ]))
        else:
            await query.message.reply_text('Ошибка при получении списка пользователей. Попробуйте снова.')
    else:
        await query.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.')


async def choose_transfer_work_type(query: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    await query.message.delete()
    context.user_data['transfer_user_id'] = user_id
    response = requests.get(f'{DJANGO_API_URL}worktypes/')
    if response.status_code == 200:
        work_types = response.json()
        keyboard = [
            [InlineKeyboardButton(work['name'], callback_data=f'transfer_work_{work["id"]}')] for work in work_types
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Выберите вид работ:', reply_markup=reply_markup)
        context.user_data['stage'] = 'choose_transfer_work_type'
    else:
        await query.message.reply_text('Ошибка при получении списка видов работ. Попробуйте снова.')


async def confirm_transfer(query: Update, context: ContextTypes.DEFAULT_TYPE, work_type_id: int) -> None:
    await query.message.delete()
    front_id = context.user_data['transfer_front_id']
    org_id = context.user_data['transfer_org_id']
    user_chat_id = context.user_data['transfer_user_id']  # Это chat_id пользователя

    # Используем правильный маршрут для получения данных пользователя по chat_id
    response = requests.get(f'{DJANGO_API_URL}users/chat/{user_chat_id}/')
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data['id']  # Получаем id пользователя из данных

        boss_response = requests.get(f'{DJANGO_API_URL}users/chat/{query.from_user.id}/')
        if boss_response.status_code == 200:
            boss_data = boss_response.json()
            boss_id = boss_data['id']

            # Получаем данные о виде работ по его ID
            work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{work_type_id}/')
            if work_type_response.status_code == 200:
                work_type_data = work_type_response.json()
                work_type_name = work_type_data['name']
                work_type_id_base = work_type_data['id']
            else:
                await query.message.reply_text('Ошибка при получении данных вида работ. Попробуйте снова.')
                return

            # Получаем текущие данные о фронте
            front_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
            if front_response.status_code == 200:
                front_data = front_response.json()

                # Получаем дополнительные данные об объекте, блоке/секции и виде работ
                object_response = requests.get(f'{DJANGO_API_URL}objects/{front_data["object_id"]}/')
                block_section_response = requests.get(
                    f'{DJANGO_API_URL}blocksections/{front_data["block_section_id"]}/')
                current_work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front_data["work_type_id"]}/')

                # Получаем данные об организации отправителя
                sender_response = requests.get(f'{DJANGO_API_URL}users/{front_data["sender_id"]}/')
                if sender_response.status_code == 200:
                    sender_data = sender_response.json()
                    organization_id = sender_data['organization_id']
                    organization_response = requests.get(f'{DJANGO_API_URL}organizations/{organization_id}/')

                    if organization_response.status_code == 200:
                        organization_name = organization_response.json().get('organization', 'неизвестно')
                    else:
                        organization_name = 'неизвестно'

                    if object_response.status_code == 200:
                        object_name = object_response.json().get('name', 'неизвестно')
                    else:
                        object_name = 'неизвестно'

                    if block_section_response.status_code == 200:
                        block_section_name = block_section_response.json().get('name', 'неизвестно')
                    else:
                        block_section_name = 'неизвестно'

                    if current_work_type_response.status_code == 200:
                        current_work_type_name = current_work_type_response.json().get('name', 'неизвестно')
                    else:
                        current_work_type_name = 'неизвестно'

                    # Обновляем статус фронта на "on_consideration"
                    front_data.update({
                        'status': 'on_consideration',
                        'receiver_id': user_id,  # Используем id пользователя
                        'next_work_type_id': work_type_id_base,
                        'boss_id': boss_id
                    })

                    logger.info(
                        f"Отправка данных в API для обновления записи FrontTransfer: {json.dumps(front_data, indent=2)}")
                    response = requests.put(f'{DJANGO_API_URL}fronttransfers/{front_id}/', json=front_data)
                    logger.info(
                        f"Ответ от API при обновлении записи FrontTransfer: {response.status_code}, {response.text}")

                    if response.status_code == 200:
                        await query.message.reply_text('Фронт успешно передан на рассмотрение.')

                        # Отправляем уведомление получателю
                        transfer_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
                        if transfer_response.status_code == 200:
                            transfer = transfer_response.json()

                            sender_response = requests.get(f'{DJANGO_API_URL}users/chat/{transfer["sender_chat_id"]}/')
                            if sender_response.status_code == 200:
                                sender_data = sender_response.json()
                                sender_full_name = sender_data.get('full_name', 'Неизвестный отправитель')

                                message_text = (
                                    f"*Вам передан фронт работ*\n"
                                    f"*Отправитель:* {sender_full_name}\n"
                                    f"*Организация:* {organization_name}\n"
                                    f"*Объект:* {object_name}\n"
                                    f"*Вид работ:* {current_work_type_name}\n"
                                    f"*Блок/Секция:* {block_section_name}\n"
                                    f"*Этаж:* {transfer['floor']}\n"
                                    f"*Дата передачи (МСК):* {transfer['created_at']}\n"
                                    f"*Новый вид работ:* {work_type_name}"
                                )

                                keyboard = [
                                    [InlineKeyboardButton("\U00002705 Принять",
                                                          callback_data=f"accept_front_{front_id}")],
                                    [InlineKeyboardButton("\U0000274C Отклонить",
                                                          callback_data=f"decline_front_{front_id}")]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)

                                # Отправка фотографий
                                media_group = []
                                photo_ids = transfer.get('photo_ids', [])
                                for idx, photo_id in enumerate(photo_ids):
                                    if photo_id:
                                        if idx == 0:
                                            media_group.append(InputMediaPhoto(media=photo_id, caption=message_text,
                                                                               parse_mode=ParseMode.MARKDOWN))
                                        else:
                                            media_group.append(InputMediaPhoto(media=photo_id))

                                # Если есть фото, отправляем группу медиа
                                if media_group:
                                    await context.bot.send_media_group(chat_id=user_chat_id, media=media_group)
                                    await context.bot.send_message(
                                        chat_id=user_chat_id,
                                        text="Выберите действие:",
                                        reply_markup=reply_markup
                                    )
                                else:
                                    await context.bot.send_message(
                                        chat_id=user_chat_id,
                                        text=message_text,
                                        reply_markup=reply_markup,
                                        parse_mode=ParseMode.MARKDOWN
                                    )

                            else:
                                await query.message.reply_text('Ошибка при получении данных отправителя.')
                        else:
                            await query.message.reply_text('Ошибка при получении данных передачи фронта.')
                    else:
                        await query.message.reply_text(f'Ошибка при обновлении статуса фронта: {response.text}')
                else:
                    await query.message.reply_text('Ошибка при получении данных отправителя.')
            else:
                await query.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.')
        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')
    else:
        await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')


async def accept_front(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    await query.edit_message_reply_markup(reply_markup=None)
    response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
    if response.status_code == 200:
        front = response.json()
        user_chat_id = str(query.from_user.id)  # Преобразуем в строку

        # Проверка наличия ключа 'receiver_id' в данных фронта
        if 'receiver_id' not in front:
            await query.message.reply_text('Ошибка: получатель фронта не указан.')
            return

        # Создание нового фронта с новым статусом
        new_front_data = {
            'sender_id': front['receiver_id'],  # Принимающий становится отправителем
            'sender_chat_id': user_chat_id,
            'object_id': front['object_id'],
            'work_type_id': front['next_work_type_id'],
            'block_section_id': front['block_section_id'],
            'floor': front['floor'],
            'status': 'in_process',
            'created_at': datetime.now().isoformat(),
            'approval_at': datetime.now().isoformat(),
            'photo1': None,
            'photo2': None,
            'photo3': None,
            'photo4': None,
            'photo5': None,
            'receiver_id': None,
            'remarks': None,
            'next_work_type_id': None,
            'boss_id': None,
            'photo_ids': [],
        }

        response = requests.post(f'{DJANGO_API_URL}fronttransfers/', json=new_front_data)
        if response.status_code == 200:
            # Получаем все старые данные от фронта
            old_front_data = {
                'sender_id': front['sender_id'],
                'object_id': front['object_id'],
                'work_type_id': front['work_type_id'],
                'block_section_id': front['block_section_id'],
                'floor': front['floor'],
                'status': 'approved',  # Обновляем статус
                'photo1': front['photo1'],
                'photo2': front['photo2'],
                'photo3': front['photo3'],
                'photo4': front['photo4'],
                'photo5': front['photo5'],
                'receiver_id': front['receiver_id'],
                'remarks': front['remarks'],
                'next_work_type_id': front['next_work_type_id'],
                'boss_id': front['boss_id'],
                'created_at': front['created_at'],
                'approval_at': datetime.now().isoformat(),  # Обновляем дату
                'photo_ids': front['photo_ids'],
                'sender_chat_id': front['sender_chat_id'],
            }

            response = requests.put(f'{DJANGO_API_URL}fronttransfers/{front_id}/', json=old_front_data)
            if response.status_code == 200:
                # Получаем chat_id босса по его id
                boss_id = front['boss_id']
                boss_response = requests.get(f'{DJANGO_API_URL}users/{boss_id}/')
                if boss_response.status_code == 200:
                    boss_chat_id = boss_response.json()['chat_id']
                else:
                    await query.message.reply_text('Ошибка при получении chat_id ген подрядчика.')
                    return

                # Получаем chat_id создателя по его id
                sender_id = front['sender_id']
                sender_response = requests.get(f'{DJANGO_API_URL}users/{sender_id}/')
                if sender_response.status_code == 200:
                    sender_chat_id = sender_response.json()['chat_id']
                else:
                    await query.message.reply_text('Ошибка при получении chat_id создателя фронта.')
                    return

                # Получение данных для уведомления
                object_response = requests.get(f'{DJANGO_API_URL}objects/{front["object_id"]}/')
                block_section_response = requests.get(f'{DJANGO_API_URL}blocksections/{front["block_section_id"]}/')
                work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front["work_type_id"]}/')

                if object_response.status_code == 200:
                    object_name = object_response.json().get('name', 'Неизвестный объект')
                else:
                    object_name = 'Неизвестный объект'

                if block_section_response.status_code == 200:
                    block_section_name = block_section_response.json().get('name', 'Неизвестный блок/секция')
                else:
                    block_section_name = 'Неизвестный блок/секция'

                if work_type_response.status_code == 200:
                    work_type_name = work_type_response.json().get('name', 'Неизвестный вид работ')
                else:
                    work_type_name = 'Неизвестный вид работ'

                notification_text = (
                    f"\U00002705 Фронт работ успешно принят:"
                    f"\n\n*Объект:* {object_name}\n"
                    f"*Секция/Блок:* {block_section_name}\n"
                    f"*Этаж:* {front['floor']}\n"
                    f"*Вид работ:* {work_type_name}\n"
                )

                await context.bot.send_message(
                    chat_id=boss_chat_id,
                    text=notification_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                await context.bot.send_message(
                    chat_id=sender_chat_id,
                    text=notification_text,
                    parse_mode=ParseMode.MARKDOWN
                )

                await query.message.reply_text('Фронт успешно принят. Нажмите /start для быстрой передачи фронт работ.',
                                               reply_markup=reply_markup_kb_main)
            else:
                await query.message.reply_text(f'Ошибка при обновлении статуса старого фронта: {response.text}',
                                               reply_markup=reply_markup_kb_main)
        else:
            await query.message.reply_text(f'Ошибка при создании нового фронта: {response.text}',
                                           reply_markup=reply_markup_kb_main)
    else:
        await query.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.',
                                       reply_markup=reply_markup_kb_main)


async def decline_front(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text('Пожалуйста, введите причину отклонения:')
    context.user_data['stage'] = f'decline_{front_id}'


async def notify_general_contractors(context: ContextTypes.DEFAULT_TYPE, transfer_data: dict) -> None:
    logger.info("Начало выполнения notify_general_contractors")
    response = requests.get(f'{DJANGO_API_URL}users/?organization=3')
    if response.status_code == 200:
        all_users = response.json()

        # Фильтруем пользователей с organization_id = 3
        general_contractors = [user for user in all_users if user.get('organization_id') == 3]

        sender_chat_id = transfer_data["sender_chat_id"]
        sender_response = requests.get(f'{DJANGO_API_URL}users/chat/{sender_chat_id}/')



        if sender_response.status_code == 200:
            sender_data = sender_response.json()
            sender_full_name = sender_data.get('full_name', 'Неизвестный отправитель')
            org_response = requests.get(f'{DJANGO_API_URL}organizations/{sender_data["organization_id"]}/').json()
            sender_organization = org_response["organization"]


            logger.info(f"Уведомление подрядчиков, количество: {len(general_contractors)}")
            for contractor in general_contractors:
                chat_id = contractor['chat_id']
                keyboard = [
                    [InlineKeyboardButton("Просмотр фронт работ", callback_data='view_fronts')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                message_text = (
                    f"*Создан новый фронт работ*\n"
                    f"*Отправитель:* {sender_full_name}\n"
                    f"*Организация:* {sender_organization}\n"
                    f"*Объект:* {transfer_data['object_name']}\n"
                    f"*Вид работ:* {transfer_data['work_type_name']}\n"
                    f"*Блок/Секция:* {transfer_data['block_section_name']}\n"
                    f"*Этаж:* {transfer_data['floor']}"
                )
                logger.info(f"Отправка сообщения подрядчику с chat_id: {chat_id}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                )
        else:
            logger.error(f"Ошибка при получении данных отправителя: {sender_response.status_code}")
    else:
        logger.error(f"Ошибка при получении списка пользователей: {response.status_code}")


async def choose_existing_front(query: Update, context: ContextTypes.DEFAULT_TYPE, fronts: list) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения

    keyboard = []
    for front in fronts:
        # Получаем названия объектов, видов работ и блоков/секции
        object_name = "неизвестно"
        work_type_name = "неизвестно"
        block_section_name = "неизвестно"

        # Если данные уже есть в ответе, используем их
        if 'object_name' in front:
            object_name = front['object_name']
        else:
            object_response = requests.get(f'{DJANGO_API_URL}objects/{front["object_id"]}/')
            if object_response.status_code == 200:
                object_name = object_response.json().get('name', "неизвестно")

        if 'work_type_name' in front:
            work_type_name = front['work_type_name']
        else:
            work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{front["work_type_id"]}/')
            if work_type_response.status_code == 200:
                work_type_name = work_type_response.json().get('name', "неизвестно")

        if 'block_section_name' in front:
            block_section_name = front['block_section_name']
        else:
            block_section_response = requests.get(f'{DJANGO_API_URL}blocksections/{front["block_section_id"]}/')
            if block_section_response.status_code == 200:
                block_section_name = block_section_response.json().get('name', "неизвестно")

        button_text = f"{object_name} - {work_type_name} - {block_section_name} - {front['floor']}"
        callback_data = f"existing_front_{front['id']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text('Выберите фронт для продолжения передачи:', reply_markup=reply_markup)
    context.user_data['stage'] = 'choose_existing_front'


async def handle_existing_front_selection(query: Update, context: ContextTypes.DEFAULT_TYPE, front_id: int) -> None:
    await query.message.delete()  # Удаление предыдущего сообщения
    context.user_data['transfer_id'] = front_id
    context.user_data['photos'] = []  # Сброс списка фотографий
    context.user_data.pop('last_photo_message_id', None)  # Сброс идентификатора последнего сообщения

    # Получаем текущие данные о фронте
    front_response = requests.get(f'{DJANGO_API_URL}fronttransfers/{front_id}/')
    if front_response.status_code == 200:
        front_data = front_response.json()
        # Обновляем статус фронта на "transferred"
        front_data['status'] = 'transferred'
        response = requests.put(f'{DJANGO_API_URL}fronttransfers/{front_id}/', json=front_data)
        logger.info(f"Ответ от API при обновлении статуса фронта: {response.status_code}, {response.text}")

        if response.status_code == 200:
            # Уведомление ген подрядчиков
            transfer_data = {
                'object_name': front_data.get('object_name', 'неизвестно'),
                'work_type_name': front_data.get('work_type_name', 'неизвестно'),
                'block_section_name': front_data.get('block_section_name', 'неизвестно'),
                'floor': front_data['floor'],
                'sender_chat_id': front_data['sender_chat_id']
            }
            # await notify_general_contractors(context, transfer_data)

            await query.message.reply_text(
                'Продолжите передачу фронта. Пожалуйста, прикрепите фотографии (до 10 штук) или нажмите /done:')
            context.user_data['stage'] = 'attach_photos'
        else:
            await query.message.reply_text('Ошибка при обновлении статуса фронта. Попробуйте снова.')
    else:
        await query.message.reply_text('Ошибка при получении данных фронта. Попробуйте снова.')


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data.startswith('org_'):
        org_id = int(data.split('_')[1])

        # Получаем текущие данные пользователя
        response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
        if response.status_code == 200:
            user_data = response.json()
            user_data['organization_id'] = org_id  # Обновляем поле organization_id

            logger.info(f"Отправка данных в API: {json.dumps(user_data, indent=2)}")
            response = requests.put(f'{DJANGO_API_URL}users/{user_data["id"]}/', json=user_data)
            logger.info(f"Ответ от API: {response.status_code}, {response.text}")

            if response.status_code == 200:
                reply_keyboard = [
                    [KeyboardButton("/info")],
                    [KeyboardButton("/start")],
                    [KeyboardButton("/choice")]
                ]
                reply_markup_kb = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
                await query.message.delete()
                await query.message.reply_text(
                    'Организация успешно выбрана!',
                    reply_markup=reply_markup_kb
                )
                user_data = response.json()
                await send_main_menu(query.message.chat.id, context, user_data['full_name'], user_data['organization_id'])
            else:
                await query.message.reply_text('Ошибка при сохранении данных. Попробуйте снова.')
        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')

    elif data.startswith('work_'):
        work_type_id = int(data.split('_')[1])
        await choose_block_section(query, context, work_type_id)

    elif data.startswith('block_'):
        block_section_id = int(data.split('_')[1])
        await choose_floor(query, context, block_section_id)

    elif data.startswith('floor_'):
        floor = data.split('_')[1]
        await confirm_transfer_data(query, context, floor)

    elif data == 'confirm_yes':
        await handle_transfer_confirmation(query, context, confirmed=True)

    elif data == 'confirm_no':
        await handle_transfer_confirmation(query, context, confirmed=False)


    elif data == 'transfer':

        # Удаление сообщения с основным меню
        if 'main_menu_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat.id,
                    message_id=context.user_data['main_menu_message_id']
                )

            except telegram.error.BadRequest:
                logger.warning("Message to delete not found")

        response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
        if response.status_code == 200:
            user_data = response.json()
            if not user_data['organization_id']:
                await query.message.reply_text('Пожалуйста, выберите организацию командой /choice.')
                return

        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')
            return

        response = requests.get(f'{DJANGO_API_URL}objects/')
        if response.status_code == 200:
            objects = response.json()

            keyboard = [
                [InlineKeyboardButton(obj['name'], callback_data=f'obj_{obj["id"]}')] for obj in objects
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text('Выберите объект:', reply_markup=reply_markup)
            context.user_data['stage'] = 'choose_object'

        else:
            await query.message.reply_text('Ошибка при получении списка объектов. Попробуйте снова.')

    elif data.startswith('obj_'):
        object_id = int(data.split('_')[1])

        # Получаем фронты, где пользователь является отправителем и статус "in_process"
        response = requests.get(f'{DJANGO_API_URL}fronttransfers/?sender_chat_id={user_id}&status=in_process')
        if response.status_code == 200:
            fronts = response.json()
            if fronts:
                await choose_existing_front(query, context, fronts)
            else:
                await choose_work_type(query, context, object_id)
        else:
            await query.message.reply_text('Ошибка при получении списка фронтов. Попробуйте снова.')

    elif data.startswith('existing_front_'):
        front_id = int(data.split('_')[2])
        await handle_existing_front_selection(query, context, front_id)

    elif data == 'accept':
        await query.edit_message_text(text="Вы выбрали 'Принять фронт'. Выполняется...")
        # Здесь можно добавить логику для действия "Принять фронт"

    elif data == 'view_fronts':
        await view_fronts(update, context)

    elif data.startswith('front_'):
        front_id = int(data.split('_')[1])
        await view_front_details(query, context, front_id)

    elif data.startswith('rework_'):
        front_id = int(data.split('_')[1])
        await handle_rework(query, context, front_id)

    elif data.startswith('approve_'):
        front_id = int(data.split('_')[1])
        await approve_front(query, context, front_id)

    elif data.startswith('accept_front_'):
        front_id = int(data.split('_')[2])
        await accept_front(query, context, front_id)

    elif data.startswith('decline_front_'):
        front_id = int(data.split('_')[2])
        await decline_front(query, context, front_id)

    elif data.startswith('transfer_'):
        if 'org_' in data:
            org_id = int(data.split('_')[2])
            await choose_transfer_user(query, context, org_id)

        elif 'user_' in data:
            user_id = int(data.split('_')[2])
            await choose_transfer_work_type(query, context, user_id)

        elif 'work_' in data:
            work_type_id = int(data.split('_')[2])
            await confirm_transfer(query, context, work_type_id)

        else:
            front_id = int(data.split('_')[1])
            await handle_transfer(query, context, front_id)

    elif data == 'back':
        await send_main_menu(query.message.chat.id, context, context.user_data['full_name'],
                             context.user_data['organization'])
    elif data == 'main_menu':
        await query.message.delete()
        await query.answer("Назад...")
        response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')
        if response.status_code == 200:
            user_data = response.json()
            full_name = user_data.get('full_name', 'Пользователь')
            organization_id = user_data.get('organization_id', None)
            await send_main_menu(query.message.chat.id, context, full_name, organization_id)

        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')


    elif data == 'issue_front':

        # Удаление сообщения с основным меню
        if 'main_menu_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=query.message.chat.id,
                message_id=context.user_data['main_menu_message_id']
            )

        response = requests.get(f'{DJANGO_API_URL}objects/')
        if response.status_code == 200:
            objects = response.json()
            keyboard = [
                [InlineKeyboardButton(obj['name'], callback_data=f'issue_obj_{obj["id"]}')] for obj in objects
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text('Выберите объект:', reply_markup=reply_markup)
            context.user_data['stage'] = 'issue_choose_object'

        else:
            await query.message.reply_text('Ошибка при получении списка объектов. Попробуйте снова.')


    elif data.startswith('issue_obj_'):
        await query.message.delete()  # Удаление предыдущего сообщения
        object_id = int(data.split('_')[2])
        context.user_data['issue_object_id'] = object_id
        response = requests.get(f'{DJANGO_API_URL}organizations/')
        if response.status_code == 200:
            organizations = response.json()
            keyboard = [
                [InlineKeyboardButton(org['organization'], callback_data=f'issue_org_{org["id"]}')] for org in
                organizations
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text('Выберите организацию:', reply_markup=reply_markup)
            context.user_data['stage'] = 'issue_choose_organization'

        else:
            await query.message.reply_text('Ошибка при получении списка организаций. Попробуйте снова.')



    elif data.startswith('issue_org_'):

        await query.message.delete()  # Удаление предыдущего сообщения

        org_id = int(data.split('_')[2])

        context.user_data['issue_org_id'] = org_id

        response = requests.get(f'{DJANGO_API_URL}users/')

        if response.status_code == 200:

            users = response.json()

            filtered_users = [user for user in users if user['organization_id'] == org_id]

            if filtered_users:

                keyboard = [

                    [InlineKeyboardButton(user['full_name'], callback_data=f'issue_user_{user["chat_id"]}')] for user in
                    filtered_users

                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.message.reply_text('Выберите пользователя:', reply_markup=reply_markup)

                context.user_data['stage'] = 'issue_choose_user'

            else:

                await query.message.reply_text('В этой организации нет доступных пользователей.')

        else:

            await query.message.reply_text('Ошибка при получении списка пользователей. Попробуйте снова.')


    elif data.startswith('issue_user_'):
        await query.message.delete()  # Удаление предыдущего сообщения
        user_chat_id = int(data.split('_')[2])
        context.user_data['issue_user_chat_id'] = user_chat_id
        response = requests.get(f'{DJANGO_API_URL}worktypes/')

        if response.status_code == 200:
            work_types = response.json()
            keyboard = [
                [InlineKeyboardButton(work['name'], callback_data=f'issue_work_{work["id"]}')] for work in work_types
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text('Выберите вид работ:', reply_markup=reply_markup)
            context.user_data['stage'] = 'issue_choose_work_type'

        else:
            await query.message.reply_text('Ошибка при получении списка видов работ. Попробуйте снова.')


    elif data.startswith('issue_work_'):
        await query.message.delete()  # Удаление предыдущего сообщения
        work_type_id = int(data.split('_')[2])
        context.user_data['issue_work_type_id'] = work_type_id
        response = requests.get(f'{DJANGO_API_URL}objects/{context.user_data["issue_object_id"]}/blocksections/')

        if response.status_code == 200:
            block_sections = response.json()
            keyboard = [
                [InlineKeyboardButton(block['name'], callback_data=f'issue_block_{block["id"]}')] for block in
                block_sections
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text('Выберите блок или секцию:', reply_markup=reply_markup)
            context.user_data['stage'] = 'issue_choose_block_section'

        else:
            await query.message.reply_text('Ошибка при получении списка блоков или секций. Попробуйте снова.')


    elif data.startswith('issue_block_'):
        await query.message.delete()  # Удаление предыдущего сообщения
        block_section_id = int(data.split('_')[2])
        context.user_data['issue_block_section_id'] = block_section_id
        response = requests.get(f'{DJANGO_API_URL}blocksections/{block_section_id}/')

        if response.status_code == 200:
            block_section = response.json()
            number_of_floors = block_section['number_of_floors']
            keyboard = [[InlineKeyboardButton(f'{i} этаж', callback_data=f'issue_floor_{i}')] for i in
                        range(-2, number_of_floors + 1)]
            keyboard.append([InlineKeyboardButton('Кровля', callback_data='issue_floor_roof')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text('Выберите этаж:', reply_markup=reply_markup)
            context.user_data['stage'] = 'issue_choose_floor'

        else:
            await query.message.reply_text('Ошибка при получении информации о блоке или секции. Попробуйте снова.')



    elif data.startswith('issue_floor_'):
        await query.message.delete()  # Удаление предыдущего сообщения
        floor = data.split('_')[2]
        floor_number = floor if floor != 'roof' else 'Кровля'
        context.user_data['issue_floor'] = floor_number

        # Получаем все данные до подтверждения
        user_chat_id = context.user_data['issue_user_chat_id']
        user_response = requests.get(f'{DJANGO_API_URL}users/chat/{user_chat_id}/')
        object_response = requests.get(f'{DJANGO_API_URL}objects/{context.user_data["issue_object_id"]}/')
        work_type_response = requests.get(f'{DJANGO_API_URL}worktypes/{context.user_data["issue_work_type_id"]}/')
        block_section_response = requests.get(
            f'{DJANGO_API_URL}blocksections/{context.user_data["issue_block_section_id"]}/')

        if user_response.status_code == 200 and object_response.status_code == 200 and work_type_response.status_code == 200 and block_section_response.status_code == 200:
            user_data = user_response.json()
            context.user_data['issue_user_id'] = user_data['id']
            context.user_data['issue_object_name'] = object_response.json()['name']
            context.user_data['issue_work_type_name'] = work_type_response.json()['name']
            context.user_data['issue_block_section_name'] = block_section_response.json()['name']

            transfer_info = (
                f"Объект: {context.user_data['issue_object_name']}\n"
                f"Вид работ: {context.user_data['issue_work_type_name']}\n"
                f"Блок/Секция: {context.user_data['issue_block_section_name']}\n"
                f"Этаж: {floor_number}\n"
            )

            keyboard = [
                [InlineKeyboardButton("\U00002705 Да", callback_data='issue_confirm_yes')],
                [InlineKeyboardButton("\U0000274C Нет", callback_data='issue_confirm_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(f'Подтвердите данные:\n{transfer_info}', reply_markup=reply_markup)

        else:
            await query.message.reply_text('Ошибка при получении данных. Попробуйте снова.')


    elif data == 'issue_confirm_yes':
        await query.edit_message_reply_markup(reply_markup=None)

        # Используем данные из контекста, чтобы избежать повторных запросов
        user_id = context.user_data['issue_user_id']
        user_chat_id = str(context.user_data['issue_user_chat_id'])  # Преобразуем в строку
        object_name = context.user_data['issue_object_name']
        work_type_name = context.user_data['issue_work_type_name']
        block_section_name = context.user_data['issue_block_section_name']
        floor_number = context.user_data['issue_floor']

        transfer_data = {
            'sender_id': user_id,
            'sender_chat_id': user_chat_id,
            'object_id': context.user_data['issue_object_id'],
            'work_type_id': context.user_data['issue_work_type_id'],
            'block_section_id': context.user_data['issue_block_section_id'],
            'floor': context.user_data['issue_floor'],
            'status': 'in_process',
            'created_at': datetime.now().isoformat(),
            'approval_at': datetime.now().isoformat(),
            'photos': []

        }

        # Добавим отладочную информацию для проверки данных

        logger.info(f"Отправка данных в API для создания нового фронта: {json.dumps(transfer_data, indent=2)}")
        response = requests.post(f'{DJANGO_API_URL}fronttransfers/', json=transfer_data)

        # Проверим ответ от API
        logger.info(f"Ответ от API при создании нового фронта: {response.status_code}, {response.text}")

        if response.status_code == 200:
            transfer = response.json()
            await query.message.reply_text('Фронт успешно выдан.')
            formatted_datetime = datetime.now().strftime('%d-%m-%Y %H:%M:%S')

            # Уведомление пользователя
            message_text = (

                f"Вам был выдан фронт работ:\n"
                f"*Объект:* {object_name}\n"
                f"*Вид работ:* {work_type_name}\n"
                f"*Блок/Секция:* {block_section_name}\n"
                f"*Этаж:* {floor_number}\n"
                f"*Дата выдачи (МСК):* {formatted_datetime}\n"

            )

            keyboard = [
                [InlineKeyboardButton("Передать фронт", callback_data='transfer')],

            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            try:

                # Попробуем отправить сообщение и логируем результат
                logger.info(f"Отправка сообщения пользователю с chat_id: {user_chat_id}")
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup

                )

                logger.info("Сообщение успешно отправлено пользователю")

            except Exception as e:

                # Логируем ошибку, если отправка сообщения не удалась
                logger.error(f"Ошибка при отправке сообщения пользователю: {e}")
                await query.message.reply_text(f"Ошибка при отправке сообщения пользователю: {e}")

            # Возвращение в главное меню

            user_id = query.from_user.id
            response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')

            if response.status_code == 200:
                user_data = response.json()
                full_name = user_data.get('full_name', 'Пользователь')
                organization_id = user_data.get('organization_id', None)
                await send_main_menu(user_id, context, full_name, organization_id)

            else:

                await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')


        else:

            await query.message.reply_text(f'Ошибка при создании фронта: {response.text}')


    elif data == 'issue_confirm_no':
        await query.message.delete()  # Удаление предыдущего сообщения
        await query.message.reply_text('Выдача фронта отменена.')
        user_id = query.from_user.id
        response = requests.get(f'{DJANGO_API_URL}users/chat/{user_id}/')

        if response.status_code == 200:
            user_data = response.json()
            full_name = user_data.get('full_name', 'Пользователь')
            organization_id = user_data.get('organization_id', None)
            await send_main_menu(user_id, context, full_name, organization_id)

        else:
            await query.message.reply_text('Ошибка при получении данных пользователя. Попробуйте снова.')


def main() -> None:
    # Вставьте свой токен
    application = Application.builder().token("7363654158:AAFfqLnieUtbqgpoKnTH0TAQajNRa4xjg-M").build()

    application.add_handler(CommandHandler("info", welcome_message))
    application.add_handler(CommandHandler("choice", choose_organization))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("done", handle_done_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_upload))

    application.run_polling()


if __name__ == '__main__':
    main()