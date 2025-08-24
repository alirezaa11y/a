from pyrubi import Client
from pyrubi.types import Message
from datetime import datetime
import threading

bot = Client('bot')

# ساختار ذخیره داده‌ها
save = {
    "groups": {}
}

lock = threading.Lock()

def is_admin(group_guid, user_guid):
    """بررسی اینکه کاربر ادمین است یا نه"""
    try:
        admins = bot.get_admin_members(group_guid)['in_chat_members']
        return any(admin['member_guid'] == user_guid for admin in admins)
    except Exception:
        return False

def check_admin(msg):
    """بررسی ادمین بودن کاربر قبل از اجرای دستور"""
    if not is_admin(msg.object_guid, msg.author_guid):
        msg.reply("شما دسترسی لازم برای اجرای این دستور را ندارید! ❌")
        return False
    return True

def load_data(group_guid):
    """بارگذاری داده‌های گروه"""
    with lock:
        if group_guid not in save["groups"]:
            save["groups"][group_guid] = {
                "silent_list": [],
                "silent_users_info": {},
                "warnings_link": {},
                "warnings_forward": {}
            }
        return save["groups"][group_guid]

def get_user_info(user_guid):
    """دریافت اطلاعات کاربر"""
    try:
        user_info = bot.get_chat_info(user_guid)
        if 'user' in user_info:
            return {
                "first_name": user_info['user'].get('first_name', 'ناشناس'),
                "username": user_info['user'].get('username')
            }
        return {"first_name": 'ناشناس', "username": None}
    except Exception:
        return {"first_name": 'ناشناس', "username": None}

def format_username(username):
    """فرمت کردن نام کاربری"""
    return f"@{username}" if username else "ندارد"

@bot.on_message()
def handle_message(ms: Message):
    try:
        if not ms.is_group:
            return

        group_guid = ms.object_guid
        group_data = load_data(group_guid)
        text = ms.text.strip().lower() if ms.text else None

        # بررسی کاربران ساکت شده
        if ms.author_guid in group_data["silent_list"]:
            ms.delete()
            return

        # دستورات مدیریتی
        if text == "راهنما":
            help_msg = """📚 راهنمای دستورات ربات :

🔹 سکوت [ریپلای]
 - اضافه کردن کاربر به لیست سکوت (فقط ادمین)

🔹 حذف سکوت [ریپلای]
 - حذف کاربر از لیست سکوت (فقط ادمین)

🔹 لیست سکوت
 - نمایش لیست کاربران ساکت شده (فقط ادمین)

🔹 پاکسازی لیست سکوت
 - پاک کردن تمام لیست سکوت (فقط ادمین)

🔹 پین [ریپلای]
 - سنجاق کردن پیام (فقط ادمین)

🔹 بن [ریپلای]
 - بن کردن کاربر (فقط ادمین)

ایدی سازنده : @alireza_11207
"""
            ms.reply(help_msg)

        elif text == "سکوت":
            if not check_admin(ms):
                return
                
            if not ms.reply_info:
                ms.reply("⚠️ لطفاً روی پیام کاربر ریپلای کنید")
                return

            user_guid = ms.reply_info.author_guid
            user_info = get_user_info(user_guid)
            username = format_username(user_info["username"])

            with lock:
                if user_guid not in group_data["silent_list"]:
                    group_data["silent_list"].append(user_guid)
                    group_data["silent_users_info"][user_guid] = {
                        "name": user_info["first_name"],
                        "username": username
                    }
                    ms.reply(f"✅ کاربر {user_info['first_name']} ({username}) با موفقیت ساکت شد.")
                else:
                    ms.reply(f"⚠️ کاربر {user_info['first_name']} ({username}) از قبل ساکت است.")

        elif text == "حذف سکوت":
            if not check_admin(ms):
                return
                
            if not ms.reply_info:
                ms.reply("⚠️ لطفاً روی پیام کاربر ریپلای کنید")
                return

            user_guid = ms.reply_info.author_guid
            with lock:
                if user_guid in group_data["silent_list"]:
                    user_info = group_data["silent_users_info"].get(user_guid, {})
                    name = user_info.get("name", "ناشناس")
                    username = user_info.get("username", "ندارد")
                    group_data["silent_list"].remove(user_guid)
                    group_data["silent_users_info"].pop(user_guid, None)
                    ms.reply(f"✅ کاربر {name} ({username}) از لیست سکوت حذف شد.")
                else:
                    ms.reply("⚠️ این کاربر در لیست سکوت نیست.")

        elif text == "لیست سکوت":
            if not check_admin(ms):
                return
                
            with lock:
                if not group_data["silent_list"]:
                    ms.reply("🔹 لیست سکوت خالی است.")
                else:
                    msg = "📋 لیست کاربران ساکت شده:\n\n"
                    for i, user_guid in enumerate(group_data["silent_list"], 1):
                        user_info = group_data["silent_users_info"].get(user_guid, {})
                        name = user_info.get("name", "ناشناس")
                        username = user_info.get("username", "ندارد")
                        msg += f"{i}. {name} ({username})\n"
                    ms.reply(msg)

        elif text == "پاکسازی لیست سکوت":
            if not check_admin(ms):
                return
                
            with lock:
                count = len(group_data["silent_list"])
                group_data["silent_list"] = []
                group_data["silent_users_info"] = {}
                ms.reply(f"✅ لیست سکوت پاکسازی شد. ({count} کاربر حذف شدند)")

        elif text == "پین":
            if not check_admin(ms):
                return
                
            if hasattr(ms, 'reply_message_id') and ms.reply_message_id:
                try:
                    bot.pin_message(group_guid, ms.reply_message_id)
                    ms.reply("✅ پیام با موفقیت سنجاق شد!")
                except Exception as e:
                    ms.reply(f"❌ خطا در سنجاق کردن پیام: {str(e)}")
            else:
                ms.reply("⚠️ لطفاً روی پیام مورد نظر ریپلای کنید")

        elif text == "بن":
            if not check_admin(ms):
                return
                
            if not ms.reply_info:
                ms.reply("⚠️ لطفاً روی پیام کاربر ریپلای کنید")
                return

            user_guid = ms.reply_info.author_guid
            try:
                bot.ban_member(group_guid, user_guid)
                ms.reply("✅ کاربر با موفقیت بن شد.")
            except Exception as e:
                ms.reply(f"❌ خطا در بن کردن کاربر: {str(e)}")

        # مدیریت تخلفات
        if ms.text and ('http://' in ms.text or 'https://' in ms.text):
            handle_link_violation(ms, group_data, group_guid)
        
        if ms.is_forward:
            handle_forward_violation(ms, group_data, group_guid)

    except Exception as e:
        print(f"خطا در پردازش پیام: {e}")

