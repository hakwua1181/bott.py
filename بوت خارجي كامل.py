import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import time
import threading
from collections import defaultdict
import os
import random

# Configuration
API_TOKEN = '7987242628:AAFqSeQ3ni2l_p5yaf4LXpa1Wto7MJcsm_c'
ADMIN_ID = 381450213
bot = telebot.TeleBot(API_TOKEN)

# Data storage
user_data = {}
allowed_users = {}
stop_requested = False
sending_stats = defaultdict(lambda: {
    'total_sent': 0,
    'total_failed': 0,
    'active': False,
    'accounts': defaultdict(lambda: {'sent': 0, 'failed': 0, 'banned': False}),
    'start_time': None,
    'progress_message_id': None,
    'target_count': 0,
    'delay': 1
})

class EmailSender:
    @staticmethod
    def send_email(sender, password, recipient, subject, body, image_path=None):
        try:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    msg.attach(img)
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                try:
                    server.login(sender, password)
                except smtplib.SMTPAuthenticationError:
                    raise
                except Exception as e:
                    print(f"Login error: {str(e)}")
                    return False
                
                try:
                    server.send_message(msg)
                    return True
                except Exception as e:
                    print(f"Sending error: {str(e)}")
                    return False
                
        except smtplib.SMTPAuthenticationError:
            raise
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False

def show_main_menu(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("▶ بدء الإرسال", callback_data="start_sending"),
        InlineKeyboardButton("📋 عرض الحسابات", callback_data="show_accounts"),
        InlineKeyboardButton("➕ تعيين حساب", callback_data="set_account"),
        InlineKeyboardButton("📝 تعيين كليشة", callback_data="set_template"),
        InlineKeyboardButton("📌 تعيين موضوع", callback_data="set_subject"),
        InlineKeyboardButton("🔢 تعيين عدد إرسال", callback_data="set_count"),
        InlineKeyboardButton("🖼️ تعيين صورة", callback_data="set_image"),
        InlineKeyboardButton("⏱️ تعيين سليب", callback_data="set_delay"),
        InlineKeyboardButton("📧 تعيين ايميلات", callback_data="set_emails"),
        InlineKeyboardButton("ℹ️ عرض المعلومات", callback_data="show_info"),
        InlineKeyboardButton("🗑️ مسح المعلومات", callback_data="clear_data"),
        InlineKeyboardButton("❌ مسح الصورة", callback_data="delete_image")
    ]
    markup.add(buttons[0])
    markup.add(buttons[1], buttons[2])
    markup.add(buttons[3], buttons[4])
    markup.add(buttons[5], buttons[6])
    markup.add(buttons[7], buttons[8])
    markup.add(buttons[9], buttons[10])
    markup.add(buttons[11])
    bot.send_message(chat_id, "🏠 القائمة الرئيسية:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in allowed_users:
        contact_markup = InlineKeyboardMarkup()
        contact_markup.add(InlineKeyboardButton("📞 تواصل مع المطور", url="https://t.me/YOUR_TELEGRAM"))
        bot.send_message(message.chat.id, "⚠️ عذراً، أنت غير مشترك في البوت.\nيرجى التواصل مع المطور للتفعيل.", reply_markup=contact_markup)
    else:
        show_main_menu(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ هذا الأمر للمطور فقط!")
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("➕ إضافة مشترك", callback_data="add_user"),
        InlineKeyboardButton("➖ حذف مشترك", callback_data="remove_user")
    )
    markup.add(InlineKeyboardButton("👥 عرض المشتركين", callback_data="list_users"))
    
    bot.send_message(message.chat.id, "🔧 لوحة التحكم:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_account")
def set_account_handler(call):
    msg = bot.send_message(call.message.chat.id, "📩 أرسل الحساب (أو عدة حسابات) بالشكل:\nemail:password\nويمكنك إرسال أكثر من حساب بسطر لكل حساب")
    bot.register_next_step_handler(msg, process_accounts)

def process_accounts(message):
    try:
        user_id = message.from_user.id
        accounts = [line.strip() for line in message.text.split('\n') if ':' in line]
        
        if not accounts:
            bot.send_message(message.chat.id, "❌ لم يتم إدخال حسابات صالحة!")
            return
        
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]['accounts'] = []
        
        for acc in accounts:
            email, password = acc.split(':', 1)
            user_data[user_id]['accounts'].append({
                'email': email.strip(),
                'password': password.strip()
            })
        
        count = len(user_data[user_id]['accounts'])
        bot.send_message(message.chat.id, f"✅ تم حفظ {count} حساب بنجاح!")
        show_main_menu(message.chat.id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "show_accounts")
