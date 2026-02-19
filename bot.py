import telebot
from telebot import types
import sqlite3
from datetime import datetime
import random

# Токен бота (вставь свой от @BotFather)
TOKEN = '8319214595:AAFWD3Qpqdir5hu55YTnPnT53EoBnoF02-w'
bot = telebot.TeleBot(TOKEN)

# Подключаемся к базе данных
conn = sqlite3.connect('finance.db', check_same_thread=False)
cursor = conn.cursor()

# Создаём таблицы
# Создаём таблицы
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    created_at TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT,
    date TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS goals (
    user_id INTEGER PRIMARY KEY,
    goal_name TEXT,
    goal_amount REAL
)''')

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    name = message.from_user.first_name
    
    # Добавляем пользователя в базу
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, created_at) VALUES (?, ?, ?)",
                  (user_id, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    
    # Создаём кнопки
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('➕ Доход', '➖ Расход')
    markup.add('📊 Статистика', '🎯 Моя цель')
    markup.add('🔮 Прогноз', '🧪 Что если...')
    
    bot.send_message(
        user_id,
        f"Привет, {name}! 👋\n\n"
        "Я помогу следить за деньгами.\n\n"
        "📝 Как писать:\n"
        "• Доход: +500 стипендия\n"
        "• Расход: -300 обед\n\n"
        "Или просто жми кнопки!",
        reply_markup=markup
    )

# Обработка всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    user_id = message.chat.id
    
    # Кнопки
    if text == '➕ Доход':
        msg = bot.send_message(user_id, "Сколько и откуда?\nНапример: 500 стипендия")
        bot.register_next_step_handler(msg, add_income)
        
    elif text == '➖ Расход':
        msg = bot.send_message(user_id, "Сколько и на что?\nНапример: 300 обед")
        bot.register_next_step_handler(msg, add_expense)
        
    elif text == '📊 Статистика':
        show_stats(user_id)
        
    elif text == '🎯 Моя цель':
        ask_goal(user_id)
        
    elif text == '🔮 Прогноз':
        make_forecast(user_id)
        
    elif text == '🧪 Что если...':
        run_experiment(user_id)
        
    # Автоматическое распознавание
    elif text.startswith('+'):
        try:
            parts = text[1:].split(maxsplit=1)
            amount = float(parts[0])
            desc = parts[1] if len(parts) > 1 else 'доход'
            
            cursor.execute(
                "INSERT INTO transactions (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (user_id, amount, desc, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            
            bot.send_message(user_id, f"✅ Записал: +{amount} руб. ({desc})")
            check_goal_progress(user_id)
            
        except:
            bot.send_message(user_id, "❌ Что-то не так. Попробуй: +500 стипендия")
            
    elif text.startswith('-'):
        try:
            parts = text[1:].split(maxsplit=1)
            amount = float(parts[0])
            desc = parts[1] if len(parts) > 1 else 'расход'
            
            cursor.execute(
                "INSERT INTO transactions (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (user_id, -amount, desc, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            
            bot.send_message(user_id, f"✅ Записал: -{amount} руб. ({desc})")
            check_goal_progress(user_id)
            
        except:
            bot.send_message(user_id, "❌ Что-то не так. Попробуй: -300 обед")

# Добавление дохода через кнопку
def add_income(message):
    user_id = message.chat.id
    text = message.text
    
    try:
        parts = text.split(maxsplit=1)
        amount = float(parts[0])
        desc = parts[1] if len(parts) > 1 else 'доход'
        
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (user_id, amount, desc, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        
        bot.send_message(user_id, f"✅ Записал: +{amount} руб. ({desc})")
        check_goal_progress(user_id)
        
    except:
        bot.send_message(user_id, "❌ Ошибка. Пиши так: 500 стипендия")

# Добавление расхода через кнопку
def add_expense(message):
    user_id = message.chat.id
    text = message.text
    
    try:
        parts = text.split(maxsplit=1)
        amount = float(parts[0])
        desc = parts[1] if len(parts) > 1 else 'расход'
        
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (user_id, -amount, desc, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        
        bot.send_message(user_id, f"✅ Записал: -{amount} руб. ({desc})")
        check_goal_progress(user_id)
        
    except:
        bot.send_message(user_id, "❌ Ошибка. Пиши так: 300 обед")

# Статистика
def show_stats(user_id):
    # Получаем все транзакции
    cursor.execute("SELECT amount, category FROM transactions WHERE user_id = ?", (user_id,))
    transactions = cursor.fetchall()
    
    if not transactions:
        bot.send_message(user_id, "Пока нет записей. Добавь доходы и расходы!")
        return
    
    # Считаем общие суммы
    total_income = sum(t[0] for t in transactions if t[0] > 0)
    total_expense = sum(abs(t[0]) for t in transactions if t[0] < 0)
    balance = total_income - total_expense
    
    # Группируем расходы по категориям
    expenses = {}
    for t in transactions:
        if t[0] < 0:
            cat = t[1]
            expenses[cat] = expenses.get(cat, 0) + abs(t[0])
    
    # Формируем текст
    text = f"📊 Твоя статистика:\n\n"
    text += f"💰 Всего доходов: {total_income:.0f} руб.\n"
    text += f"💸 Всего расходов: {total_expense:.0f} руб.\n"
    text += f"💎 Текущий баланс: {balance:.0f} руб.\n\n"
    
    if expenses:
        text += "Куда уходят деньги:\n"
        # Сортируем по убыванию
        sorted_expenses = sorted(expenses.items(), key=lambda x: x[1], reverse=True)
        for cat, amount in sorted_expenses:
            percent = (amount / total_expense) * 100
            text += f"• {cat}: {amount:.0f} руб. ({percent:.0f}%)\n"
    
    bot.send_message(user_id, text)

# Установка цели
def ask_goal(user_id):
    cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = ?", (user_id,))
    goal = cursor.fetchone()
    
    if goal:
        # Показываем текущую цель
        goal_name, goal_amount = goal
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0] or 0
        
        if balance >= goal_amount:
            text = f"🎉 Ты уже накопил на {goal_name}! Поздравляю!"
        else:
            remaining = goal_amount - balance
            percent = (balance / goal_amount) * 100
            text = (f"🎯 Твоя цель: {goal_name}\n"
                   f"💰 Нужно: {goal_amount:.0f} руб.\n"
                   f"💎 Осталось: {remaining:.0f} руб.\n"
                   f"📈 Прогресс: {percent:.1f}%")
        
        # Кнопки для управления
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Новая цель", callback_data="new_goal"))
        markup.add(types.InlineKeyboardButton("🔮 Прогноз", callback_data="forecast"))
        
        bot.send_message(user_id, text, reply_markup=markup)
        
    else:
        # Спрашиваем новую цель
        msg = bot.send_message(
            user_id,
            "Какая у тебя цель?\nНапиши название и сумму через пробел\nНапример: Айфон 30000"
        )
        bot.register_next_step_handler(msg, set_goal)

def set_goal(message):
    user_id = message.chat.id
    text = message.text
    
    try:
        # Отделяем последнее слово (сумму)
        parts = text.rsplit(maxsplit=1)
        goal_name = parts[0]
        goal_amount = float(parts[1])
        
        cursor.execute(
            "INSERT OR REPLACE INTO goals (user_id, goal_name, goal_amount) VALUES (?, ?, ?)",
            (user_id, goal_name, goal_amount)
        )
        conn.commit()
        
        bot.send_message(user_id, f"✅ Цель '{goal_name}' на {goal_amount:.0f} руб. сохранена!")
        
    except:
        bot.send_message(user_id, "❌ Ошибка. Пиши так: Айфон 30000")

# Обработка кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    
    if call.data == "new_goal":
        msg = bot.send_message(
            user_id,
            "Напиши новую цель (название и сумму):\nНапример: Макбук 80000"
        )
        bot.register_next_step_handler(msg, set_goal)
        
    elif call.data == "forecast":
        make_forecast(user_id)

# Проверка прогресса цели
def check_goal_progress(user_id):
    cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = ?", (user_id,))
    goal = cursor.fetchone()
    
    if goal:
        goal_name, goal_amount = goal
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0] or 0
        
        if balance >= goal_amount:
            bot.send_message(
                user_id,
                f"🎉🎉🎉 УРА! Ты накопил на {goal_name}! Поздравляю! 🎉🎉🎉"
            )

# Простой прогноз
def make_forecast(user_id):
    cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = ?", (user_id,))
    goal = cursor.fetchone()
    
    if not goal:
        bot.send_message(user_id, "Сначала поставь цель в разделе 🎯 Моя цель")
        return
    
    goal_name, goal_amount = goal
    
    # Считаем средний доход и расход
    cursor.execute("SELECT amount FROM transactions WHERE user_id = ? AND amount > 0", (user_id,))
    incomes = [i[0] for i in cursor.fetchall()]
    
    cursor.execute("SELECT amount FROM transactions WHERE user_id = ? AND amount < 0", (user_id,))
    expenses = [abs(e[0]) for e in cursor.fetchall()]
    
    if len(incomes) < 3:
        bot.send_message(user_id, "Нужно больше данных для прогноза. Добавь ещё доходов!")
        return
    
    avg_income = sum(incomes) / len(incomes)
    avg_expense = sum(expenses) / len(expenses) if expenses else 0
    
    # Текущий баланс
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0] or 0
    
    remaining = goal_amount - balance
    
    if remaining <= 0:
        bot.send_message(user_id, f"🎉 Ты уже накопил на {goal_name}!")
        return
    
    monthly_saving = avg_income - avg_expense
    
    if monthly_saving <= 0:
        bot.send_message(user_id, "⚠️ Ты тратишь больше, чем получаешь. Сначала сократи расходы!")
        return
    
    # Простой прогноз
    months = remaining / monthly_saving
    
    # Простой вероятностный прогноз
    if len(incomes) > 5:
        # Считаем разброс доходов
        variations = []
        for _ in range(100):
            sim_balance = balance
            sim_months = 0
            while sim_balance < goal_amount and sim_months < 60:
                # Случайный доход из истории
                rand_income = random.choice(incomes)
                rand_expense = random.choice(expenses) if expenses else avg_expense
                sim_balance += rand_income - rand_expense
                sim_months += 1
            if sim_balance >= goal_amount:
                variations.append(sim_months)
        
        if variations:
            avg_months = sum(variations) / len(variations)
            text = (f"🔮 Прогноз для '{goal_name}':\n\n"
                   f"💰 Осталось: {remaining:.0f} руб.\n"
                   f"📊 В месяц откладываешь: {monthly_saving:.0f} руб.\n\n"
                   f"По простому расчёту: {months:.1f} мес.\n"
                   f"С учётом случайностей: ~{avg_months:.1f} мес.")
        else:
            text = (f"🔮 Прогноз для '{goal_name}':\n\n"
                   f"💰 Осталось: {remaining:.0f} руб.\n"
                   f"📊 В месяц откладываешь: {monthly_saving:.0f} руб.\n"
                   f"Нужно примерно: {months:.1f} мес.")
    else:
        text = (f"🔮 Прогноз для '{goal_name}':\n\n"
               f"💰 Осталось: {remaining:.0f} руб.\n"
               f"📊 В месяц откладываешь: {monthly_saving:.0f} руб.\n"
               f"Нужно примерно: {months:.1f} мес.\n\n"
               f"(Добавь больше записей для точного прогноза)")
    
    bot.send_message(user_id, text)

# Эксперимент "Что если..."
def run_experiment(user_id):
    cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = ?", (user_id,))
    goal = cursor.fetchone()
    
    if not goal:
        bot.send_message(user_id, "Сначала поставь цель в разделе 🎯 Моя цель")
        return
    
    goal_name, goal_amount = goal
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0] or 0
    
    # Считаем текущие средние
    cursor.execute("SELECT amount FROM transactions WHERE user_id = ? AND amount > 0", (user_id,))
    incomes = [i[0] for i in cursor.fetchall()]
    avg_income = sum(incomes) / len(incomes) if incomes else 0
    
    cursor.execute("SELECT amount FROM transactions WHERE user_id = ? AND amount < 0", (user_id,))
    expenses = [abs(e[0]) for e in cursor.fetchall()]
    avg_expense = sum(expenses) / len(expenses) if expenses else 0
    
    msg = bot.send_message(
        user_id,
        f"🧪 Эксперимент с целью '{goal_name}'\n\n"
        f"Сейчас ты получаешь ~{avg_income:.0f} руб./мес\n"
        f"Тратишь ~{avg_expense:.0f} руб./мес\n"
        f"Накоплено: {balance:.0f} из {goal_amount:.0f} руб.\n\n"
        f"Что если изменить?\n"
        f"Напиши новый доход и расход через пробел\n"
        f"Например: 30000 20000"
    )
    
    bot.register_next_step_handler(msg, show_experiment_result, goal_name, goal_amount, balance)

def show_experiment_result(message, goal_name, goal_amount, balance):
    user_id = message.chat.id
    
    try:
        parts = message.text.split()
        new_income = float(parts[0])
        new_expense = float(parts[1])
        
        remaining = goal_amount - balance
        monthly_saving = new_income - new_expense
        
        if monthly_saving <= 0:
            bot.send_message(user_id, "❌ При таких расходах ты ничего не отложишь!")
            return
        
        new_months = remaining / monthly_saving
        
        # Текущий прогноз для сравнения
        cursor.execute("SELECT amount FROM transactions WHERE user_id = ? AND amount > 0", (user_id,))
        incomes = [i[0] for i in cursor.fetchall()]
        cursor.execute("SELECT amount FROM transactions WHERE user_id = ? AND amount < 0", (user_id,))
        expenses = [abs(e[0]) for e in cursor.fetchall()]
        
        current_income = sum(incomes) / len(incomes) if incomes else 0
        current_expense = sum(expenses) / len(expenses) if expenses else 0
        current_saving = current_income - current_expense
        
                if current_saving > 0:
            current_months = remaining / current_saving
            diff = current_months - new_months
            
            if diff > 0:
                compare = f"Быстрее на {diff:.1f} мес. 🚀"
            else:
                compare = f"Медленнее на {abs(diff):.1f} мес. ⏰"
        else:
            current_months = "никогда"
            compare = "раньше, чем сейчас 👍"
        
        text = (f"📊 Результат:\n\n"
               f"Сейчас ты копил бы: {current_months:.1f} мес.\n"
               f"Если изменить: {new_months:.1f} мес.\n"
               f"Итог: {compare}")
        
        bot.send_message(user_id, text)
        
    except:
        bot.send_message(user_id, "❌ Ошибка. Пиши так: 30000 20000")

# Запуск бота
print("Бот запущен...")

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('', port), HealthCheckHandler)
    print(f"Сервер здоровья запущен на порту {port}")
    server.serve_forever()

# Запускаем сервер в отдельном потоке
threading.Thread(target=run_health_server, daemon=True).start()

# Запускаем бота
bot.infinity_polling()
