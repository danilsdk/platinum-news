import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from database import Session, User, News, Template
from news_grabber import get_news
from data.configuration import API_TOKEN, admin_username, channel_id
from sqlalchemy import text

bot = telebot.TeleBot(API_TOKEN)


# функция для проверки прав пользователя
def check_permissions(message):
    session = Session()
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if user is not None and user.username == admin_username:
        return "admin"

    if user:
        if user.is_banned:
            return 'banned'
        elif user.is_admin:
            return 'admin'
        else:
            return 'user'
    else:
        # добавляем нового пользователя в базу данных
        first_name = message.from_user.first_name or ''
        last_name = message.from_user.last_name or ''
        username = message.from_user.username or ''
        user_data = {
            'user_id': message.from_user.id,
            'nickname': f"{first_name} {last_name}",
            'username': f"@{username}",
            'is_banned': False
        }
        new_user = User(**user_data)
        session.add(new_user)
        session.commit()
        session.close()
        return 'user'


# функция для получения id вложения
def get_attachment(message):
    attachment = {
        'type': "text",
        'file_id': "",
        'text': message.text,
        'user': f"@{message.from_user.username}"
    }

    if message.photo:
        attachment['type'] = 'photo'
        attachment['file_id'] = message.photo[-1].file_id
        attachment['text'] = message.caption if message.caption is not None else ""
    elif message.video:
        attachment['type'] = 'video'
        attachment['file_id'] = message.video.file_id
        attachment['text'] = message.caption if message.caption is not None else ""
    elif message.animation:
        attachment['type'] = 'gif'
        attachment['file_id'] = message.animation.file_id
        attachment['text'] = message.caption if message.caption is not None else ""

    return attachment