def show_accounts_handler(call):
    user_id = call.from_user.id
    accounts = user_data.get(user_id, {}).get('accounts', [])
    
    if not accounts:
        bot.send_message(call.message.chat.id, "⚠️ لا توجد حسابات مسجلة!")
        return
    
    response = "📋 الحسابات المسجلة:\n\n"
    for i, acc in enumerate(accounts, 1):
        response += f"{i}. {acc['email']}\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🗑️ حذف جميع الحسابات", callback_data="delete_all_accounts"))
    
    bot.send_message(call.message.chat.id, response, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "delete_all_accounts")
def delete_all_accounts_handler(call):
    user_id = call.from_user.id
    if user_id in user_data and 'accounts' in user_data[user_id]:
        user_data[user_id]['accounts'] = []
        bot.send_message(call.message.chat.id, "✅ تم حذف جميع الحسابات بنجاح!")
    else:
        bot.send_message(call.message.chat.id, "⚠️ لا توجد حسابات لحذفها!")
    show_main_menu(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_template")
def set_template_handler(call):
    msg = bot.send_message(call.message.chat.id, "📝 أرسل نص الكليشة التي تريد إرسالها:")
    bot.register_next_step_handler(msg, process_template)

def process_template(message):
    user_id = message.from_user.id
    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['template'] = message.text
    bot.send_message(message.chat.id, "✅ تم حفظ الكليشة بنجاح!")
    show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_subject")
def set_subject_handler(call):
    msg = bot.send_message(call.message.chat.id, "📌 أرسل موضوع الرسالة:")
    bot.register_next_step_handler(msg, process_subject)

def process_subject(message):
    user_id = message.from_user.id
    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['subject'] = message.text
    bot.send_message(message.chat.id, "✅ تم حفظ الموضوع بنجاح!")
    show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_count")
def set_count_handler(call):
    msg = bot.send_message(call.message.chat.id, "🔢 أرسل عدد الرسائل التي تريد إرسالها لكل مستلم:")
    bot.register_next_step_handler(msg, process_count)

def process_count(message):
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
        user_id = message.from_user.id
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]['message_count'] = count
        bot.send_message(message.chat.id, f"✅ تم تعيين عدد الرسائل إلى {count} بنجاح!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إدخال رقم صحيح موجب!")
    finally:
        show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_delay")
def set_delay_handler(call):
    msg = bot.send_message(call.message.chat.id, "⏱️ أرسل الفاصل الزمني بين الرسائل (بالثواني):")
    bot.register_next_step_handler(msg, process_delay)

def process_delay(message):
    try:
        delay = int(message.text)
        if delay < 0:
            raise ValueError
        user_id = message.from_user.id
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]['delay'] = delay
        sending_stats[user_id]['delay'] = delay
        bot.send_message(message.chat.id, f"✅ تم تعيين الفاصل الزمني إلى {delay} ثانية بنجاح!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إدخال رقم صحيح غير سالب!")
    finally:
        show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_emails")
def set_emails_handler(call):
    msg = bot.send_message(call.message.chat.id, "📧 أرسل قائمة الايميلات المستلمة (إيميل واحد في كل سطر):")
    bot.register_next_step_handler(msg, process_emails)

def process_emails(message):
    emails = [line.strip() for line in message.text.split('\n') if '@' in line]
    if not emails:
        bot.send_message(message.chat.id, "❌ لم يتم إدخال ايميلات صالحة!")
        return
    
    user_id = message.from_user.id
    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['emails'] = emails
    
    bot.send_message(message.chat.id, f"✅ تم حفظ {len(emails)} ايميل بنجاح!")
    show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_image")
