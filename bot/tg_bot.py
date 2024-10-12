import paramiko
import psycopg2
import logging
import subprocess
import re
from dotenv import load_dotenv
import os
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

load_dotenv()

TOKEN = os.getenv('TOKEN')

SSH_HOST = os.getenv('RM_HOST')
SSH_PORT = os.getenv('RM_PORT')
SSH_USERNAME = os.getenv('RM_USERNAME')
SSH_PASSWORD = os.getenv('RM_PASSWORD')

DB_DATABASE = os.getenv('DB_DATABASE')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')  
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

version = os.getenv('POSTGRES_VERSION')

PASSWORD_CHECK = 1

LOG_FILE_PATH = "/var/log/postgresql/postgresql.log"

phoneNumberList = []
emailAddrList = []

# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')

def helpCommand(update: Update, context):
    update.message.reply_text('Help!')

def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'findPhoneNumbers'

def findPhoneNumbers (update: Update, context):
    user_input = update.message.text # Получаем текст, содержащий(или нет) номера телефонов

    phoneNumRegex = re.compile(r'(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}') # формат 8 (000) 000-00-00

    global phoneNumberList

    phoneNumberList = phoneNumRegex.findall(user_input) # Ищем номера телефонов

    if not phoneNumberList: # Обрабатываем случай, когда номеров телефонов нет
        update.message.reply_text('Телефонные номера не найдены')
        return # Завершаем выполнение функции
    
    phoneNumbers = '' # Создаем строку, в которую будем записывать номера телефонов
    for i in range(len(phoneNumberList)):
        phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n' # Записываем очередной номер
        
    update.message.reply_text(phoneNumbers) # Отправляем сообщение пользователю
    
    update.message.reply_text("Записать найденные телефонные номера в базу данных?")
    return 'save_phone_number_to_db'

def findEmailAddrCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска электронных почт: ')

    return 'findEmailAddr'

def findEmailAddr (update: Update, context):
    user_input = update.message.text # Получаем текст

    emailAddrRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b') 

    global emailAddrList

    emailAddrList = emailAddrRegex.findall(user_input) # Ищем Email-адреса

    if not emailAddrList: # Обрабатываем случай, когда Email-адресов нет
        update.message.reply_text('Email-адреса не найдены')
        return  # Завершаем выполнение функции
    
    emailAddr = '' # Создаем строку, в которую будем записывать Email-адреса
    for i in range(len(emailAddrList)):
        emailAddr += f'{i+1}. {emailAddrList[i]}\n' # Записываем очередной Email-адрес

    update.message.reply_text('Найденные Email-адреса: ')    
    update.message.reply_text(emailAddr) # Отправляем сообщение пользователю
    
    update.message.reply_text("Записать найденные Email-адреса в базу данных?")
    return 'save_email_to_db'

# Регулярное выражение для проверки сложности пароля
def is_password_strong(password: str) -> bool:
    password_regex = re.compile(
        r'^(?=.*[A-Z])'        # Хотя бы одна заглавная буква
        r'(?=.*[a-z])'         # Хотя бы одна строчная буква
        r'(?=.*\d)'            # Хотя бы одна цифра
        r'(?=.*[@$!%*?&])'     # Хотя бы один специальный символ
        r'[A-Za-z\d@$!%*?&]'   # Ограничиваем разрешенные символы
        r'{8,}$'               # Минимум 8 символов
    )
    return bool(password_regex.match(password))

# Команда для запроса пароля
def verifyPasswordCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Введите пароль для проверки сложности:')
    return PASSWORD_CHECK

# Функция для проверки пароля
def verifyPassword(update: Update, context: CallbackContext):
    user_input = update.message.text  # Получаем введенный пароль

    # Проверяем сложность пароля
    if is_password_strong(user_input):
        update.message.reply_text('Пароль сложный.')
    else:
        update.message.reply_text('Пароль простой.')
    
    return ConversationHandler.END

# Функция для завершения диалога
#def cancel(update: Update, context: CallbackContext):
    #update.message.reply_text('Проверка отменена.')
    #return ConversationHandler.END

def ssh_command(command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, password=SSH_PASSWORD)
        
        stdin, stdout, stderr = client.exec_command(command)
        result = stdout.read().decode('utf-8').strip()  # Читаем результат команды
        client.close()

        if result:
            return result
        else:
            return stderr.read().decode('utf-8').strip()

    except Exception as e:
        return f"Ошибка подключения: {str(e)}"

