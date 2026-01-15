# SPDX-License-Identifier: MIT
# Copyright (c) 2018-2024 Amano LLC

import asyncio
import re
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from hydrogram import Client, filters
from hydrogram.enums import ChatMemberStatus, ParseMode
from hydrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ChatPrivileges
)

from config import PREFIXES, SUDOERS
from eduu.utils import commands, get_target_user
from eduu.utils.decorators import require_admin
from eduu.utils.localization import use_chat_lang

# ---------------- CONFIGURATION ---------------- #

# OpenRouter API Key
OPENROUTER_API_KEY = "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" 
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# MongoDB Connection
MONGO_URI = "mongodb+srv://arclx724_db_user:arclx724_db_user@cluster0.czhpczm.mongodb.net/?appName=Cluster0"

# Connect to Database
mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.get_default_database("Cluster0")

# Collections
abuse_col = db["abuse_settings"]
auth_col = db["auth_users"]

# Abusive Words List
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

# ---------------- DATABASE FUNCTIONS ---------------- #

async def is_abuse_enabled(chat_id: int) -> bool:
    doc = await abuse_col.find_one({"chat_id": chat_id})
    return doc.get("enabled", False) if doc else False

async def set_abuse_status(chat_id: int, enabled: bool):
    await abuse_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled}},
        upsert=True
    )

async def is_user_whitelisted(chat_id: int, user_id: int) -> bool:
    doc = await auth_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return bool(doc)

async def add_whitelist(chat_id: int, user_id: int):
    await auth_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"timestamp": asyncio.get_event_loop().time()}},
        upsert=True
    )

async def remove_whitelist(chat_id: int, user_id: int):
    await auth_col.delete_one({"chat_id": chat_id, "user_id": user_id})

async def get_whitelisted_users(chat_id: int):
    return auth_col.find({"chat_id": chat_id})

async def remove_all_whitelist(chat_id: int):
    await auth_col.delete_many({"chat_id": chat_id})

# ---------------- AI HELPER ---------------- #

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
            await m.reply_text(strings("abuse_invalid_arg"))
            return
    else:
        current_status = await is_abuse_enabled(m.chat.id)
        new_status = not current_status

    await set_abuse_status(m.chat.id, new_status)
    
    if new_status:
        await m.reply_text("Abuse protection has been enabled ✅")
    else:
        await m.reply_text("Abuse protection has been disabled ❌")


@Client.on_message(filters.command(["auth", "promote"], PREFIXES) & filters.group)
@use_chat_lang
async def auth_user_handler(c: Client, m: Message, strings):
    if m.from_user.id not in SUDOERS:
        await m.reply_text(strings("abuse_sudo_only"))
        return

    target_user = await get_target_user(c, m)
    if not target_user:
        await m.reply_text(strings("abuse_no_user"))
        return

    await add_whitelist(m.chat.id, target_user.id)
    # Using Markdown format manual construction
    user_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    await m.reply_text(strings("abuse_user_authed").format(user=user_mention))


@Client.on_message(filters.command("unauth", PREFIXES) & filters.group)
@use_chat_lang
async def unauth_user_handler(c: Client, m: Message, strings):
    if m.from_user.id not in SUDOERS:
        await m.reply_text(strings("abuse_sudo_only"))
        return

    target_user = await get_target_user(c, m)
    if not target_user:
        await m.reply_text(strings("abuse_no_user"))
        return

    await remove_whitelist(m.chat.id, target_user.id)
    # Using Markdown format manual construction
    user_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    await m.reply_text(strings("abuse_user_unauthed").format(user=user_mention))


@Client.on_message(filters.command("authlist", PREFIXES) & filters.group)
@use_chat_lang
async def authlist_handler(c: Client, m: Message, strings):
    if m.from_user.id not in SUDOERS:
        await m.reply_text(strings("abuse_sudo_only"))
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
        await m.reply_text(strings("abuse_authlist_empty"))
    else:
        await m.reply_text(strings("abuse_authlist_header") + "\n- " + "\n- ".join(users))


@Client.on_message(filters.command("unauthall", PREFIXES) & filters.group)
@use_chat_lang
async def unauthall_handler(c: Client, m: Message, strings):
    member = await m.chat.get_member(m.from_user.id)
    if member.status != ChatMemberStatus.OWNER and m.from_user.id not in SUDOERS:
        await m.reply_text(strings("abuse_owner_only"))
        return

    await remove_all_whitelist(m.chat.id)
    await m.reply_text(strings("abuse_authlist_cleared"))


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
    
    # 3. Check Local List (Hinglish) & Apply MARKDOWN Spoiler
    for word in ABUSIVE_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        if pattern.search(censored_text):
            detected_abuse = True
            # ||word|| pixelated spoiler ke liye
            censored_text = pattern.sub(lambda match: f"||{match.group(0)}||", censored_text)
    
    # 4. Check AI if not locally detected (Fallback)
    if not detected_abuse:
        if await check_toxicity_ai(text):
            detected_abuse = True
            # AI case mein pure text ko spoiler mein daal do
            censored_text = f"||{text}||"

    # 5. Action
    if detected_abuse:
        try:
            await m.delete()

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{c.me.username}?startgroup=true"),
                        InlineKeyboardButton("📢 Updates", url="https://t.me/RoboKaty"),
                    ]
                ]
            )

            # Warning Message Creation (MARKDOWN FORMAT FIXED)
            # Hum user mention manually bana rahe hain: [Name](tg://user?id=123)
            # Taaki ye ParseMode.MARKDOWN ke saath perfect chale
            user_link = f"[{m.from_user.first_name}](tg://user?id={m.from_user.id})"

            warning_text = (
                f"🚫 Hey {user_link}, your message was removed.\n\n"
                f"🔍 **Censored:**\n{censored_text}\n\n"
                f"Please keep the chat respectful."
            )

            # ParseMode.MARKDOWN hi rakha hai taaki ||spoiler|| aur [Name](Link) dono chalein
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


# ---------------- REGISTRATION ---------------- #

commands.add_command("abuse", "admin")
commands.add_command("auth", "admin")
commands.add_command("promote", "admin")
commands.add_command("unauth", "admin")
commands.add_command("authlist", "admin")
commands.add_command("unauthall", "admin")
      