@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    permission = check_permissions(message)

    session = Session()
    user = session.query(User).filter(User.user_id == user_id).first()
    session.close()

    try:
        bot.delete_message(chat_id, message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e

    # Проверяем статус пользователя
    if permission == 'admin':
        markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
        markup_admin.add('Найти новости', 'Очистить предложку')

        msg1 = bot.send_message(chat_id, 'Вы имеете права администратора\n\nИспользуйте кнопки👇',
                                reply_markup=markup_admin)

        bot.register_next_step_handler(msg1, admin_interface)
    else:
        markup_user = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup_user.add('Предложить новость 🗞', 'Профиль 👤')

        bot.send_sticker(chat_id, "CAACAgIAAxkBAAEInnRkPXKDFnovwn0W_L9IT1YQ1jl-DAACAQEAAladvQoivp8OuMLmNC8E")
        msg2 = bot.send_message(chat_id, f"""
    *Привет. {user.nickname}!* 👋

📰 С помощью этого бота ты сможешь отправить новость администратору канала *@channelexample* и он рассмотрит её к публикации. 

Для начала работы нажми на одну из кнопок ниже 👇
""", parse_mode="Markdown", reply_markup=markup_user)

        bot.register_next_step_handler(msg2, user_interface)


# Для юзеров
def user_interface(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    permission = check_permissions(message)
    if permission == 'admin':
        admin_interface(message)

    session = Session()
    user = session.query(User).filter(User.user_id == user_id).first()
    count = session.query(News).filter(News.source == f"{user.username}").count()
    session.close()

    try:
        bot.delete_message(chat_id, message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e

    markup_user = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    if message.text == "Профиль 👤":
        markup_user.add('Предложить новость 🗞', 'Профиль 👤')
        msg = bot.send_message(chat_id, f"""📄Профиль {user.nickname}({user.username})

📊Новостей на рассмотрении: {count}
Заблокирован: {"Да 🔴" if user.is_banned else "Нет 🟢"}""", reply_markup=markup_user)

        bot.register_next_step_handler(msg, user_interface)

    elif message.text in ['Предложить еще одну новость 🗞', 'Предложить новость 🗞']:
        if check_permissions(message) == 'banned':
            markup_user.add('Предложить новость 🗞', 'Профиль 👤')
            insert = bot.send_message(chat_id, "Ты заблокирован в боте и не можешь отправлять новости.",
                                      reply_markup=markup_user)
            bot.register_next_step_handler(insert, user_interface)
        else:
            insert = bot.send_message(chat_id,
                                      "Введи свою новость. Текст и все вложения (фото, видео, гиф) одним сообщением.")
            if permission == 'user':
                bot.register_next_step_handler(insert, news_sent)

    elif message.text == '/change_perm':
        get_perm(message)

    elif permission in ['user', 'banned']:
        markup_user.add('Предложить новость 🗞', 'Профиль 👤')
        msg = bot.send_message(chat_id, "Воспользуйся кнопками ниже 👇",
                               reply_markup=markup_user)

        bot.register_next_step_handler(msg, user_interface)


def news_sent(message):
    chat_id = message.chat.id

    # Создаем клавиатуру
    markup2 = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup2.add('Предложить еще одну новость 🗞', 'Профиль 👤')

    attachment = get_attachment(message)

    write_todb(attachment)

    msg = bot.send_message(chat_id, "Новость принята на рассмотрение! ✅", reply_markup=markup2)

    bot.register_next_step_handler(msg, user_interface)


def write_todb(attachment):
    with Session() as session:
        news = News(
            text=attachment['text'],
            attachment=attachment['file_id'],
            source=attachment['user'],
            type='text' if attachment['type'] is None else attachment['type']
        )
        session.add(news)
        session.commit()


# Для админа
def admin_interface(message):
    global news_count
    global current_news_index

    chat_id = message.chat.id

    permission = check_permissions(message)
    if permission == 'user':
        user_interface(message)

    try:
        bot.delete_message(chat_id, message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e

    if message.text == "Посмотреть новости":
        session = Session()

        news_count = len(session.query(News).all())

        current_news_index = 0

        # если нет новостей в базе данных, отправляем сообщение об этом
        if news_count == 0:
            markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
            markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
            markup_admin.add('Найти новости', 'Очистить предложку')

            msg = bot.send_message(chat_id, 'Новостей нет', reply_markup=markup_admin)

            bot.register_next_step_handler(msg, admin_interface)
        # отправляем первую новость
        send_news(message)

    elif message.text.split()[0] == '/ban':
        ban(message)

    elif message.text.split()[0] == '/unban':
        unban(message)

    elif message.text == "Сделать шаблон постов":
        session = Session()

        keyboard = InlineKeyboardMarkup(row_width=4)

        header_button = InlineKeyboardButton('🔼 Изменить заголовок', callback_data='header')
        footer_button = InlineKeyboardButton('🔽 Изменить нижнюю часть', callback_data='footer')
        reset = InlineKeyboardButton('🧹 Cбросить', callback_data='reset')
        back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

        keyboard.add(header_button, footer_button)
        keyboard.add(reset)
        keyboard.add(back_button)
        template = session.query(Template).first()

        bot.send_message(chat_id, f"Заголовок: {template.header}\n\nНижняя часть: {template.footer}",
                         reply_markup=keyboard)
        session.close()

    elif message.text == "Очистить предложку":
        markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
        markup_admin.add('Найти новости', 'Очистить предложку')

        session = Session()
        session.query(News).delete()
        session.commit()
        session.close()

        msg = bot.send_message(chat_id, "Предложка очищена 💨", reply_markup=markup_admin)
        bot.register_next_step_handler(msg, admin_interface)

    elif message.text == "Найти новости":
        session = Session()
        temp = session.query(Template).first()
        session.close()

        keyboard = InlineKeyboardMarkup(row_width=4)

        ru = InlineKeyboardButton('🇷🇺✔️' if temp.lang == 'ru' else '🇷🇺', callback_data='ru')
        en = InlineKeyboardButton('🇬🇧✔️' if temp.lang == 'en' else '🇬🇧', callback_data='en')
        back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

        keyboard.add(ru, en)
        keyboard.add(back_button)

        msg = bot.send_message(chat_id, "Отправьте текстовый запрос для поиска новостей", reply_markup=keyboard)

        bot.register_next_step_handler(msg, find_news, delete=msg)

    elif message.text == '/change_perm':
        get_perm(message)

    elif permission == 'admin':
        markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
        markup_admin.add('Найти новости', 'Очистить предложку')

        msg = bot.send_message(chat_id, "Воспользуйся кнопками ниже 👇", reply_markup=markup_admin)

        bot.register_next_step_handler(msg, admin_interface)


def send_news(message):
    chat_id = message.chat.id
    global news_count
    global current_news_index

    session = Session()
    news = session.get(News, current_news_index + 1)
    session.close()

    if not news:
        return

    # создаем клавиатуру для переключения между новостями и удаления новости
    keyboard = InlineKeyboardMarkup(row_width=4)
    k_list = []
    if current_news_index > 0:
        prev_button = InlineKeyboardButton('⬅', callback_data='prev')
        k_list.append(prev_button)
    if current_news_index < news_count - 1:
        next_button = InlineKeyboardButton('➡', callback_data='next')
        k_list.append(next_button)
    del_button = InlineKeyboardButton('❌', callback_data='delete')
    post_button = InlineKeyboardButton('✅', callback_data='post')
    edit_button = InlineKeyboardButton('✏️', callback_data='edit')
    profile_button = InlineKeyboardButton('👤', callback_data='profile')
    back_button = InlineKeyboardButton('↩️ Вернуться назад', callback_data='back')
    keyboard.row(*k_list)
    keyboard.add(post_button, del_button, edit_button, profile_button)
    keyboard.add(back_button)

    # проверяем тип вложения и отправляем соответствующий метод
    if news.type == 'photo':
        bot.send_photo(chat_id, news.attachment, caption=news.text, reply_markup=keyboard)
    elif news.type == 'video':
        bot.send_video(chat_id, news.attachment, caption=news.text, reply_markup=keyboard)
    elif news.type == 'gif':
        bot.send_animation(chat_id, news.attachment, caption=news.text, reply_markup=keyboard)
    else:
        bot.send_message(chat_id, news.text, reply_markup=keyboard)

    try:
        bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e


# обработчик нажатия на кнопку в инлайн-клавиатуре
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global current_news_index
    global news_count
    global old_post
    global user_name

    session = Session()
    chat_id = call.message.chat.id

    try:
        news = session.get(News, current_news_index + 1)
    except NameError:
        news = None

    # проверяем, какая кнопка была нажата
    if call.data == 'next':
        current_news_index += 1
        if current_news_index >= news_count:
            current_news_index = 0

    elif call.data == 'prev':
        current_news_index -= 1
        if current_news_index < 0:
            current_news_index = news_count - 1

    elif call.data in ['delete', 'post']:
        if call.data == 'post':
            post_to_channel(current_news_index)
        # Отсоединяем объект от предыдущей сессии

        # Удаляем объект из текущей сессии
        session.delete(news)
        session.commit()
        stmt = text('UPDATE News SET id = id - 1 WHERE id > :id_str')
        session.execute(stmt, {'id_str': str(current_news_index + 1)})
        session.commit()

        # обновляем текущий индекс новости
        current_news_index = 0

        # удаляем текущую новость из списка всех новостей и обновляем количество новостей
        news_count -= 1

        # если была удалена последняя новость, переходим к первой
        if current_news_index >= news_count:
            current_news_index = 0
        try:
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # если сообщение уже было удалено, то игнорируем ошибку
            if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
                raise e

        # если нет новостей в базе данных, отправляем сообщение об этом
        if news_count == 0:
            markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
            markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
            markup_admin.add('Найти новости', 'Очистить предложку')

            msg = bot.send_message(call.message.chat.id, 'Новостей нет', reply_markup=markup_admin)

            bot.register_next_step_handler(msg, admin_interface)

    elif call.data == 'edit':
        global msg_new

        old_post = call.message
        msg_new = bot.send_message(chat_id, "Пришлите новый текст публикации")

        bot.register_next_step_handler(msg_new, edit_post)

    elif call.data == 'back':
        markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
        markup_admin.add('Найти новости', 'Очистить предложку')

        msg1 = bot.send_message(chat_id, 'Вы имеете права администратора\n\nИспользуйте кнопки👇',
                                reply_markup=markup_admin)

        bot.register_next_step_handler(msg1, admin_interface)

        try:
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # если сообщение уже было удалено, то игнорируем ошибку
            if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
                raise e

    elif call.data == 'profile':
        session = Session()
        news = session.get(News, current_news_index + 1)
        username = news.source
        user = session.query(User).filter(User.username == username).first()
        count = session.query(News).filter(News.source == username).count()
        session.close()

        global user_name
        user_name = username
        old_post = call.message
        keyboard = InlineKeyboardMarkup(row_width=2)

        if not user.is_banned:
            ban_button = InlineKeyboardButton('🚫 Забанить', callback_data='ban')
        else:
            ban_button = InlineKeyboardButton('✔️ Разбанить', callback_data='unban')
        back_button = InlineKeyboardButton('↩️ Вернуться назад', callback_data='back2')
        del_all = InlineKeyboardButton('🗑️ Удалить все', callback_data='del_all')
        keyboard.row(ban_button, del_all)
        keyboard.add(back_button)

        bot.send_message(chat_id, f"""Автор новости: {username}\nВсего новостей у пользователя: {count}""",
                         reply_markup=keyboard)

    elif call.data == 'back2':
        try:
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # если сообщение уже было удалено, то игнорируем ошибку
            if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
                raise e

    elif call.data == 'back3':
        bot.register_next_step_handler(call.message, admin_interface)
        try:
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # если сообщение уже было удалено, то игнорируем ошибку
            if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
                raise e

    elif call.data == 'ban':
        new_keyboard = InlineKeyboardMarkup(row_width=2)

        ban_button = InlineKeyboardButton('✔️ Разбанить', callback_data='unban')
        back_button = InlineKeyboardButton('↩️ Вернуться назад', callback_data='back2')
        del_all = InlineKeyboardButton('🗑️ Удалить все', callback_data='del_all')
        new_keyboard.row(ban_button, del_all)
        new_keyboard.add(back_button)

        session = Session()
        user = session.query(User).filter_by(username=user_name).first()

        if user is not None:
            user.is_banned = True
        session.commit()
        session.close()

        bot.edit_message_reply_markup(chat_id, message_id=call.message.id, reply_markup=new_keyboard)

    elif call.data == 'unban':
        new_keyboard = InlineKeyboardMarkup(row_width=2)

        ban_button = InlineKeyboardButton('🚫 Забанить', callback_data='ban')
        back_button = InlineKeyboardButton('↩️ Вернуться назад', callback_data='back2')
        del_all = InlineKeyboardButton('🗑️ Удалить все', callback_data='del_all')
        new_keyboard.row(ban_button, del_all)
        new_keyboard.add(back_button)

        session = Session()
        user = session.query(User).filter_by(username=user_name).first()

        if user is not None:
            user.is_banned = False
        session.commit()
        session.close()

        bot.edit_message_reply_markup(chat_id, message_id=call.message.id, reply_markup=new_keyboard)

    elif call.data == 'del_all':
        session = Session()
        cur_news = session.get(News, current_news_index + 1)
        all_news = session.query(News).filter(News.source == cur_news.source).all()
        session.close()

        # Удаляем объект из текущей сессии
        for news in all_news:
            session.delete(news)
            session.commit()

            news_count -= 1

        news_list = session.query(News).order_by(News.id).all()

        i = 1
        for news in news_list:
            news.id = i
            i += 1

        session.commit()

        current_news_index = 0
        # если была удалена последняя новость, переходим к первой
        if current_news_index >= news_count:
            current_news_index = 0
        try:
            bot.delete_message(chat_id=chat_id, message_id=old_post.message_id)
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)

        except telebot.apihelper.ApiTelegramException as e:
            # если сообщение уже было удалено, то игнорируем ошибку
            if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
                raise e

    elif call.data in ['footer', 'header']:
        msg = bot.send_message(chat_id,
                               f"Отправь измененн{'ый заголовок' if call.data == 'header' else 'ую нижнюю часть'}")

        bot.register_next_step_handler(msg, change_template, part=0 if call.data == 'header' else 1, edit=call.message,
                                       delete=msg)

    elif call.data == 'reset':
        session = Session()
        template = session.query(Template).first()

        template.header = ''
        template.footer = ''

        session.commit()

        keyboard = InlineKeyboardMarkup(row_width=4)

        header_button = InlineKeyboardButton('🔼 Изменить заголовок', callback_data='header')
        footer_button = InlineKeyboardButton('🔽 Изменить нижнюю часть', callback_data='footer')
        reset = InlineKeyboardButton('🧹 Cбросить', callback_data='reset')
        back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

        keyboard.add(header_button, footer_button)
        keyboard.add(reset)
        keyboard.add(back_button)

        bot.edit_message_text(f"Заголовок: {template.header}\n\nНижняя часть: {template.footer}", chat_id,
                              call.message.id,
                              reply_markup=keyboard)
        session.close()

    elif call.data in ['ru', 'en']:
        session = Session()
        template = session.query(Template).first()

        keyboard = InlineKeyboardMarkup(row_width=4)

        if call.data == 'ru':
            template.lang = 'ru'
        else:
            template.lang = 'en'

        ru = InlineKeyboardButton('🇷🇺✔️' if template.lang == 'ru' else '🇷🇺', callback_data='ru')
        en = InlineKeyboardButton('🇬🇧✔️' if template.lang == 'en' else '🇬🇧', callback_data='en')
        back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

        keyboard.add(ru, en)
        keyboard.add(back_button)

        session.commit()
        session.close()

        try:
            bot.edit_message_text(f"Отправьте текстовый запрос для поиска новостей", chat_id, call.message.id,
                                  reply_markup=keyboard)
        except telebot.apihelper.ApiTelegramException:
            pass

    elif call.data == 'find':
        bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)

        session = Session()
        temp = session.query(Template).first()
        session.close()

        keyboard = InlineKeyboardMarkup(row_width=4)

        ru = InlineKeyboardButton('🇷🇺✔️' if temp.lang == 'ru' else '🇷🇺', callback_data='ru')
        en = InlineKeyboardButton('🇬🇧✔️' if temp.lang == 'en' else '🇬🇧', callback_data='en')
        back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

        keyboard.add(ru, en)
        keyboard.add(back_button)

        msg = bot.send_message(chat_id, "Отправьте текстовый запрос для поиска новостей", reply_markup=keyboard)

        bot.register_next_step_handler(msg, find_news, delete=msg)

    session.close()

    if call.data in ['next', 'prev', 'delete', 'post', 'edit', 'del_all']:
        # отправляем новость
        send_news(call.message)


def change_template(message, part, edit, delete):
    session = Session()
    template = session.query(Template).first()

    if part == 0:
        template.header = message.text
    else:
        template.footer = message.text

    session.commit()

    keyboard = InlineKeyboardMarkup(row_width=4)

    header_button = InlineKeyboardButton('🔼 Изменить заголовок', callback_data='header')
    footer_button = InlineKeyboardButton('🔽 Изменить нижнюю часть', callback_data='footer')
    reset = InlineKeyboardButton('🧹 Cбросить', callback_data='reset')
    back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

    keyboard.add(header_button, footer_button)
    keyboard.add(reset)
    keyboard.add(back_button)

    bot.edit_message_text(f"Заголовок: {template.header}\n\nНижняя часть: {template.footer}", edit.chat.id, edit.id,
                          reply_markup=keyboard)
    bot.delete_message(edit.chat.id, delete.id)
    bot.delete_message(message.chat.id, message.id)
    session.close()


def edit_post(message):
    global current_news_index
    global news_count
    global msg_new
    global old_post

    permission = check_permissions(message)
    if permission == 'user':
        return

    new_text = message.text

    session = Session()
    news = session.get(News, current_news_index + 1)
    if news is not None:
        news.text = new_text
        session.commit()
    session.close()

    post_to_channel(current_news_index)
    bot.delete_message(message.chat.id, msg_new.id)

    # Удаляем объект из текущей сессии
    session.delete(news)
    session.commit()
    stmt = text('UPDATE News SET id = id - 1 WHERE id > :id_str')
    session.execute(stmt, {'id_str': str(current_news_index + 1)})
    session.commit()

    # обновляем текущий индекс новости
    current_news_index = 0

    # удаляем текущую новость из списка всех новостей и обновляем количество новостей
    news_count -= 1

    # если была удалена последняя новость, переходим к первой
    if current_news_index >= news_count:
        current_news_index = 0
    try:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e

    # если нет новостей в базе данных, отправляем сообщение об этом
    if news_count == 0:
        markup_admin = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup_admin.add('Посмотреть новости', 'Сделать шаблон постов')
        markup_admin.add('Найти новости', 'Очистить предложку')

        msg = bot.send_message(message.chat.id, 'Новостей нет', reply_markup=markup_admin)

        bot.register_next_step_handler(msg, admin_interface)

    bot.delete_message(chat_id=message.chat.id, message_id=old_post.message_id)
    send_news(message)
    return


def post_to_channel(news_id):
    session = Session()
    template = session.query(Template).first()
    session.close()

    data = get_news_by_id(news_id + 1)

    type = data['type']
    file_id = data['attachment']
    text = data['text']
    source = data['source']

    caption = f'{template.header} {source}\n\n{text}\n\n{template.footer}'

    if type == 'photo':
        bot.send_photo(channel_id, file_id, caption=caption)
    elif type == 'video':
        bot.send_video(channel_id, file_id, caption=caption)
    elif type == 'gif':
        bot.send_animation(channel_id, file_id, caption=caption)
    else:
        bot.send_message(channel_id, caption)


def get_news_by_id(news_id):
    session = Session()
    news = session.get(News, news_id)
    news_dict = news.__dict__
    del news_dict['_sa_instance_state']
    return news_dict


def find_news(message, delete):
    chat_id = message.chat.id

    session = Session()
    temp = session.query(Template).first()
    session.close()

    language = temp.lang
    request_text = message.text

    data = get_news(request_text, language)

    try:
        bot.delete_message(chat_id, delete.id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e

    keyboard = InlineKeyboardMarkup(row_width=4)

    find = InlineKeyboardButton('🔄 Искать еще', callback_data='find')
    back_button = InlineKeyboardButton('↩️Вернуться назад', callback_data='back3')

    keyboard.add(find)
    keyboard.add(back_button)

    if data == '404':
        bot.send_message(chat_id, "Новость не найдена", reply_markup=keyboard)
    else:
        text = f"{data['title']}\n\nИсточник: {data['source']}\n Дата публикации: {data['date']}\n\nСсылка: {data['url']}"
        if data['image'] is not None:
            bot.send_photo(chat_id, data['image'], caption=text, reply_markup=keyboard)
        else:
            bot.send_message(chat_id, text, reply_markup=keyboard)


@bot.message_handler(commands=['ban'])
def ban(username):
    if check_permissions(username) != 'admin':
        return

    session = Session()
    user = session.query(User).filter_by(username=username.text.split()[1]).first()

    if user is not None:
        user.is_banned = True
    session.commit()
    session.close()

    bot.register_next_step_handler(username, admin_interface)
    try:
        bot.delete_message(username.chat.id, username.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e


@bot.message_handler(commands=['unban'])
def unban(username):
    if check_permissions(username) != 'admin':
        return

    session = Session()
    user = session.query(User).filter_by(username=username.text.split()[1]).first()

    if user is not None:
        user.is_banned = False
    session.commit()
    session.close()

    bot.register_next_step_handler(username, admin_interface)
    try:
        bot.delete_message(username.chat.id, username.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e


@bot.message_handler(commands=['change_perm'])  # смена прав пользователя - функция для тестирования
def get_perm(message):
    session = Session()
    user = session.query(User).filter_by(user_id=message.from_user.id).first()

    if user is not None and user.is_admin:
        user.is_admin = False
    elif user is not None and not user.is_admin:
        user.is_admin = True

    session.commit()
    session.close()

    bot.register_next_step_handler(message, send_welcome)
    bot.send_message(message.chat.id, "Смена прав")
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        # если сообщение уже было удалено, то игнорируем ошибку
        if e.result.status_code != 400 or 'message to delete not found' not in e.result.json()['description']:
            raise e


bot.infinity_polling()
