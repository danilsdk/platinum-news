# Platinum News Bot

Менеджер новостей для телеграм-канала и функция предложки

# Команды администратора

![](data/screenshots/img.png)

При запуске бота отправляется стартовое сообщение и доступна клавиатура с 4 кнопками.

## Посмотреть новости

![](data/screenshots/img2.png)

При выборе данной кнопки администратор может просматривать новости, хранящиеся в базе данных. Сообщение отображает
вложения, а также текст новости.

Кнопки инлайн клавиатуры:

* Стрелки влево-вправо нужны для выбора новостей
* Кнопка с галочкой запостит новость в канал и удалит ее из базы данных
* При нажатии кнопки с карандашом, администратор может ввести новый текст новости, после чего новость будет отправлена в
  канал
* При нажатии кнопки профиля, можно просмотреть информацию об авторе новости, забанить его или удалить все предложенные
  им новости
* Нижняя кнопка возвращает в главное меню

![](data/screenshots/img3.png)
> Профиль автора новости

## Сделать шаблон постов

При выборе этой кнопки администратор может задать заголовок и нижнюю часть для своих постов

![](data/screenshots/img4.png)
![](data/screenshots/img5.png)

## Найти новости

При выборе этой кнопки администратор может найти новости на английском или на русском языке,
используя [News API](https://newsapi.org/).

![](data/screenshots/img6.png)
![](data/screenshots/img7.png)

## Очистить предложку

Кнопка очищает базу данных новостей

# Команды пользователя

![](data/screenshots/img8.png)

## Предложить новость

Команда позволяет отправить новость администратору

![](data/screenshots/img9.png)

## Профиль

Команда показывает информацию о профиле пользователя

![](data/screenshots/img10.png)

# Текстовые команды

## /ban @username

Банит пользователя с юзернеймом @username

## /unban @username

Разбан пользователя с юзернеймом @username

## /change_perm

Функция для тестирования бота - меняет права на пользователя или на админа