def handle_link_violation(ms, group_data, group_guid):
    """مدیریت تخلف ارسال لینک"""
    user_guid = ms.author_guid
    with lock:
        if user_guid not in group_data["warnings_link"]:
            group_data["warnings_link"][user_guid] = 0
        
        group_data["warnings_link"][user_guid] += 1
        warnings = group_data["warnings_link"][user_guid]
        
        try:
            ms.delete()
            if warnings == 1:
                ms.reply(f"⚠️ اخطار 1/3: ارسال لینک ممنوع! (کاربر: {get_user_info(user_guid)['first_name']})")
            elif warnings == 2:
                ms.reply(f"⚠️ اخطار 2/3: آخرین اخطار! (کاربر: {get_user_info(user_guid)['first_name']})")
            elif warnings >= 3:
                bot.ban_member(group_guid, user_guid)
                ms.reply(f"⛔ کاربر {get_user_info(user_guid)['first_name']} به دلیل 3 اخطار ارسال لینک حذف شد!")
                group_data["warnings_link"][user_guid] = 0
        except Exception as e:
            print(f"خطا در پردازش تخلف لینک: {e}")

def handle_forward_violation(ms, group_data, group_guid):
    """مدیریت تخلف فوروارد"""
    user_guid = ms.author_guid
    with lock:
        if user_guid not in group_data["warnings_forward"]:
            group_data["warnings_forward"][user_guid] = 0
        
        group_data["warnings_forward"][user_guid] += 1
        warnings = group_data["warnings_forward"][user_guid]
        
        try:
            ms.delete()
            if warnings == 1:
                ms.reply(f"⚠️ اخطار 1/3: فوروارد ممنوع! (کاربر: {get_user_info(user_guid)['first_name']})")
            elif warnings == 2:
                ms.reply(f"⚠️ اخطار 2/3: آخرین اخطار! (کاربر: {get_user_info(user_guid)['first_name']})")
            elif warnings >= 3:
                bot.ban_member(group_guid, user_guid)
                ms.reply(f"⛔ کاربر {get_user_info(user_guid)['first_name']} به دلیل 3 اخطار فوروارد حذف شد!")
                group_data["warnings_forward"][user_guid] = 0
        except Exception as e:
            print(f"خطا در پردازش تخلف فوروارد: {e}")

bot.run()