def set_image_handler(call):
    msg = bot.send_message(call.message.chat.id, "🖼️ أرسل الصورة التي تريد إرفاقها:")
    bot.register_next_step_handler(msg, process_image)

def process_image(message):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ يجب إرسال صورة صالحة!")
        return
    
    try:
        user_id = message.from_user.id
        user_data[user_id] = user_data.get(user_id, {})
        
        # Get the file path
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Save the image
        if not os.path.exists('images'):
            os.makedirs('images')
            
        image_path = f'images/{user_id}_{message.photo[-1].file_id}.jpg'
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        user_data[user_id]['image_path'] = image_path
        bot.send_message(message.chat.id, "✅ تم حفظ الصورة بنجاح!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء حفظ الصورة: {str(e)}")
    finally:
        show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "delete_image")
def delete_image_handler(call):
    user_id = call.from_user.id
    if user_id in user_data and 'image_path' in user_data[user_id]:
        try:
            os.remove(user_data[user_id]['image_path'])
        except:
            pass
        del user_data[user_id]['image_path']
        bot.send_message(call.message.chat.id, "✅ تم حذف الصورة بنجاح!")
    else:
        bot.send_message(call.message.chat.id, "⚠️ لا توجد صورة محفوظة!")
    show_main_menu(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "show_info")
def show_info_handler(call):
    user_id = call.from_user.id
    info = user_data.get(user_id, {})
    
    if not info:
        bot.send_message(call.message.chat.id, "⚠️ لا توجد معلومات مسجلة!")
        return
    
    response = "📊 معلوماتك الحالية:\n\n"
    response += f"📋 عدد الحسابات: {len(info.get('accounts', []))}\n"
    response += f"📧 عدد الايميلات المستلمة: {len(info.get('emails', []))}\n"
    response += f"📌 الموضوع: {info.get('subject', 'غير معين')}\n"
    response += f"📝 الكليشة: {info.get('template', 'غير معين')[:50]}...\n"
    response += f"🔢 عدد الرسائل: {info.get('message_count', 'غير معين')}\n"
    response += f"⏱️ الفاصل الزمني: {info.get('delay', 'غير معين')} ثانية\n"
    response += f"🖼️ الصورة: {'موجودة' if 'image_path' in info else 'غير موجودة'}"
    
    bot.send_message(call.message.chat.id, response)

@bot.callback_query_handler(func=lambda call: call.data == "clear_data")
def clear_data_handler(call):
    user_id = call.from_user.id
    if user_id in user_data:
        # Delete image file if exists
        if 'image_path' in user_data[user_id]:
            try:
                os.remove(user_data[user_id]['image_path'])
            except:
                pass
        user_data[user_id] = {}
        bot.send_message(call.message.chat.id, "✅ تم مسح جميع البيانات بنجاح!")
    else:
        bot.send_message(call.message.chat.id, "⚠️ لا توجد بيانات لحذفها!")
    show_main_menu(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "add_user")
def add_user_handler(call):
    msg = bot.send_message(call.message.chat.id, "أرسل ID المستخدم لإضافته:")
    bot.register_next_step_handler(msg, process_add_user)

def process_add_user(message):
    try:
        user_id = int(message.text)
        allowed_users[user_id] = True
        bot.send_message(message.chat.id, f"✅ تم تفعيل المستخدم {user_id} بنجاح!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إدخال رقم ID صحيح!")
    finally:
        admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "remove_user")
def remove_user_handler(call):
    msg = bot.send_message(call.message.chat.id, "أرسل ID المستخدم لإزالته:")
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    try:
        user_id = int(message.text)
        if user_id in allowed_users:
            del allowed_users[user_id]
            bot.send_message(message.chat.id, f"✅ تم إزالة المستخدم {user_id} بنجاح!")
        else:
            bot.send_message(message.chat.id, "⚠️ هذا المستخدم غير موجود في القائمة!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إدخال رقم ID صحيح!")
    finally:
        admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "list_users")
def list_users_handler(call):
    if not allowed_users:
        bot.send_message(call.message.chat.id, "⚠️ لا يوجد مستخدمين مفعلين!")
        return
    
    response = "👥 قائمة المستخدمين المفعلين:\n\n"
    for user_id in allowed_users:
        response += f"- {user_id}\n"
    
    bot.send_message(call.message.chat.id, response)

