from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import PREFIXES

# --- Screenshots ke hisaab se Texts ---

START_TEXT = (
    "🔐 Hello **{name}**, welcome to **Security Bot**!\n\n"
    "✨ **Your Personal Chat Bodyguard is here!**\n\n"
    "🚀 **Features:**\n"
    "• Instantly deletes **edited messages** to prevent confusion.\n"
    "• Auto-removes all types of **media** — photos, videos, documents, gifs, stickers.\n"
    "• Cleans abusive, harmful words to keep your group positive and respectful.\n"
    "• Offers flexible **admin controls** like authentication and deletion delay.\n\n"
    "💡 *Keep your chat clean, safe, and spam-free — without lifting a finger!*\n\n"
    "👇 Click on the Help and Commands to know more!"
)

HELP_TEXT = (
    "📖 **Available Commands:**\n\n"
    "• `/start` — Show main menu\n"
    "• `/auth` — Exempt a user from deletions (Super Admins only)\n"
    "• `/unauth` — Remove exemption (Super Admins only)\n"
    "• `/authlist` — View exempted users\n"
    "• `/unauthall` — Remove all users exemption (chat owner only)\n"
    "• `/delay` — Set deletion delay for media (Admins only)\n"
    "• `/abuse` — Enable/disable abusive word filter (Admins only)\n\n"
    "📝 *Note: Default media deletion time is 1 hour.*"
)

# --- Buttons Logic ---

def start_buttons(bot_username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Secure Your Chat", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("📜 Help & Commands", callback_data="open_help")],
        [InlineKeyboardButton("Updates 📢", url="https://t.me/RoboKaty"), 
         InlineKeyboardButton("Support 💬", url="https://t.me/SupportGroup")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="open_start")]
    ])

# --- Handlers ---

@Client.on_message(filters.command("start", PREFIXES))
async def start_handler(c: Client, m: Message):
    # Screenshot 2 wala interface dikhayega
    await m.reply_text(
        text=START_TEXT.format(name=m.from_user.first_name),
        reply_markup=start_buttons(c.me.username)
    )

@Client.on_callback_query(filters.regex("open_help"))
async def help_callback(c: Client, cb: CallbackQuery):
    # Screenshot 1 wala interface (Help Menu)
    await cb.edit_message_text(
        text=HELP_TEXT,
        reply_markup=back_button()
    )

@Client.on_callback_query(filters.regex("open_start"))
async def start_callback(c: Client, cb: CallbackQuery):
    # Wapas Main Menu par jaane ke liye
    await cb.edit_message_text(
        text=START_TEXT.format(name=cb.from_user.first_name),
        reply_markup=start_buttons(c.me.username)
    )
    
