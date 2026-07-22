import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB = "giveaway.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS giveaways
                 (id INTEGER PRIMARY KEY, channel TEXT, winners INTEGER, participants TEXT, auto INTEGER, creator INTEGER, active INTEGER)''')
    conn.commit()
    conn.close()

init_db()

async def check_sub(user_id, channel, bot):
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحبا! انا بوت السحوبات 🎁\n\n"
        "الاوامر:\n"
        "/newgiveaway @القناة عدد_الفائزين auto/manual\n"
        "مثال: /newgiveaway @my_channel 3 auto"
    )

async def new_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("الاستخدام: /newgiveaway @القناة عدد_الفائزين auto/manual")
        return
    channel = context.args[0]
    winners = int(context.args[1])
    auto = 1 if context.args[2].lower() == "auto" else 0
    creator = update.effective_user.id
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO giveaways (channel, winners, participants, auto, creator, active) VALUES (?,?,?,?,?,1)",(channel, winners, "", auto, creator, 1))
    giveaway_id = c.lastrowid
    conn.commit()
    conn.close()
    keyboard = [[InlineKeyboardButton("اشترك في السحب 🎉", callback_data=f"join_{giveaway_id}")]]
    await update.message.reply_text(
        f"تم انشاء سحب جديد!\n"
        f"القناة المطلوبة: {channel}\n"
        f"عدد الفائزين: {winners}\n"
        f"نوع السحب: {'تلقائي' if auto else 'يدوي'}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    giveaway_id = int(query.data.split("_")[1])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM giveaways WHERE id=?", (giveaway_id,))
    g = c.fetchone()
    if not g or g[6] == 0:
        await query.edit_message_text("السحب منتهي")
        return
    if not await check_sub(query.from_user.id, g[1], context.bot):
        await query.message.reply_text(f"لازم تشترك في القناة اول: {g[1]}")
        conn.close()
        return
    participants = g[3].split(",") if g[3] else []
    user_id = str(query.from_user.id)
    if user_id in participants:
        await query.message.reply_text("انت مشترك بالفعل")
        conn.close()
        return
    participants.append(user_id)
    c.execute("UPDATE giveaways SET participants=? WHERE id=?", (",".join(participants), giveaway_id))
    conn.commit()
    conn.close()
    await query.message.reply_text("تم اشتراكك! ✅")
    await context.bot.send_message(g[5], f"مشترك جديد في السحب #{giveaway_id}: {query.from_user.first_name}")

async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("الاستخدام: /draw رقم_السحب")
        return
    giveaway_id = int(context.args[0])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM giveaways WHERE id=?", (giveaway_id,))
    g = c.fetchone()
    if not g:
        await update.message.reply_text("السحب غير موجود")
        return
    if update.effective_user.id!= g[5]:
        await update.message.reply_text("ممنوع! فقط منشئ السحب يقدر يسحب")
        return
    participants = g[3].split(",") if g[3] else []
    if len(participants) < g[2]:
        await update.message.reply_text("عدد المشاركين اقل من عدد الفائزين")
        return
    winners = random.sample(participants, g[2])
    c.execute("UPDATE giveaways SET active=0 WHERE id=?", (giveaway_id,))
    conn.commit()
    conn.close()
    winners_text = "\n".join([f"- {w}" for w in winners])
    await update.message.reply_text(f"الفائزين في السحب #{giveaway_id}:\n{winners_text}")

async def participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("الاستخدام: /participants رقم_السحب")
        return
    giveaway_id = int(context.args[0])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT participants FROM giveaways WHERE id=?", (giveaway_id,))
    g = c.fetchone()
    conn.close()
    count = len(g[0].split(",")) if g and g[0] else 0
    await update.message.reply_text(f"عدد المشاركين في السحب #{giveaway_id}: {count}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newgiveaway", new_giveaway))
    app.add_handler(CommandHandler("draw", draw))
    app.add_handler(CommandHandler("participants", participants))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()