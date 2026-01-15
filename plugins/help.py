# plugins/help.py
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_callback_query(filters.regex("help_menu"))
async def help_ui(c, cb):
    help_text = (
        "📖 **Available Commands:**\n\n"
        "• `/start` — Show main menu\n"
        "• `/auth` — Exempt a user (Admins)\n"
        "• `/abuse` — Toggle abuse filter\n"
        "• `/delay` — Set deletion delay\n\n"
        "📝 *Note: Default media deletion time is 1 hour.*"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="start_back")]
    ])
    
    await cb.message.edit_text(help_text, reply_markup=buttons)
  