# Команда /get_release - получение информации о релизе
def get_release(update: Update, context: CallbackContext) -> None:
    release_info = ssh_command("cat /etc/os-release")
    update.message.reply_text(f"Информация о релизе:\n{release_info}")

# Команда /get_uname - информация об архитектуре, хосте и версии ядра
def get_uname(update: Update, context: CallbackContext) -> None:
    uname_info = ssh_command("uname -a")
    update.message.reply_text(f"Информация о системе:\n{uname_info}")

# Команда /get_uptime - информация о времени работы системы
def get_uptime(update: Update, context: CallbackContext) -> None:
    uptime_info = ssh_command("uptime -p")
    update.message.reply_text(f"Время работы системы:\n{uptime_info}")

# Команда /get_df - состояние файловой системы
def get_df(update: Update, context: CallbackContext) -> None:
    df_info = ssh_command("df -h")
    update.message.reply_text(f"Состояние файловой системы:\n{df_info}")

# Команда /get_free - информация о состоянии оперативной памяти
def get_free(update: Update, context: CallbackContext) -> None:
    free_info = ssh_command("free -h")
    update.message.reply_text(f"Состояние оперативной памяти:\n{free_info}")

# Команда /get_mpstat - информация о производительности системы
def get_mpstat(update: Update, context: CallbackContext) -> None:
    mpstat_info = ssh_command("mpstat")
    update.message.reply_text(f"Информация о производительности системы:\n{mpstat_info}")

# Команда /get_w - информация о текущих пользователях в системе
def get_w(update: Update, context: CallbackContext) -> None:
    w_info = ssh_command("w")
    update.message.reply_text(f"Информация о работающих пользователях:\n{w_info}")

# Команда /get_auths - последние 10 входов в систему
def get_auths(update: Update, context: CallbackContext) -> None:
    auths_info = ssh_command("last -n 10")
    update.message.reply_text(f"Последние 10 входов в систему:\n{auths_info}")

# Команда /get_critical - последние 5 критических событий
def get_critical(update: Update, context: CallbackContext) -> None:
    critical_info = ssh_command("journalctl -p crit -n 5")
    update.message.reply_text(f"Последние 5 критических событий:\n{critical_info}")

# Команда /get_ps - информация о запущенных процессах
def get_ps(update: Update, context: CallbackContext) -> None:
    ps_info = ssh_command("ps aux | head -n 10")
    update.message.reply_text(f"Список запущенных процессов:\n{ps_info}")

# Команда /get_ss - информация об используемых портах
def get_ss(update: Update, context: CallbackContext) -> None:
    ss_info = ssh_command("ss -tuln")
    update.message.reply_text(f"Используемые порты:\n{ss_info}")

# Команда /get_apt_list - информация об установленных пакетах (вариант 1: все пакеты)
def get_apt_list(update: Update, context: CallbackContext) -> None:
    apt_list = ssh_command("apt list --installed | head -n 20")
    update.message.reply_text(f"Список установленных пакетов:\n{apt_list}")

# Команда /get_apt_list_search - запрашивает пакет для поиска (вариант 2: конкретный пакет)
def get_apt_list_search(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Введите название пакета для поиска:")
    return 'search_package'

# Поиск конкретного пакета
def search_package(update: Update, context: CallbackContext) -> None:
    package_name = update.message.text
    search_result = ssh_command(f"apt list --installed | grep {package_name}")
    
    if search_result:
        update.message.reply_text(f"Информация о пакете {package_name}:\n{search_result}")
    else:
        update.message.reply_text(f"Пакет {package_name} не найден.")
    
    return ConversationHandler.END

# Команда /get_services - информация о запущенных сервисах
def get_services(update: Update, context: CallbackContext) -> None:
    services_info = ssh_command("systemctl list-units --type=service --state=running")
    update.message.reply_text(f"Запущенные сервисы:\n{services_info}")

def get_repl_logs(update: Update, context: CallbackContext) -> None:
    repl_info = ssh_command("tail -n 1000 /var/log/postgresql/postgresql-12-main.log | grep -i repl")
    update.message.reply_text(f"Запущенные сервисы:\n{repl_info}")

def connect_to_db():
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
            dbname=DB_DATABASE,  
            user=DB_USER, 
            password=DB_PASSWORD,  
            host=DB_HOST,  
            port=DB_PORT  
        )
        return connection
    except psycopg2.Error as e:
        print("Ошибка подключения к базе данных:", e)

