import asyncio
import re
import aiohttp

from hydrogram import Client, filters
from hydrogram.enums import ChatMemberStatus, ParseMode
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatPrivileges

# Humne ye details config aur database se import kar li hain
from config import PREFIXES, SUDOERS, OPENROUTER_API_KEY
from database import (
    is_abuse_enabled, set_abuse_status, is_user_whitelisted, 
    add_whitelist, remove_whitelist, get_whitelisted_users, remove_all_whitelist
)
from eduu.utils import commands, get_target_user
from eduu.utils.decorators import require_admin
from eduu.utils.localization import use_chat_lang

# API URL for AI
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Abusive Words List (Aapki original list)
ABUSIVE_WORDS = [
    "madarchod", "Madharchod", "Madharchood", "behenchod", "madherchood", "madherchod", "bhenchod", "maderchod", "mc", "bc", "bsdk", 
    "bhosdike", "bhosdiwala", "chutiya", "chutiyapa", "gandu", "gand", 
    "lodu", "lode", "lauda", "lund", "lawda", "lavda", "aand", "jhant", 
    "jhaant", "chut", "chuchi", "tatte", "tatti", "gaand", "gaandmar", 
    "gaandmasti", "gaandfat", "gaandmara", "kamina", "kamine", "harami", 
    "haraami", "nalayak", "nikamma", "kutte", "kutta", "kutti", "saala", 
    "saali", "bhadwa", "bhadwe", "randi", "randibaaz", "bkl", "l*da", 
    "l@da", "ch*tiya", "g@ndu", "behench*d", "bhench0d", "madarxhod", 
    "chutya", "chuteya", "rand", "ramdi", "choot", "bhosda", "fuck", 
    "bitch", "bastard", "asshole", "motherfucker", "dick", "tmkc", "mkc"
]

# ---------------- AI HELPER (Wahi original logic) ---------------- #

async def check_toxicity_ai(text: str) -> bool:
    if not text:
        return False
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org", 
    }
    
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [
            {
                "role": "system", 
                "content": "You are a content filter. Reply ONLY with 'YES' if the message contains hate speech, severe abuse, or extreme profanity. Reply 'NO' if safe."
            },
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 5
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data['choices'][0]['message']['content'].strip().upper()
                    return "YES" in answer
    except Exception:
        pass
    return False

# ---------------- COMMAND HANDLERS ---------------- #

@Client.on_message(filters.command("abuse", PREFIXES) & filters.group)
@require_admin(ChatPrivileges(can_change_info=True))
@use_chat_lang
async def toggle_abuse_handler(c: Client, m: Message, strings):
    if len(m.command) > 1:
        arg = m.command[1].lower()
        if arg in ["on", "enable", "yes"]:
            new_status = True
        elif arg in ["off", "disable", "no"]:
            new_status = False
        else:
            await m.reply_text("Invalid argument! Use on/off.")
            return
    else:
        current_status = await is_abuse_enabled(m.chat.id)
        new_status = not current_status

    await set_abuse_status(m.chat.id, new_status)
    status_text = "enabled ✅" if new_status else "disabled ❌"
    await m.reply_text(f"Abuse protection has been {status_text}")


@Client.on_message(filters.command(["auth", "promote"], PREFIXES) & filters.group)
@use_chat_lang
async def auth_user_handler(c: Client, m: Message, strings):
    if m.from_user.id not in SUDOERS:
        await m.reply_text("This command is for Sudoers only.")
        return

    target_user = await get_target_user(c, m)
    if not target_user:
        await m.reply_text("Please reply to a user or provide their ID.")
        return

    await add_whitelist(m.chat.id, target_user.id)
    user_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    await m.reply_text(f"User {user_mention} has been authorized.")


@Client.on_message(filters.command("unauth", PREFIXES) & filters.group)
@use_chat_lang
async def unauth_user_handler(c: Client, m: Message, strings):
    if m.from_user.id not in SUDOERS:
        await m.reply_text("This command is for Sudoers only.")
        return

    target_user = await get_target_user(c, m)
    if not target_user:
        await m.reply_text("Please reply to a user or provide their ID.")
        return

    await remove_whitelist(m.chat.id, target_user.id)
    user_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    await m.reply_text(f"User {user_mention} has been unauthorized.")


@Client.on_message(filters.command("authlist", PREFIXES) & filters.group)
@use_chat_lang
async def authlist_handler(c: Client, m: Message, strings):
    if m.from_user.id not in SUDOERS:
        await m.reply_text("This command is for Sudoers only.")
        return

    cursor = await get_whitelisted_users(m.chat.id)
    users = []
    async for doc in cursor:
        try:
            user = await c.get_users(doc["user_id"])
            users.append(f"[{user.first_name}](tg://user?id={user.id})")
        except Exception:
            users.append(f"ID: {doc['user_id']}")
    
    if not users:
        await m.reply_text("Authlist is empty.")
    else:
        await m.reply_text("Authorized Users:\n- " + "\n- ".join(users))


@Client.on_message(filters.command("unauthall", PREFIXES) & filters.group)
@use_chat_lang
async def unauthall_handler(c: Client, m: Message, strings):
    member = await m.chat.get_member(m.from_user.id)
    if member.status != ChatMemberStatus.OWNER and m.from_user.id not in SUDOERS:
        await m.reply_text("Only the owner can clear the list.")
        return

    await remove_all_whitelist(m.chat.id)
    await m.reply_text("All authorized users have been removed.")


# ---------------- MESSAGE WATCHER ---------------- #

@Client.on_message(filters.text & filters.group & ~filters.bot & ~filters.service, group=10)
@use_chat_lang
async def abuse_watcher(c: Client, m: Message, strings):
    if not await is_abuse_enabled(m.chat.id):
        return

    if not m.from_user:
        return

    if m.from_user.id in SUDOERS or await is_user_whitelisted(m.chat.id, m.from_user.id):
        return

    text = m.text or ""
    censored_text = text
    detected_abuse = False
    
    # Check Local List
    for word in ABUSIVE_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        if pattern.search(censored_text):
            detected_abuse = True
            censored_text = pattern.sub(lambda match: f"||{match.group(0)}||", censored_text)
    
    # Check AI if not locally detected
    if not detected_abuse:
        if await check_toxicity_ai(text):
            detected_abuse = True
            censored_text = f"||{text}||"

    if detected_abuse:
        try:
            await m.delete()
            user_link = f"[{m.from_user.first_name}](tg://user?id={m.from_user.id})"
            warning_text = (
                f"🚫 Hey {user_link}, your message was removed.\n\n"
                f"🔍 **Censored:**\n{censored_text}\n\n"
                f"Please keep the chat respectful."
            )
            
            buttons = InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{c.me.username}?startgroup=true"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/RoboKaty")
            ]])

            warning_msg = await c.send_message(
                chat_id=m.chat.id,
                text=warning_text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN
            )

            await asyncio.sleep(60)
            await warning_msg.delete()

        except Exception as e:
            print(f"Abuse filter error: {e}")

# Register commands
commands.add_command("abuse", "admin")
commands.add_command("auth", "admin")
commands.add_command("promote", "admin")
commands.add_command("unauth", "admin")
commands.add_command("authlist", "admin")
commands.add_command("unauthall", "admin")
    