def update_progress_message(user_id):
    while sending_stats[user_id]['active'] and not stop_requested:
        try:
            stats = sending_stats[user_id]
            elapsed = time.time() - stats['start_time']
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
            
            progress = min(stats['total_sent'] / stats['target_count'] * 100, 100) if stats['target_count'] > 0 else 0
            
            progress_msg = f"""
🚀 جارٍ الإرسال...

📤 عدد الإرسال: {stats['total_sent']}
🎯 العدد المطلوب: {stats['target_count']}
📊 التقدم: {progress:.1f}%

⏱ السليب: {stats['delay']} ثانية
⏱ الوقت المنقضي: {elapsed_str}
            """
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⏹ إيقاف الإرسال", callback_data="stop_sending"))
            
            bot.edit_message_text(
                chat_id=user_id,
                message_id=stats['progress_message_id'],
                text=progress_msg,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error updating progress: {str(e)}")
        
        time.sleep(2)

def send_emails_process(user_id, user_info):
    global stop_requested
    
    accounts = user_info['accounts']
    recipients = user_info['emails']
    subject = user_info['subject']
    template = user_info['template']
    count = user_info['message_count']
    delay = user_info.get('delay', 1)
    image_path = user_info.get('image_path')
    
    # Initialize stats
    sending_stats[user_id]['total_sent'] = 0
    sending_stats[user_id]['total_failed'] = 0
    sending_stats[user_id]['active'] = True
    sending_stats[user_id]['start_time'] = time.time()
    sending_stats[user_id]['target_count'] = len(recipients) * count * len(accounts)
    sending_stats[user_id]['delay'] = delay
    
    # Initialize account stats
    for acc in accounts:
        sending_stats[user_id]['accounts'][acc['email']] = {
            'sent': 0,
            'failed': 0,
            'banned': False
        }
    
    # Start progress updater
    threading.Thread(target=update_progress_message, args=(user_id,)).start()
    
    # إرسال من جميع الحسابات لكل مستلم بالعدد المطلوب
    for recipient in recipients:
        if stop_requested:
            break
            
        for _ in range(count):
            if stop_requested:
                break
                
            # ترتيب الحسابات عشوائياً لتوزيع الحمل
            random.shuffle(accounts)
            
            # إرسال من كل حساب للمستلم الحالي
            for account in accounts:
                if stop_requested:
                    break
                    
                # تخطي الحسابات المحظورة
                if sending_stats[user_id]['accounts'][account['email']]['banned']:
                    continue
                    
                try:
                    success = EmailSender.send_email(
                        account['email'],
                        account['password'],
                        recipient,
                        subject,
                        template,
                        image_path
                    )
                    
                    if success:
                        sending_stats[user_id]['accounts'][account['email']]['sent'] += 1
                        sending_stats[user_id]['total_sent'] += 1
                    else:
                        sending_stats[user_id]['accounts'][account['email']]['failed'] += 1
                        sending_stats[user_id]['total_failed'] += 1
                        
                except smtplib.SMTPAuthenticationError:
                    # وضع علامة على الحساب كمحظور
                    sending_stats[user_id]['accounts'][account['email']]['banned'] = True
                    sending_stats[user_id]['accounts'][account['email']]['failed'] += 1
                    sending_stats[user_id]['total_failed'] += 1
                    
                    # إعلام المستخدم بالحساب المحظور
                    bot.send_message(
                        user_id,
                        f"⚠️ الحساب محظور أو به خطأ: {account['email']}\n"
                        f"سيتم الاستمرار باستخدام الحسابات الأخرى"
                    )
                    
                except Exception as e:
                    print(f"Error: {str(e)}")
                    sending_stats[user_id]['accounts'][account['email']]['failed'] += 1
                    sending_stats[user_id]['total_failed'] += 1
                
                # تطبيق السليب فقط إذا كان أكبر من 0
                if delay > 0 and not stop_requested:
                    time.sleep(delay)
            
            # التحقق إذا كانت جميع الحسابات محظورة
            active_accounts = sum(
                1 for acc in accounts 
                if not sending_stats[user_id]['accounts'][acc['email']]['banned']
            )
            
            if active_accounts == 0:
                bot.send_message(
                    user_id,
                    "⛔ توقف الإرسال! جميع الحسابات محظورة أو بها أخطاء"
                )
                stop_requested = True
                break
    
    sending_stats[user_id]['active'] = False
    
    # إرسال التقرير النهائي
    elapsed = time.time() - sending_stats[user_id]['start_time']
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    
    success_rate = (sending_stats[user_id]['total_sent'] / sending_stats[user_id]['target_count'] * 100) if sending_stats[user_id]['target_count'] > 0 else 0
    
    # إعداد تقرير حالة الحسابات
    accounts_status = "\n\n📧 حالة الحسابات:\n"
    for acc in accounts:
        acc_stat = sending_stats[user_id]['accounts'][acc['email']]
        status = "❌ محظور" if acc_stat['banned'] else "✅ نشط"
        accounts_status += (
            f"{acc['email']} - {status}\n"
            f"📤 مرسلة: {acc_stat['sent']} | ❌ فشل: {acc_stat['failed']}\n\n"
        )
    
    final_msg = f"""
{'✅ تم الانتهاء من الإرسال بنجاح!' if not stop_requested else '⏹ تم إيقاف الإرسال!'}

📊 النتائج:
📤 تم الإرسال: {sending_stats[user_id]['total_sent']}
❌ فشل الإرسال: {sending_stats[user_id]['total_failed']}
🎯 الهدف: {sending_stats[user_id]['target_count']}
📊 معدل النجاح: {success_rate:.1f}%
⏱ الوقت المستغرق: {elapsed_str}
{accounts_status}
    """
    
    try:
        bot.edit_message_text(
            chat_id=user_id,
            message_id=sending_stats[user_id]['progress_message_id'],
            text=final_msg
        )
    except:
        bot.send_message(user_id, final_msg)

@bot.callback_query_handler(func=lambda call: call.data == "start_sending")
def start_sending_handler(call):
    global stop_requested
    user_id = call.from_user.id
    
    # التحقق من البيانات المطلوبة
    required = {
        'accounts': "الحسابات المرسلة",
        'emails': "قائمة المستلمين",
        'subject': "موضوع الرسالة",
        'template': "محتوى الرسالة",
        'message_count': "عدد الرسائل"
    }
    
    user_info = user_data.get(user_id, {})
    missing = [desc for field, desc in required.items() if not user_info.get(field)]
    
    if missing:
        error_msg = "❌ المطلوب:\n" + "\n".join(f"- {item}" for item in missing)
        bot.send_message(user_id, error_msg)
        return
    
    stop_requested = False
    
    # تعيين سليب افتراضي إذا لم يتم تعيينه
    if 'delay' not in user_info:
        user_info['delay'] = 1
    
    # إنشاء رسالة التقدم مع العداد
    progress_msg = f"""
🚀 بدأ الإرسال بنجاح!

📤 عدد الإرسال: 0
🎯 العدد المطلوب: {len(user_info['emails']) * user_info['message_count'] * len(user_info['accounts'])}

⏱ السليب: {user_info['delay']} ثانية

جارٍ الإرسال... الرجاء الانتظار
    """
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⏹ إيقاف الإرسال", callback_data="stop_sending"))
    
    msg = bot.send_message(user_id, progress_msg, reply_markup=markup)
    sending_stats[user_id]['progress_message_id'] = msg.message_id
    
    # بدء الإرسال في thread جديد
    threading.Thread(
        target=send_emails_process,
        args=(user_id, user_info)
    ).start()

@bot.callback_query_handler(func=lambda call: call.data == "stop_sending")
def stop_sending_handler(call):
    global stop_requested
    user_id = call.from_user.id
    stop_requested = True
    bot.answer_callback_query(call.id, "⏹ جاري إيقاف الإرسال...")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    global stop_requested
    user_id = message.from_user.id
    stop_requested = True
    bot.send_message(message.chat.id, "⏹ تم طلب إيقاف الإرسال...")

if __name__ == "__main__":
    print("🤖 Bot is running with all requested features...")
    bot.polling()