# Функция для получения списка email-адресов из базы данных
def get_emails(update: Update, context):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("SELECT email FROM emails")  # Выборка email-адресов из таблицы emails
        emails = cursor.fetchall()
        if emails:
            email_list = "\n".join(email[0] for email in emails)
            update.message.reply_text("Email адреса:\n" + email_list)  # Отправка списка email-адресов пользователю
        else:
            update.message.reply_text("В базе данных нет email-адресов.")  # Если в базе нет email-адресов
    except psycopg2.Error as e:
        update.message.reply_text(f"Ошибка при получении электорнных почт из базы данных: {str(e)}")
    finally:
        cursor.close()
        connection.close()


# Функция для получения списка номеров телефонов из базы данных
def get_phone_numbers(update: Update, context):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("SELECT phone_number FROM phones")  # Выборка номеров телефонов из таблицы phone_numbers
        phone_numbers = cursor.fetchall()
        if phone_numbers:
            phone_number_list = "\n".join(phone_number[0] for phone_number in phone_numbers)
            update.message.reply_text("Телефонные номера:\n" + phone_number_list)  # Отправка списка номеров телефонов пользователю
        else:
            update.message.reply_text("В базе данных нет телефонных номеров.")  # Если в базе нет номеров телефонов
    except psycopg2.Error as e:
        update.message.reply_text(f"Ошибка при получении телефонных номеров из базы данных: {str(e)}")
    finally:
        cursor.close()
        connection.close()

def save_email_to_db(update: Update, context: CallbackContext):
    answer = update.message.text.lower()
    if answer in ["да", "yes"]:
        global emailAddrList

        for email in emailAddrList:
            try:
                connection = connect_to_db()
                cursor = connection.cursor()

                # Проверяем, существует ли уже такой email в базе данных
                cursor.execute("SELECT * FROM emails WHERE email = %s", (email,))
                existing_email = cursor.fetchone()
                if existing_email:
                    update.message.reply_text(f"Электронная почта {email} уже существует в базе данных.")
                    continue

                # Если email не существует, выполняем вставку
                cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
                connection.commit()
                update.message.reply_text(f"Электронная почта {email} успешно записана в базу данных.")

            except psycopg2.Error as error:
                update.message.reply_text(f"Ошибка добавления электронной почты в базу данных: {str(error)}")
            finally:
                cursor.close()
                connection.close()

    else:
        update.message.reply_text("Запись данных отменена.")

    return ConversationHandler.END

def save_phone_number_to_db(update: Update, context: CallbackContext):
    answer = update.message.text.lower()
    if answer in ["да", "yes"]:
        global phoneNumberList

        for phone in phoneNumberList:
            try:
                connection = connect_to_db()
                cursor = connection.cursor()

                # Проверяем, существует ли уже такой номер в базе данных
                cursor.execute("SELECT * FROM phones WHERE phone_number = %s", (phone,))
                existing_phone = cursor.fetchone()
                if existing_phone:
                    update.message.reply_text(f"Номер телефона {phone} уже существует в базе данных.")
                    continue

                # Если номер не существует, выполняем вставку
                cursor.execute("INSERT INTO phones (phone_number) VALUES (%s)", (phone,))
                connection.commit()
                update.message.reply_text(f"Номер телефона {phone} успешно записан в базу данных.")

            except psycopg2.Error as error:
                update.message.reply_text(f"Ошибка добавления номера телефона в базу данных: {str(error)}")
            finally:
                cursor.close()
                connection.close()

    else:
        update.message.reply_text("Запись данных отменена.")

    return ConversationHandler.END

def echo(update: Update, context):
    update.message.reply_text(update.message.text)

def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Обработчик диалога
    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('findPhoneNumbers', findPhoneNumbersCommand), CommandHandler('findEmailAddr', findEmailAddrCommand), CommandHandler('verify_password', verifyPasswordCommand), CommandHandler('get_apt_list_search', get_apt_list_search)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'findEmailAddr': [MessageHandler(Filters.text & ~Filters.command, findEmailAddr)],
            PASSWORD_CHECK : [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
            'search_package': [MessageHandler(Filters.text & ~Filters.command, search_package)],
            'save_phone_number_to_db': [MessageHandler(Filters.text & ~Filters.command, save_phone_number_to_db)],
            'save_email_to_db': [MessageHandler(Filters.text & ~Filters.command, save_email_to_db)],
        },
        fallbacks=[]
    )
		
	# Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    dp.add_handler(CommandHandler("echo", echo))
    #dp.add_handler(CommandHandler("check_db_connection", check_db_connection))
	# Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
		
	# Запускаем бота
    updater.start_polling()

	# Останавливаем бота при нажатии Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
