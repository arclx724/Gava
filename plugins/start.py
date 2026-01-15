# plugins/start.py
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

@Client.on_message(filters.command("start") & filters.private)
async def start_private(c: Client, m: Message):
    text = (
        f"🔐 Hello **{m.from_user.first_name}**, welcome to **Security Bot**!\n\n"
        "✨ **Your Personal Chat Bodyguard is here!**\n\n"
        "🚀 **Features:**\n"
        "• Instantly deletes edited messages.\n"
        "• Auto-removes all types of media.\n"
        "• Cleans abusive, harmful words.\n"
        "• Flexible admin controls."
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Secure Your Chat", url=f"https://t.me/{c.me.username}?startgroup=true")],
        [InlineKeyboardButton("📜 Help & Commands", callback_data="help_menu")],
        [InlineKeyboardButton("Updates 📢", url="https://t.me/RoboKaty"), 
         InlineKeyboardButton("Support 💬", url="https://t.me/SupportGroup")]
    ])
    
    await m.reply_text(text, reply_markup=buttons)

# Callback for "Back to Menu"
@Client.on_callback_query(filters.regex("start_back"))
async def back_to_start(c, cb):
    # Wahi logic jo upar start mein hai (edit_message_text ke sath)
    await cb.message.edit_text("Welcome back!", reply_markup=start_buttons)
  
