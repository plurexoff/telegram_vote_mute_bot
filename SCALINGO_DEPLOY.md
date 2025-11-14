# Инструкция по деплою на Scalingo

## Что такое Scalingo?

Scalingo - европейская PaaS-платформа для хостинга приложений. Предлагает бесплатный 30-дневный trial без привязки карты.

## Шаг 1: Регистрация на Scalingo

1. Перейдите на https://scalingo.com
2. Нажмите "Free Trial" в правом верхнем углу
3. Зарегистрируйтесь через email или GitHub
4. Подтвердите email

## Шаг 2: Установка Scalingo CLI

### Linux & macOS:
```bash
curl -O https://cli-dl.scalingo.com/install && bash install
```

### Windows (через Git Bash):
1. Скачайте scalingo.exe с https://cli-dl.scalingo.com/release/scalingo_latest_windows_amd64.zip
2. Распакуйте в удобную папку (например, C:\Program Files)
3. Добавьте путь в PATH:
```bash
export PATH=$PATH:/c/Program\ Files/
echo "export PATH=$PATH:/c/Program\ Files/" >> $HOME/.bashrc
```

## Шаг 3: Вход в Scalingo CLI

```bash
scalingo login
```

Введите email и пароль от аккаунта Scalingo.

## Шаг 4: Подготовка проекта

1. Распакуйте архив `telegram_vote_mute_bot.zip`
2. Откройте терминал в папке проекта
3. Инициализируйте Git репозиторий (если ещё не инициализирован):

```bash
git init
git add .
git commit -m "Initial commit"
```

## Шаг 5: Создание приложения на Scalingo

```bash
scalingo create my-telegram-bot --region osc-fr1
```

Где:
- `my-telegram-bot` - название вашего приложения (можно изменить)
- `--region osc-fr1` - регион (европейский дата-центр во Франции)

## Шаг 6: Настройка переменных окружения

Добавьте токен вашего Telegram-бота:

```bash
scalingo --app my-telegram-bot env-set BOT_TOKEN="ваш_токен_от_BotFather"
```

Где получить токен:
1. Откройте Telegram
2. Найдите @BotFather
3. Отправьте `/newbot`
4. Следуйте инструкциям
5. Скопируйте полученный токен

## Шаг 7: Деплой приложения

```bash
git push scalingo master
```

Или если ваша основная ветка называется `main`:
```bash
git push scalingo main:master
```

## Шаг 8: Проверка работы

1. Дождитесь завершения деплоя (в терминале появится сообщение об успешном деплое)
2. Проверьте логи:
```bash
scalingo --app my-telegram-bot logs --lines 100
```

3. Проверьте статус:
```bash
scalingo --app my-telegram-bot ps
```

## Шаг 9: Масштабирование (если нужно)

По умолчанию запускается 1 контейнер. Если нужно больше:

```bash
scalingo --app my-telegram-bot scale web:1:M
```

## Важные моменты

### Бесплатный trial
- Длительность: 30 дней
- Лимит: 1 приложение, максимум 5 контейнеров (S или M размера)
- Приложение будет удалено через 30 дней бездействия после окончания trial
- НЕ требуется привязка карты

### Права бота в группе
Для работы функции мьюта бот должен:
1. Быть добавлен в группу
2. Иметь права администратора
3. Иметь право "Restrict members" (ограничивать участников)

### Обновление бота

Когда вы внесли изменения в код:

```bash
git add .
git commit -m "Описание изменений"
git push scalingo master
```

## Полезные команды

```bash
# Просмотр логов в реальном времени
scalingo --app my-telegram-bot logs -f

# Перезапуск приложения
scalingo --app my-telegram-bot restart

# Просмотр переменных окружения
scalingo --app my-telegram-bot env

# Открыть dashboard в браузере
scalingo --app my-telegram-bot dashboard

# Удалить приложение
scalingo --app my-telegram-bot destroy
```

## Альтернативный способ деплоя (через GitHub)

1. Создайте репозиторий на GitHub
2. Загрузите туда код
3. В dashboard Scalingo:
   - Перейдите в раздел "Code"
   - Выберите "Link with GitHub"
   - Выберите ваш репозиторий
   - Включите Auto Deploy

## Troubleshooting

### Ошибка "Application crashed"
Проверьте логи: `scalingo --app my-telegram-bot logs`

### Бот не отвечает
1. Проверьте, что токен правильно установлен: `scalingo --app my-telegram-bot env`
2. Убедитесь, что процесс запущен: `scalingo --app my-telegram-bot ps`

### "Permission denied" при мьюте
Убедитесь, что бот:
- Является администратором группы
- Имеет право "Restrict members"

## Дополнительные ресурсы

- Документация Scalingo: https://doc.scalingo.com
- Документация aiogram: https://docs.aiogram.dev
- Telegram Bot API: https://core.telegram.org/bots/api

---

При возникновении проблем обращайтесь в поддержку Scalingo или проверяйте логи приложения.
