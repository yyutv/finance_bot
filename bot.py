import telebot
from telebot import types
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Токен бота
TOKEN = '8319214595:AAFWD3Qpqdir5hu55YTnPnT53EoBnoF02-w'
bot = telebot.TeleBot(TOKEN)

# Подключение к PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ОШИБКА: DATABASE_URL не задана!")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    print("✅ Подключение к БД успешно")
except Exception as e:
    print(f"❌ Ошибка подключения к БД: {e}")
    exit(1)

# Создаём таблицы
try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        name TEXT,
        created_at TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount REAL,
        category TEXT,
        date TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        user_id BIGINT PRIMARY KEY,
        goal_name TEXT,
        goal_amount REAL
    )
    ''')
    conn.commit()
    print("✅ Таблицы созданы")
except Exception as e:
    print(f"❌ Ошибка создания таблиц: {e}")
    conn.close()
    exit(1)

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    name = message.from_user.first_name
    
    try:
        # Проверяем существует ли пользователь
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, name, created_at) VALUES (%s, %s, %s)",
                (user_id, name, datetime.now())
            )
            conn.commit()
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        conn.rollback()
    
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

# Обработка сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    user_id = message.chat.id
    
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
    elif text.startswith('+'):
        try:
            parts = text[1:].split(maxsplit=1)
            amount = float(parts[0])
            desc = parts[1] if len(parts) > 1 else 'доход'
            
            cursor.execute(
                "INSERT INTO transactions (user_id, amount, category, date) VALUES (%s, %s, %s, %s)",
                (user_id, amount, desc, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            bot.send_message(user_id, f"✅ Записал: +{amount} руб. ({desc})")
            check_goal_progress(user_id)
        except Exception as e:
            bot.send_message(user_id, "❌ Ошибка. Пример: +500 стипендия")
            print(f"Ошибка: {e}")
            conn.rollback()
    elif text.startswith('-'):
        try:
            parts = text[1:].split(maxsplit=1)
            amount = float(parts[0])
            desc = parts[1] if len(parts) > 1 else 'расход'
            
            cursor.execute(
                "INSERT INTO transactions (user_id, amount, category, date) VALUES (%s, %s, %s, %s)",
                (user_id, -amount, desc, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            bot.send_message(user_id, f"✅ Записал: -{amount} руб. ({desc})")
            check_goal_progress(user_id)
        except Exception as e:
            bot.send_message(user_id, "❌ Ошибка. Пример: -300 обед")
            print(f"Ошибка: {e}")
            conn.rollback()

def add_income(message):
    user_id = message.chat.id
    text = message.text
    try:
        parts = text.split(maxsplit=1)
        amount = float(parts[0])
        desc = parts[1] if len(parts) > 1 else 'доход'
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, category, date) VALUES (%s, %s, %s, %s)",
            (user_id, amount, desc, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        bot.send_message(user_id, f"✅ Записал: +{amount} руб. ({desc})")
        check_goal_progress(user_id)
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка. Пример: 500 стипендия")
        print(f"Ошибка: {e}")
        conn.rollback()

def add_expense(message):
    user_id = message.chat.id
    text = message.text
    try:
        parts = text.split(maxsplit=1)
        amount = float(parts[0])
        desc = parts[1] if len(parts) > 1 else 'расход'
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, category, date) VALUES (%s, %s, %s, %s)",
            (user_id, -amount, desc, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        bot.send_message(user_id, f"✅ Записал: -{amount} руб. ({desc})")
        check_goal_progress(user_id)
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка. Пример: 300 обед")
        print(f"Ошибка: {e}")
        conn.rollback()

def show_stats(user_id):
    try:
        cursor.execute("SELECT amount, category FROM transactions WHERE user_id = %s", (user_id,))
        transactions = cursor.fetchall()
        
        if not transactions:
            bot.send_message(user_id, "Пока нет записей. Добавь доходы и расходы!")
            return
        
        total_income = 0
        total_expense = 0
        expenses = {}
        
        for t in transactions:
            if t['amount'] > 0:
                total_income += t['amount']
            else:
                total_expense += abs(t['amount'])
                cat = t['category']
                expenses[cat] = expenses.get(cat, 0) + abs(t['amount'])
        
        balance = total_income - total_expense
        
        text = f"📊 Твоя статистика:\n\n"
        text += f"💰 Всего доходов: {total_income:.0f} руб.\n"
        text += f"💸 Всего расходов: {total_expense:.0f} руб.\n"
        text += f"💎 Текущий баланс: {balance:.0f} руб.\n\n"
        
        if expenses:
            text += "Куда уходят деньги:\n"
            sorted_expenses = sorted(expenses.items(), key=lambda x: x[1], reverse=True)
            for cat, amount in sorted_expenses:
                percent = (amount / total_expense) * 100
                text += f"• {cat}: {amount:.0f} руб. ({percent:.0f}%)\n"
        
        bot.send_message(user_id, text)
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при получении статистики")
        print(f"Ошибка в show_stats: {e}")

def ask_goal(user_id):
    try:
        cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = %s", (user_id,))
        goal = cursor.fetchone()
        
        if goal:
            goal_name = goal['goal_name']
            goal_amount = goal['goal_amount']
            cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            balance = result['total'] if result else 0
            
            if balance >= goal_amount:
                text = f"🎉 Ты уже накопил на {goal_name}! Поздравляю!"
            else:
                remaining = goal_amount - balance
                percent = (balance / goal_amount) * 100
                text = (f"🎯 Твоя цель: {goal_name}\n"
                       f"💰 Нужно: {goal_amount:.0f} руб.\n"
                       f"💎 Осталось: {remaining:.0f} руб.\n"
                       f"📈 Прогресс: {percent:.1f}%")
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Новая цель", callback_data="new_goal"))
            markup.add(types.InlineKeyboardButton("🔮 Прогноз", callback_data="forecast"))
            
            bot.send_message(user_id, text, reply_markup=markup)
        else:
            msg = bot.send_message(
                user_id,
                "Какая у тебя цель?\nНапиши название и сумму через пробел\nНапример: Айфон 30000"
            )
            bot.register_next_step_handler(msg, set_goal)
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка")
        print(f"Ошибка в ask_goal: {e}")

def set_goal(message):
    user_id = message.chat.id
    text = message.text
    try:
        parts = text.rsplit(maxsplit=1)
        goal_name = parts[0]
        goal_amount = float(parts[1])
        
        # Проверяем есть ли уже цель
        cursor.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute(
                "UPDATE goals SET goal_name = %s, goal_amount = %s WHERE user_id = %s",
                (goal_name, goal_amount, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO goals (user_id, goal_name, goal_amount) VALUES (%s, %s, %s)",
                (user_id, goal_name, goal_amount)
            )
        conn.commit()
        bot.send_message(user_id, f"✅ Цель '{goal_name}' на {goal_amount:.0f} руб. сохранена!")
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка. Пример: Айфон 30000")
        print(f"Ошибка в set_goal: {e}")
        conn.rollback()

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

def check_goal_progress(user_id):
    try:
        cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = %s", (user_id,))
        goal = cursor.fetchone()
        
        if goal:
            goal_name = goal['goal_name']
            goal_amount = goal['goal_amount']
            cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            balance = result['total'] if result else 0
            
            if balance >= goal_amount:
                bot.send_message(
                    user_id,
                    f"🎉🎉🎉 УРА! Ты накопил на {goal_name}! Поздравляю! 🎉🎉🎉"
                )
    except Exception as e:
        print(f"Ошибка в check_goal_progress: {e}")

def make_forecast(user_id):
    try:
        cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = %s", (user_id,))
        goal = cursor.fetchone()
        
        if not goal:
            bot.send_message(user_id, "Сначала поставь цель в разделе 🎯 Моя цель")
            return
        
        goal_name = goal['goal_name']
        goal_amount = goal['goal_amount']
        
        cursor.execute("SELECT amount FROM transactions WHERE user_id = %s AND amount > 0", (user_id,))
        incomes_rows = cursor.fetchall()
        incomes = [row['amount'] for row in incomes_rows]
        
        cursor.execute("SELECT amount FROM transactions WHERE user_id = %s AND amount < 0", (user_id,))
        expenses_rows = cursor.fetchall()
        expenses = [abs(row['amount']) for row in expenses_rows]
        
        if len(incomes) < 3:
            bot.send_message(user_id, "Нужно больше данных для прогноза. Добавь ещё доходов!")
            return
        
        avg_income = sum(incomes) / len(incomes)
        avg_expense = sum(expenses) / len(expenses) if expenses else 0
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        balance = result['total'] if result else 0
        
        remaining = goal_amount - balance
        
        if remaining <= 0:
            bot.send_message(user_id, f"🎉 Ты уже накопил на {goal_name}!")
            return
        
        monthly_saving = avg_income - avg_expense
        
        if monthly_saving <= 0:
            bot.send_message(user_id, "⚠️ Ты тратишь больше, чем получаешь. Сначала сократи расходы!")
            return
        
        months = remaining / monthly_saving
        
        if len(incomes) > 5 and expenses:
            variations = []
            for _ in range(100):
                sim_balance = balance
                sim_months = 0
                while sim_balance < goal_amount and sim_months < 60:
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
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при прогнозе")
        print(f"Ошибка в make_forecast: {e}")

def run_experiment(user_id):
    try:
        cursor.execute("SELECT goal_name, goal_amount FROM goals WHERE user_id = %s", (user_id,))
        goal = cursor.fetchone()
        
        if not goal:
            bot.send_message(user_id, "Сначала поставь цель в разделе 🎯 Моя цель")
            return
        
        goal_name = goal['goal_name']
        goal_amount = goal['goal_amount']
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        balance = result['total'] if result else 0
        
        cursor.execute("SELECT amount FROM transactions WHERE user_id = %s AND amount > 0", (user_id,))
        incomes_rows = cursor.fetchall()
        incomes = [row['amount'] for row in incomes_rows]
        avg_income = sum(incomes) / len(incomes) if incomes else 0
        
        cursor.execute("SELECT amount FROM transactions WHERE user_id = %s AND amount < 0", (user_id,))
        expenses_rows = cursor.fetchall()
        expenses = [abs(row['amount']) for row in expenses_rows]
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
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка")
        print(f"Ошибка в run_experiment: {e}")

def show_experiment_result(message, goal_name, goal_amount, balance):
    try:
        user_id = message.chat.id
        parts = message.text.split()
        new_income = float(parts[0])
        new_expense = float(parts[1])

        remaining = goal_amount - balance
        monthly_saving = new_income - new_expense

        if monthly_saving <= 0:
            bot.send_message(user_id, "❌ При таких расходах ты ничего не отложишь!")
            return

        new_months = remaining / monthly_saving

        cursor.execute("SELECT amount FROM transactions WHERE user_id = %s AND amount > 0", (user_id,))
        incomes_rows = cursor.fetchall()
        incomes = [row['amount'] for row in incomes_rows]
        
        cursor.execute("SELECT amount FROM transactions WHERE user_id = %s AND amount < 0", (user_id,))
        expenses_rows = cursor.fetchall()
        expenses = [abs(row['amount']) for row in expenses_rows]

        current_income = sum(incomes) / len(incomes) if incomes else 0
        current_expense = sum(expenses) / len(expenses) if expenses else 0
        current_saving = current_income - current_expense

        if current_saving > 0:
            current_months = f"{remaining / current_saving:.1f} мес."
            diff = (remaining / current_saving) - new_months

            if diff > 0:
                compare = f"🚀 Быстрее на {diff:.1f} мес."
            else:
                compare = f"⏰ Медленнее на {abs(diff):.1f} мес."
        else:
            current_months = "❌ не получается (тратишь больше, чем получаешь)"
            compare = "✅ теперь получится!"

        text = (f"📊 РЕЗУЛЬТАТ ЭКСПЕРИМЕНТА:\n\n"
                f"💰 Доход: {new_income:.0f} руб./мес\n"
                f"💸 Расход: {new_expense:.0f} руб./мес\n"
                f"💎 Откладываешь: {monthly_saving:.0f} руб./мес\n\n"
                f"🎯 Цель: {goal_name}\n"
                f"⏳ Осталось: {remaining:.0f} руб.\n\n"
                f"⏱ СРОК НАКОПЛЕНИЯ:\n"
                f"• Сейчас: {current_months}\n"
                f"• Если изменить: {new_months:.1f} мес.\n\n"
                f"{compare}")

        bot.send_message(user_id, text)

    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка. Пиши так: 30000 20000")
        print(f"Ошибка в show_experiment_result: {e}")

# Сервер здоровья для Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('', port), HealthCheckHandler)
    print(f"✅ Сервер здоровья запущен на порту {port}")
    server.serve_forever()

# Запускаем сервер в отдельном потоке
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# Запуск бота
print("🚀 Бот запускается...")
print("🤖 Бот готов к работе! Иди в Telegram и пиши /start")

# Бесконечный цикл с обработкой ошибок
while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Ошибка бота: {e}")
        print("🔄 Перезапуск через 5 секунд...")
        time.sleep(5)
