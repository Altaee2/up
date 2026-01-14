import telebot
import os
import subprocess
import zipfile
import tarfile
import requests
import json 
import time
from telebot.types import ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

PYTHON_CMD = 'python3'      
PIP_CMD = 'pip3'            
PIPREQS_CMD = 'pipreqs'     

API_TOKEN = '7451237311:AAF31mNEP07Z5dw6MLJNZ2B-kPqxSOke5oo'
UPLOAD_DIR = 'telegram_scripts'
ADMIN_IDS = [6454550864, 7769271031] 

bot = telebot.TeleBot(API_TOKEN)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
RUNNING_PROCESSES = {}
def get_main_keyboard():
    """إنشاء لوحة المفاتيح الرئيسية"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📁 عرض الملفات", callback_data='list')
    )
    markup.row(

        InlineKeyboardButton("👥 عرض الأدمنز", callback_data='show_admins')
    )
    return markup

def run_script_background(filename, chat_id):

    script_path = os.path.join(UPLOAD_DIR, filename)
    
    if filename in RUNNING_PROCESSES and RUNNING_PROCESSES[filename].poll() is None:
        return f"⚠️ السكربت {filename} يعمل بالفعل.", False
        
    try:
        process = subprocess.Popen(
            [PYTHON_CMD, script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        RUNNING_PROCESSES[filename] = process
        return f"✅ تم تشغيل السكربت {filename} في الخلفية. PID: {process.pid}", True
    except FileNotFoundError:
        return f"❌ خطأ: لم يتم العثور على الأمر التنفيذي `{PYTHON_CMD}`. تأكد من تثبيت Python بشكل صحيح على السيرفر.", False
    except Exception as e:
        return f"❌ خطأ غير متوقع أثناء التشغيل: {e}", False


def stop_script(filename):
    """يوقف السكربت الجاري تشغيله"""
    if filename not in RUNNING_PROCESSES:
        return f"⚠️ السكربت {filename} غير مسجل كعملية جارية."
        
    process = RUNNING_PROCESSES[filename]
    
    if process.poll() is not None:
        del RUNNING_PROCESSES[filename]
        return f"⚠️ السكربت {filename} كان قد انتهى بالفعل."

    try:
        process.terminate() 
        time.sleep(1) 
        
        if process.poll() is None:
            process.kill()
            
        del RUNNING_PROCESSES[filename]
        return f"🛑 تم إيقاف السكربت {filename} بنجاح. (PID: {process.pid})"
    except Exception as e:
        del RUNNING_PROCESSES[filename]
        return f"❌ خطأ أثناء إيقاف السكربت {filename}: {e}"

def install_dependencies(script_dir, bot, chat_id):

    bot.send_message(chat_id, "🔧 جاري تحليل المتطلبات...")
    
    try:
        process = subprocess.run(
            [PIPREQS_CMD, '--force', script_dir], 
            check=True, 
            capture_output=True, 
            text=True
        )
        bot.send_message(chat_id, "✅ تم إنشاء requirements.txt بنجاح.")
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ خطأ في إنشاء requirements.txt:\n{e.stderr[:4000]}"
        bot.send_message(chat_id, error_msg)
        return False
    except FileNotFoundError:
        bot.send_message(chat_id, f"❌ خطأ: لم يتم العثور على الأمر التنفيذي `{PIPREQS_CMD}`. تأكد من تثبيت pipreqs.")
        return False

    requirements_file = os.path.join(script_dir, 'requirements.txt')
    if os.path.exists(requirements_file):
        try:
            bot.send_message(chat_id, "🛠️ جاري تثبيت المكتبات (قد يستغرق وقتاً)...")
            process = subprocess.run(
                [PIP_CMD, 'install', '-r', requirements_file], 
                check=True, 
                capture_output=True, 
                text=True
            )
            output = f"✅ تم تثبيت المكتبات بنجاح:\n{process.stdout[:4000]}"
            bot.send_message(chat_id, output)
            return True
        except subprocess.CalledProcessError as e:
            error_msg = f"❌ خطأ في تثبيت المكتبات (راجع السجل):\n{e.stderr[:4000]}"
            bot.send_message(chat_id, error_msg)
            return False
        except FileNotFoundError:
            bot.send_message(chat_id, f"❌ خطأ: لم يتم العثور على الأمر التنفيذي `{PIP_CMD}`. تأكد من تثبيت pip بشكل صحيح.")
            return False
    return True 

def extract_archive(filepath, extract_to, bot, chat_id):

    try:
        if filepath.endswith(('.zip')):
            with zipfile.ZipFile(filepath, 'r') as zf:
                zf.extractall(extract_to)
            return True, "✅ تم فك ضغط ملف ZIP بنجاح."
        elif filepath.endswith(('.tar', '.gz', '.tgz')):
            with tarfile.open(filepath, 'r') as tf:
                tf.extractall(extract_to)
            return True, "✅ تم فك ضغط ملف TAR/GZ بنجاح."
        return False, None
    except Exception as e:
        return False, f"❌ خطأ في فك الضغط: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "مرحباً بك في بوت تشغيل سكربتات البايثون المفتوح! 🤖\n"
        "إدارة السكربتات تتم من خلال الأزرار التفاعلية.\n\n"
        "• لرفع ملف: أرسل ملف بايثون (.py) أو مضغوط (.zip).\n"
    )
    bot.reply_to(message, help_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['list'])
def list_files(message):

    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.py') and not f.startswith('.')]
    
    if not files:
        bot.send_message(message.chat.id, "لا توجد ملفات بايثون (.py) مرفوعة حالياً قابلة للتشغيل.")
        return

    markup = InlineKeyboardMarkup()
    
    for filename in list(RUNNING_PROCESSES.keys()):
        if RUNNING_PROCESSES[filename].poll() is not None:
            del RUNNING_PROCESSES[filename]

    response_text = "📁 قائمة السكربتات المتاحة:\n"
    
    for filename in sorted(files):
        is_running = filename in RUNNING_PROCESSES
        status_emoji = "🟢 يعمل" if is_running else "⚪ متوقف"
        
        markup.add(InlineKeyboardButton(f"{status_emoji} | {filename}", callback_data='ignore'))
        
        control_row = []
        if is_running:
            control_row.append(InlineKeyboardButton("🛑 إيقاف", callback_data=f'stop_file:{filename}'))
        else:
            control_row.append(InlineKeyboardButton("🚀 تشغيل", callback_data=f'run_file:{filename}'))
            
        control_row.append(InlineKeyboardButton("🗑️ حذف", callback_data=f'delete_file:{filename}'))
        
        markup.row(*control_row)
        response_text += f"• {filename}\n"

    bot.send_message(message.chat.id, response_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    chat_id = call.message.chat.id
    
    if data != 'ignore':
        try:
       
            bot.answer_callback_query(call.id)
        except telebot.apihelper.ApiTelegramException as e:
            
            if 'query is too old' not in str(e):
                raise e
    
    if data.startswith('run_file:'):
        filename = data.split(':')[1]
        msg, success = run_script_background(filename, chat_id)
        bot.send_message(chat_id, msg)
        list_files(call.message)
        return
        
    elif data.startswith('stop_file:'):
        filename = data.split(':')[1]
        msg = stop_script(filename)
        bot.send_message(chat_id, msg)
        list_files(call.message)
        return

    elif data.startswith('delete_file:'):
        filename = data.split(':')[1]
        
        if filename in RUNNING_PROCESSES and RUNNING_PROCESSES[filename].poll() is None:
            stop_script(filename)
            bot.send_message(chat_id, f"⚠️ تم إيقاف السكربت {filename} قبل الحذف.")

        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                bot.send_message(chat_id, f"🗑️ تم حذف الملف '{filename}' بنجاح.")
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ أثناء حذف الملف: {e}")
        else:
            bot.send_message(chat_id, f"❌ الملف '{filename}' غير موجود.")
            
        list_files(call.message)
        return

    elif data == 'list':
        list_files(call.message)
    elif data == 'help':
        help_text = (
            "📜 المساعدة والأوامر:\n"
            "هذا البوت مفتوح للجميع. التحكم يتم عن طريق *📁 عرض الملفات*.\n\n"
        )
        bot.send_message(chat_id, help_text, reply_markup=get_main_keyboard())
    elif data == 'show_id':
        bot.send_message(chat_id, f"👤 الـ ID الخاص بك هو: `{call.from_user.id}`", 
                         parse_mode='Markdown', reply_markup=get_main_keyboard())
    elif data == 'show_admins':
        admins_list = "\n".join([f"• `{aid}`" for aid in ADMIN_IDS])
        bot.send_message(chat_id, f"👑 قائمة IDs الإدارة:\n{admins_list}", 
                         parse_mode='Markdown', reply_markup=get_main_keyboard())
    elif data == 'ignore':
        pass

@bot.message_handler(commands=['run', 'delete'])
def disable_old_commands(message):
    bot.reply_to(message, "⚠️ تم تعطيل هذا الأمر. يرجى استخدام زر *📁 عرض الملفات* ثم أزرار التشغيل/الإيقاف/الحذف التفاعلية.", parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    file_info = bot.get_file(message.document.file_id)
    download_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}'
    filename = message.document.file_name
    
    if not filename.endswith(('.py', '.zip', '.tar', '.gz', '.tgz')):
        bot.reply_to(message, "❌ الملف غير مدعوم. يرجى رفع ملف (.py) أو مضغوط (.zip/.tar.gz).")
        return
        
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    try:
        bot.send_message(message.chat.id, f"📥 جاري تحميل الملف '{filename}'...")
        file_response = requests.get(download_url)
        with open(filepath, 'wb') as f:
            f.write(file_response.content)
        bot.send_message(message.chat.id, f"💾 تم الحفظ بنجاح في: {filepath}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في تحميل الملف: {e}")
        return
        
    is_extracted, extract_msg = extract_archive(filepath, UPLOAD_DIR, bot, message.chat.id)
    if is_extracted:
        bot.send_message(message.chat.id, extract_msg)
        script_dir = UPLOAD_DIR
    else:
        script_dir = UPLOAD_DIR

    if filename.endswith('.py') or is_extracted:
        install_dependencies(script_dir, bot, message.chat.id)
    
    bot.send_message(message.chat.id, "✅ العملية اكتملت. استخدم *📁 عرض الملفات* للتحكم.", parse_mode='Markdown', reply_markup=get_main_keyboard())

print("البوت يعمل...")
bot.polling()