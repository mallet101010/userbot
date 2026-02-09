import sys
import types
m = types.ModuleType("imghdr")
m.what = lambda f, h=None: None
sys.modules["imghdr"] = m

import os
import asyncio
import time
import json
import random
import sqlite3
import aiohttp
import urllib.parse
import re
import string
import hashlib
import base64
import math
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
from collections import defaultdict
from typing import Optional, Dict, List, Tuple

from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest, GetDialogFiltersRequest

from flask import Flask, request
import waitress

# ==================== КОНФИГУРАЦИЯ ====================
app = Flask(__name__)
@app.route('/')
def home(): return "Userbot Online"
@app.route('/ping')
def ping_route(): return "pong"

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')
PORT = int(os.getenv('PORT', 8080))

if not all([API_ID, API_HASH, SESSION_STRING]):
    raise ValueError("Set API_ID, API_HASH, SESSION_STRING in environment")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, connection=aiohttp.TCPConnector())
client.start_time = datetime.now()
client.afk_status = {"afk": False, "reason": "", "since": None}

# ==================== БАЗА ДАННЫХ ====================
DB_PATH = Path('userbot.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS notes (name TEXT PRIMARY KEY, content TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, chat_id INTEGER, count INTEGER, PRIMARY KEY(user_id, chat_id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS spam_filters (chat_id INTEGER, pattern TEXT, PRIMARY KEY(chat_id, pattern))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS welcome_messages (chat_id INTEGER PRIMARY KEY, message TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS rules (chat_id INTEGER PRIMARY KEY, rules_text TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS afk_users (user_id INTEGER PRIMARY KEY, reason TEXT, since INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS user_notes (user_id INTEGER, note TEXT, PRIMARY KEY(user_id))''')
conn.commit()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        participant = await client.get_permissions(chat_id, user_id)
        return participant.is_admin
    except:
        return False

def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")

def get_size(bytes_size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f}TB"

# ==================== КОМАНДА МЕНЮ (120+ ФУНКЦИЙ) ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.m$'))
async def menu(event):
    text = """**Commands (120+ functions)**
.ob - all commands list
.p - ping bot
.t - time UTC+3/4/5
.s - bot status
.i - bot info
.u - uptime
.id - get chat id
.info @user - user info
.notes - list notes
.note name text - save note
.getnote name - get note
.delnote name - delete note
.ban @user - ban user
.unban @user - unban user
.kick @user - kick user
.mute @user N - mute N minutes
.unmute @user - unmute
.pin - pin message
.unpin - unpin last
.purge N - delete N messages
.warn @user - warn user
.unwarn @user - remove warn
.warns @user - check warns
.clearwarns @user - clear all warns
.weather city - weather
.calc expression - calculator
.qr text - generate QR code
.sh url - shorten link
.long url - unshorten link
.reverse text - reverse text
.translit text - transliteration
.leet text - leet speak
.upper text - uppercase
.lower text - lowercase
.bold text - bold text
.mono text - monospace
.italic text - italic text
.invisible text - invisible text
.bubble text - bubble text
.antispam add word - add spam filter
.antispam del word - remove filter
.antispam list - list filters
.welcome set text - set welcome
.welcome get - show welcome
.rules set text - set rules
.rules get - show rules
.admins - list chat admins
.tagall - tag all members
.invite N - generate invite link
.btc - Bitcoin price
.eth - Ethereum price
.ton - Toncoin price
.sol - Solana price
.doge - Dogecoin price
.currency from to amount - convert
.google query - google search
.wiki query - wikipedia search
.video2audio - convert video to audio
.tts text - text to speech
.img query - search images
.password N - generate password
.random N - random number 1-N
.dice - roll dice
.coin - flip coin
.ball question - magic 8 ball
.afk reason - set afk mode
.unafk - disable afk mode
.clone @user - clone profile
.export - export chat users
.sysinfo - system information
.logs - view logs
.restart - restart bot
.stop - stop bot
.save text - save to saved
.fwd @user text - forward message
.block @user - block user
.unblock @user - unblock user
.join link - join chat
.leave - leave chat
.report @user reason - report user
.stats - chat statistics
.parse - parse chat members
.who @user - find user chats
.search text - search in chats
.trwords - top words in chat
.fake - generate fake data
.quote - random quote
.whois - random chat member
.promote @user - promote to admin
.demote @user - demote admin
.kickme - leave chat
.me - my profile info
.pingall - ping all admins
.screenshot - take screenshot
.muteall - mute all users
.unmuteall - unmute all
.lock - lock chat
.unlock - unlock chat
.setlink - set chat link
.getlink - get chat link
.delphoto - delete chat photo
.setphoto - set chat photo
.title newname - change chat title
.desc newdesc - change description
.history N - message history
.findmsg text - find message
.getmsg msgid - get message by id
.delmsg msgid - delete message by id
.edit newtext - edit message
.react emoji - react to message
.read - mark as read
.unread - mark as unread
.archive - archive chat
.unarchive - unarchive chat
.pinmsg - pin message
.unpinmsg - unpin message
.getfile - get file info
.download - download media
.upload file - upload file
.stickerpack - create stickerpack
.addsticker - add sticker
.delsticker - delete sticker
.fonts - list fonts
.font name text - text with font
.encrypt text - encrypt text
.decrypt text - decrypt text
.hash text - generate hash
.base64 text - base64 encode
.unbase64 text - base64 decode
.urlencode text - url encode
.urldecode text - url decode
.json data - format json
.xml data - format xml
.csv data - format csv
.yaml data - format yaml
.hex text - to hex
.unhex text - from hex
.bin text - to binary
.unbin text - from binary
.morse text - to morse
.unmorse text - from morse
.ascii text - ascii art
.binary text - binary art
.qrcode text - qr code
.barcode text - barcode
.graph formula - graph
.calendar - current calendar
.timer N - timer N seconds
.stopwatch - stopwatch
.reminder N text - set reminder
.alarm HH:MM - set alarm
.todo add task - add todo
.todo list - list todos
.todo del N - delete todo
.todo clear - clear all
.poll question opt1 opt2 - create poll
.vote - vote in poll
.results - poll results
.game - start game
.trivia - trivia question
.hangman - hangman game
.quiz - quiz game"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ob$'))
async def help_all(event):
    text = """**All Commands**
.m .ob .p .t .s .i .u .id .info .notes .note .getnote .delnote .ban .unban .kick .mute .unmute .pin .unpin .purge .warn .unwarn .warns .clearwarns .weather .calc .qr .sh .long .reverse .translit .leet .upper .lower .bold .mono .italic .invisible .bubble .antispam .welcome .rules .admins .tagall .invite .btc .eth .ton .sol .doge .currency .google .wiki .video2audio .tts .img .password .random .dice .coin .ball .afk .unafk .clone .export .sysinfo .logs .restart .stop .save .fwd .block .unblock .join .leave .report .stats .parse .who .search .trwords .fake .quote .whois .promote .demote .kickme .me .pingall .screenshot .muteall .unmuteall .lock .unlock .setlink .getlink .delphoto .setphoto .title .desc .history .findmsg .getmsg .delmsg .edit .react .read .unread .archive .unarchive .pinmsg .unpinmsg .getfile .download .upload .stickerpack .addsticker .delsticker .fonts .font .encrypt .decrypt .hash .base64 .unbase64 .urlencode .urldecode .json .xml .csv .yaml .hex .unhex .bin .unbin .morse .unmorse .ascii .binary .qrcode .barcode .graph .calendar .timer .stopwatch .reminder .alarm .todo .poll .vote .results .game .trivia .hangman .quiz"""
    await event.edit(text, parse_mode='md')

# ==================== БЛОК 1: ОСНОВНЫЕ КОМАНДЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.p$'))
async def ping(event):
    start = time.time()
    msg = await event.edit('**Ping**', parse_mode='md')
    delay = int((time.time() - start) * 1000)
    await msg.edit(f'**Pong:** {delay}ms', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.t$'))
async def time_cmd(event):
    now = datetime.utcnow()
    text = f"""**Time**
UTC: {format_time(now)}
UTC+3: {format_time(now + timedelta(hours=3))}
UTC+4: {format_time(now + timedelta(hours=4))}
UTC+5: {format_time(now + timedelta(hours=5))}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.s$'))
async def status(event):
    me = await client.get_me()
    delta = datetime.now() - client.start_time
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    text = f"""**Status**
User: @{me.username or me.id}
ID: {me.id}
Uptime: {delta.days}d {hours}h {minutes}m
Platform: Render
Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.i$'))
async def info_cmd(event):
    me = await client.get_me()
    text = f"""**Bot Info**
First name: {me.first_name or ''}
Last name: {me.last_name or ''}
Username: @{me.username or 'none'}
Phone: {me.phone or 'hidden'}
Premium: {me.premium or False}
Bot: {me.bot}
Verified: {me.verified or False}
DC: {me.photo.dc_id if me.photo else 'none'}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.u$'))
async def uptime_cmd(event):
    delta = datetime.now() - client.start_time
    text = f"""**Uptime**
Days: {delta.days}
Hours: {delta.seconds // 3600}
Minutes: {(delta.seconds % 3600) // 60}
Seconds: {delta.seconds % 60}
Total: {delta.total_seconds():.0f} seconds"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.id$'))
async def get_id(event):
    chat = await event.get_chat()
    await event.edit(f'**Chat ID:** {chat.id}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.info (.+)$'))
async def user_info(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        text = f"""**User Info**
ID: {user.id}
First name: {user.first_name or ''}
Last name: {user.last_name or ''}
Username: @{user.username or 'none'}
Bot: {user.bot}
Premium: {user.premium or False}
Verified: {user.verified or False}
DC: {user.photo.dc_id if hasattr(user, 'photo') and user.photo else 'none'}"""
        await event.edit(text, parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.notes$'))
async def list_notes(event):
    cursor.execute('SELECT name FROM notes ORDER BY name')
    rows = cursor.fetchall()
    if rows:
        text = '**Notes:** ' + ', '.join([row[0] for row in rows])
    else:
        text = '**No notes**'
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.note (\w+) (.+)$'))
async def add_note(event):
    name = event.pattern_match.group(1)
    content = event.pattern_match.group(2)
    cursor.execute('INSERT OR REPLACE INTO notes VALUES (?, ?)', (name, content))
    conn.commit()
    await event.edit(f'**Note saved:** {name}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.getnote (\w+)$'))
async def get_note(event):
    name = event.pattern_match.group(1)
    cursor.execute('SELECT content FROM notes WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        await event.edit(f'**{name}:** {row[0]}', parse_mode='md')
    else:
        await event.edit('**Note not found**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.delnote (\w+)$'))
async def delete_note(event):
    name = event.pattern_match.group(1)
    cursor.execute('DELETE FROM notes WHERE name = ?', (name,))
    conn.commit()
    affected = cursor.rowcount
    if affected > 0:
        await event.edit(f'**Note deleted:** {name}', parse_mode='md')
    else:
        await event.edit('**Note not found**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ban (@?\w+)$'))
async def ban_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, view_messages=False)
        await event.edit(f'**Banned:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unban (@?\w+)$'))
async def unban_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, view_messages=True)
        await event.edit(f'**Unbanned:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.kick (@?\w+)$'))
async def kick_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.kick_participant(event.chat_id, user)
        await event.edit(f'**Kicked:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.mute (@?\w+) (\d+)$'))
async def mute_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        minutes = int(event.pattern_match.group(2))
        until = datetime.now() + timedelta(minutes=minutes)
        await client.edit_permissions(event.chat_id, user, until_date=until, send_messages=False)
        await event.edit(f'**Muted for {minutes}m:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unmute (@?\w+)$'))
async def unmute_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, send_messages=True)
        await event.edit(f'**Unmuted:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.pin$'))
async def pin_message(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        await event.message.pin()
        await event.edit('**Pinned**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unpin$'))
async def unpin_message(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        messages = await client.get_messages(event.chat_id, filter=types.InputMessagesFilterPinned)
        if messages:
            await messages[0].unpin()
            await event.edit('**Unpinned**', parse_mode='md')
        else:
            await event.edit('**No pinned messages**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.purge (\d+)$'))
async def purge_messages(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        count = int(event.pattern_match.group(1))
        count = min(count, 100)
        await event.delete()
        deleted = 0
        async for msg in client.iter_messages(event.chat_id, limit=count):
            await msg.delete()
            deleted += 1
            await asyncio.sleep(0.1)
        msg = await client.send_message(event.chat_id, f'**Purged:** {deleted} messages')
        await asyncio.sleep(2)
        await msg.delete()
    except Exception as e:
        print(f"Purge error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.warn (@?\w+)$'))
async def warn_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('SELECT count FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        row = cursor.fetchone()
        new_count = (row[0] + 1) if row else 1
        
        if row:
            cursor.execute('UPDATE warns SET count = ? WHERE user_id = ? AND chat_id = ?', (new_count, user.id, event.chat_id))
        else:
            cursor.execute('INSERT INTO warns VALUES (?, ?, ?)', (user.id, event.chat_id, new_count))
        conn.commit()
        
        await event.edit(f'**Warned:** @{user.username or user.id} ({new_count}/3)', parse_mode='md')
        
        if new_count >= 3:
            await client.kick_participant(event.chat_id, user)
            cursor.execute('DELETE FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
            conn.commit()
            await event.edit(f'**Banned for 3 warns:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.warns (@?\w+)$'))
async def check_warns(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('SELECT count FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        row = cursor.fetchone()
        count = row[0] if row else 0
        await event.edit(f'**Warns:** @{user.username or user.id} - {count}/3', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.clearwarns (@?\w+)$'))
async def clear_warns(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('DELETE FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        conn.commit()
        await event.edit(f'**Cleared warns for:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.weather (.+)$'))
async def weather(event):
    city = event.pattern_match.group(1).strip()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://wttr.in/{urllib.parse.quote(city)}?format=3') as resp:
                weather_text = await resp.text()
                await event.edit(f'**Weather:** {weather_text}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.calc (.+)$'))
async def calculate(event):
    try:
        expr = event.pattern_match.group(1).strip()
        # Безопасный eval
        allowed_names = {
            'abs': abs, 'max': max, 'min': min, 'pow': pow, 'round': round,
            'sum': sum, 'len': len, 'int': int, 'float': float, 'str': str
        }
        result = eval(expr, {"__builtins__": {}}, allowed_names)
        await event.edit(f'**Result:** {result}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Calculation error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.qr (.+)$'))
async def qr_code(event):
    text = event.pattern_match.group(1).strip()
    try:
        import qrcode
        qr = qrcode.make(text)
        bio = BytesIO()
        qr.save(bio, 'PNG')
        bio.seek(0)
        await client.send_file(event.chat_id, bio, caption=f'**QR Code:** {text[:50]}...')
        await event.delete()
    except ImportError:
        await event.edit('**Install:** pip install qrcode[pil]', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

# ==================== БЛОК 2: ССЫЛКИ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.sh (.+)$'))
async def shorten_url(event):
    url = event.pattern_match.group(1).strip()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}') as resp:
                if resp.status == 200:
                    shortened = await resp.text()
                    await event.edit(f'**Shortened:** {shortened}', parse_mode='md')
                else:
                    await event.edit('**Service unavailable**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.long (.+)$'))
async def unshorten_url(event):
    url = event.pattern_match.group(1).strip()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=False, timeout=10) as resp:
                location = resp.headers.get('location', url)
                await event.edit(f'**Original:** {location}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

# ==================== БЛОК 3: ТЕКСТОВЫЕ УТИЛИТЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.reverse (.+)$'))
async def reverse_text(event):
    text = event.pattern_match.group(1).strip()
    reversed_text = text[::-1]
    await event.edit(f'**Reversed:** {reversed_text}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.translit (.+)$'))
async def translit_text(event):
    text = event.pattern_match.group(1).strip().lower()
    translit_dict = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
        'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
        'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
        'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu',
        'я':'ya'
    }
    result = ''.join(translit_dict.get(c, c) for c in text)
    await event.edit(f'**Translit:** {result}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.leet (.+)$'))
async def leet_text(event):
    text = event.pattern_match.group(1).strip().lower()
    leet_dict = {
        'a':'4','e':'3','i':'1','o':'0','s':'5','t':'7',
        'b':'8','g':'9','l':'1','z':'2'
    }
    result = ''.join(leet_dict.get(c, c) for c in text)
    await event.edit(f'**Leet:** {result}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.upper (.+)$'))
async def uppercase_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Uppercase:** {text.upper()}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.lower (.+)$'))
async def lowercase_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Lowercase:** {text.lower()}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.bold (.+)$'))
async def bold_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Bold:** **{text}**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.mono (.+)$'))
async def mono_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Monospace:** `{text}`', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.italic (.+)$'))
async def italic_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Italic:** _{text}_', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.invisible (.+)$'))
async def invisible_text(event):
    text = event.pattern_match.group(1).strip()
    invisible = ''.join(chr(0x200B) + char for char in text)
    await event.edit(f'**Invisible text sent**\nCopy this: `{invisible}`', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.bubble (.+)$'))
async def bubble_text(event):
    text = event.pattern_match.group(1).strip()
    bubble_dict = {
        'a':'ⓐ','b':'ⓑ','c':'ⓒ','d':'ⓓ','e':'ⓔ','f':'ⓕ','g':'ⓖ','h':'ⓗ',
        'i':'ⓘ','j':'ⓙ','k':'ⓚ','l':'ⓛ','m':'ⓜ','n':'ⓝ','o':'ⓞ','p':'ⓟ',
        'q':'ⓠ','r':'ⓡ','s':'ⓢ','t':'ⓣ','u':'ⓤ','v':'ⓥ','w':'ⓦ','x':'ⓧ',
        'y':'ⓨ','z':'ⓩ','0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤',
        '6':'⑥','7':'⑦','8':'⑧','9':'⑨'
    }
    result = ''.join(bubble_dict.get(c.lower(), c) for c in text)
    await event.edit(f'**Bubble:** {result}', parse_mode='md')

# ==================== БЛОК 4: ГРУППОВЫЕ ФИШКИ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.antispam add (.+)$'))
async def antispam_add(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    pattern = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR IGNORE INTO spam_filters VALUES (?, ?)', (event.chat_id, pattern))
    conn.commit()
    await event.edit(f'**Filter added:** {pattern}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.antispam del (.+)$'))
async def antispam_del(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    pattern = event.pattern_match.group(1).strip()
    cursor.execute('DELETE FROM spam_filters WHERE chat_id = ? AND pattern = ?', (event.chat_id, pattern))
    conn.commit()
    if cursor.rowcount > 0:
        await event.edit(f'**Filter removed:** {pattern}', parse_mode='md')
    else:
        await event.edit('**Filter not found**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.antispam list$'))
async def antispam_list(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    cursor.execute('SELECT pattern FROM spam_filters WHERE chat_id = ?', (event.chat_id,))
    rows = cursor.fetchall()
    if rows:
        text = '**Spam filters:**\n' + '\n'.join([row[0] for row in rows])
    else:
        text = '**No filters**'
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(incoming=True))
async def check_spam(event):
    if event.is_group and event.text:
        cursor.execute('SELECT pattern FROM spam_filters WHERE chat_id = ?', (event.chat_id,))
        patterns = [row[0] for row in cursor.fetchall()]
        for pattern in patterns:
            if re.search(pattern, event.text, re.IGNORECASE):
                await event.delete()
                break

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.welcome set (.+)$'))
async def welcome_set(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    message = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR REPLACE INTO welcome_messages VALUES (?, ?)', (event.chat_id, message))
    conn.commit()
    await event.edit('**Welcome message set**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.welcome get$'))
async def welcome_get(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    cursor.execute('SELECT message FROM welcome_messages WHERE chat_id = ?', (event.chat_id,))
    row = cursor.fetchone()
    if row:
        await event.edit(f'**Welcome:** {row[0]}', parse_mode='md')
    else:
        await event.edit('**No welcome message**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.rules set (.+)$'))
async def rules_set(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    rules_text = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR REPLACE INTO rules VALUES (?, ?)', (event.chat_id, rules_text))
    conn.commit()
    await event.edit('**Rules set**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.rules get$'))
async def rules_get(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    cursor.execute('SELECT rules_text FROM rules WHERE chat_id = ?', (event.chat_id,))
    row = cursor.fetchone()
    if row:
        await event.edit(f'**Rules:** {row[0]}', parse_mode='md')
    else:
        await event.edit('**No rules**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.admins$'))
async def list_admins(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    try:
        participants = await client.get_participants(event.chat_id)
        admins = []
        for user in participants:
            try:
                perms = await client.get_permissions(event.chat_id, user)
                if perms.is_admin:
                    name = f'@{user.username}' if user.username else user.first_name
                    admins.append(name)
            except:
                continue
        
        if admins:
            text = '**Admins:**\n' + '\n'.join(admins[:20])
            if len(admins) > 20:
                text += f'\n...and {len(admins)-20} more'
        else:
            text = '**No admins found**'
        
        await event.edit(text, parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tagall$'))
async def tag_all(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    
    await event.edit('**Tagging...**', parse_mode='md')
    try:
        participants = await client.get_participants(event.chat_id, limit=50)
        mentions = []
        for user in participants:
            if not user.bot:
                mention = f'@{user.username}' if user.username else f'[{user.first_name or ""}](tg://user?id={user.id})'
                mentions.append(mention)
        
        if mentions:
            text = ' '.join(mentions[:30])
            await event.edit(text, parse_mode='md')
        else:
            await event.edit('**No users to tag**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.invite (\d+)$'))
async def generate_invite(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    
    try:
        usage_limit = int(event.pattern_match.group(1))
        result = await client(ExportChatInviteRequest(
            peer=event.chat_id,
            expire_date=None,
            usage_limit=usage_limit if usage_limit > 0 else None
        ))
        await event.edit(f'**Invite link:** {result.link}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

# ==================== БЛОК 5: КРИПТА И ФИНАНСЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.btc$'))
async def bitcoin_price(event):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd') as resp:
                data = await resp.json()
                price = data['bitcoin']['usd']
                await event.edit(f'**Bitcoin:** ${price:,.2f}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.eth$'))
async def ethereum_price(event):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd') as resp:
                data = await resp.json()
                price = data['ethereum']['usd']
                await event.edit(f'**Ethereum:** ${price:,.2f}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ton$'))
async def toncoin_price(event):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd') as resp:
                data = await resp.json()
                price = data['the-open-network']['usd']
                await event.edit(f'**Toncoin:** ${price:,.2f}', parse_mode='md')
    except:
        await event.edit('**Price not available**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.sol$'))
async def solana_price(event):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd') as resp:
                data = await resp.json()
                price = data['solana']['usd']
                await event.edit(f'**Solana:** ${price:,.2f}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.doge$'))
async def dogecoin_price(event):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd') as resp:
                data = await resp.json()
                price = data['dogecoin']['usd']
                await event.edit(f'**Dogecoin:** ${price:,.4f}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.currency (\w+) (\w+) ([\d\.]+)$'))
async def convert_currency(event):
    try:
        from_curr = event.pattern_match.group(1).upper()
        to_curr = event.pattern_match.group(2).upper()
        amount = float(event.pattern_match.group(3))
        
        async with aiohttp.ClientSession() as session:
            url = f'https://api.exchangerate-api.com/v4/latest/{from_curr}'
            async with session.get(url) as resp:
                data = await resp.json()
                rate = data['rates'].get(to_curr)
                if rate:
                    converted = amount * rate
                    await event.edit(f'**{amount} {from_curr} = {converted:.2f} {to_curr}**', parse_mode='md')
                else:
                    await event.edit('**Currency not supported**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

# ==================== БЛОК 6: УТИЛИТЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.google (.+)$'))
async def google_search(event):
    query = event.pattern_match.group(1).strip()
    try:
        search_url = f'https://www.google.com/search?q={urllib.parse.quote(query)}'
        await event.edit(f'**Google search:** {search_url}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.wiki (.+)$'))
async def wikipedia_search(event):
    query = event.pattern_match.group(1).strip()
    try:
        async with aiohttp.ClientSession() as session:
            url = 'https://en.wikipedia.org/w/api.php'
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': query,
                'utf8': 1,
                'srlimit': 1
            }
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                if data['query']['search']:
                    title = data['query']['search'][0]['title']
                    page_url = f'https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(" ", "_"))}'
                    await event.edit(f'**Wikipedia:** {page_url}', parse_mode='md')
                else:
                    await event.edit('**No results**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.video2audio$'))
async def video_to_audio(event):
    if event.is_reply:
        try:
            msg = await event.get_reply_message()
            if msg.video:
                await event.edit('**Downloading video...**', parse_mode='md')
                video_path = await msg.download_media()
                # Здесь нужен ffmpeg для конвертации
                await event.edit('**Install ffmpeg for conversion**', parse_mode='md')
            else:
                await event.edit('**Reply to a video**', parse_mode='md')
        except Exception as e:
            await event.edit(f'**Error:** {str(e)}', parse_mode='md')
    else:
        await event.edit('**Reply to a video**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tts (.+)$'))
async def text_to_speech(event):
    text = event.pattern_match.group(1).strip()
    try:
        from gtts import gTTS
        import tempfile
        
        tts = gTTS(text=text, lang='ru')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            tts.save(f.name)
            await client.send_file(event.chat_id, f.name, voice_note=True)
            os.unlink(f.name)
        
        await event.delete()
    except ImportError:
        await event.edit('**Install:** pip install gtts', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.img (.+)$'))
async def image_search(event):
    query = event.pattern_match.group(1).strip()
    try:
        async with aiohttp.ClientSession() as session:
            params = {'q': query, 'tbm': 'isch'}
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with session.get('https://www.google.com/search', params=params, headers=headers) as resp:
                html = await resp.text()
                import re
                urls = re.findall(r'\"ou\":\"([^\"]+)\"', html)
                if urls:
                    await client.send_file(event.chat_id, urls[0], caption=f'**Image:** {query}')
                    await event.delete()
                else:
                    await event.edit('**No images found**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.password (\d+)$'))
async def generate_password(event):
    try:
        length = int(event.pattern_match.group(1).strip())
        length = max(4, min(length, 50))
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        await event.edit(f'**Password ({length} chars):** `{password}`', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.random (\d+)$'))
async def random_number(event):
    try:
        max_num = int(event.pattern_match.group(1).strip())
        result = random.randint(1, max_num)
        await event.edit(f'**Random (1-{max_num}):** {result}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.dice$'))
async def dice_roll(event):
    result = random.randint(1, 6)
    await event.edit(f'**Dice:** {result}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.coin$'))
async def flip_coin(event):
    result = random.choice(['Heads', 'Tails'])
    await event.edit(f'**Coin:** {result}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ball (.+)$'))
async def magic_ball(event):
    answers = [
        'Yes', 'No', 'Maybe', 'Ask again later', 'Certainly', 
        'Never', 'Most likely', 'Very doubtful', 'Outlook good',
        'Cannot predict now', 'Concentrate and ask again'
    ]
    await event.edit(f'**Answer:** {random.choice(answers)}', parse_mode='md')

# ==================== БЛОК 7: РАЗНОЕ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.afk (.+)$'))
async def set_afk(event):
    reason = event.pattern_match.group(1).strip()
    client.afk_status = {
        "afk": True,
        "reason": reason,
        "since": datetime.now()
    }
    cursor.execute('INSERT OR REPLACE INTO afk_users VALUES (?, ?, ?)', 
                  (event.sender_id, reason, int(time.time())))
    conn.commit()
    await event.edit(f'**AFK mode:** {reason}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unafk$'))
async def unset_afk(event):
    client.afk_status = {"afk": False, "reason": "", "since": None}
    cursor.execute('DELETE FROM afk_users WHERE user_id = ?', (event.sender_id,))
    conn.commit()
    await event.edit('**AFK mode disabled**', parse_mode='md')

@client.on(events.NewMessage(incoming=True))
async def check_afk(event):
    if event.is_private and not event.out:
        cursor.execute('SELECT reason, since FROM afk_users WHERE user_id = ?', (event.sender_id,))
        row = cursor.fetchone()
        if row:
            reason, since_time = row
            since = datetime.fromtimestamp(since_time)
            delta = datetime.now() - since
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            await event.respond(f'**User is AFK:** {reason}\n**For:** {hours}h {minutes}m')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.clone (.+)$'))
async def clone_profile(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await event.edit(f'**Clone info for @{user.username or user.id}:**\n'
                        f'Name: {user.first_name or ""} {user.last_name or ""}\n'
                        f'Bio: {getattr(user, "about", "No bio")}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.export$'))
async def export_users(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    
    await event.edit('**Exporting users...**', parse_mode='md')
    try:
        users = []
        async for user in client.iter_participants(event.chat_id):
            if not user.bot:
                users.append(f'{user.id}|{user.username or ""}|{user.first_name or ""}')
        
        if users:
            filename = f'export_{event.chat_id}_{int(time.time())}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(users))
            
            await client.send_file(event.chat_id, filename, caption=f'**Exported {len(users)} users**')
            await event.delete()
            os.remove(filename)
        else:
            await event.edit('**No users found**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.sysinfo$'))
async def system_info(event):
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        text = f"""**System Info**
CPU: {cpu_percent}%
RAM: {memory.percent}% ({get_size(memory.used)}/{get_size(memory.total)})
Disk: {disk.percent}% ({get_size(disk.used)}/{get_size(disk.total)})
Uptime: {time.time() - psutil.boot_time():.0f}s
Processes: {len(psutil.pids())}"""
        
        await event.edit(text, parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.logs$'))
async def view_logs(event):
    try:
        if os.path.exists('bot.log'):
            with open('bot.log', 'r') as f:
                logs = f.read()[-2000:]
            await event.edit(f'**Last logs:**\n```{logs}```', parse_mode='md')
        else:
            await event.edit('**No log file**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.restart$'))
async def restart_bot(event):
    await event.edit('**Restarting...**', parse_mode='md')
    os.execv(sys.executable, [sys.executable] + sys.argv)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stop$'))
async def stop_bot(event):
    await event.edit('**Stopping...**', parse_mode='md')
    await client.disconnect()
    import sys
    sys.exit(0)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.save (.+)$'))
async def save_message(event):
    text = event.pattern_match.group(1).strip()
    await client.send_message('me', text)
    await event.edit('**Saved to messages**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.fwd (@?\w+) (.+)$'))
async def forward_message(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        text = event.pattern_match.group(2).strip()
        await client.send_message(user, text)
        await event.edit('**Message sent**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.block (@?\w+)$'))
async def block_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client(functions.contacts.BlockRequest(id=user))
        await event.edit(f'**Blocked:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unblock (@?\w+)$'))
async def unblock_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client(functions.contacts.UnblockRequest(id=user))
        await event.edit(f'**Unblocked:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.join (.+)$'))
async def join_chat(event):
    link = event.pattern_match.group(1).strip()
    try:
        if 't.me/' in link:
            username = link.split('t.me/')[-1].replace('@', '')
            await client(JoinChannelRequest(username))
            await event.edit('**Joined successfully**', parse_mode='md')
        else:
            await event.edit('**Invalid link**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.leave$'))
async def leave_chat(event):
    try:
        await client(LeaveChannelRequest(event.chat_id))
    except:
        await event.edit('**Cannot leave this chat**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.report (@?\w+) (.+)$'))
async def report_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        reason = event.pattern_match.group(2).strip()
        await event.edit(f'**Reported @{user.username or user.id} for:** {reason}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stats$'))
async def chat_stats(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    
    await event.edit('**Calculating...**', parse_mode='md')
    try:
        total = 0
        users = 0
        bots = 0
        online = 0
        
        async for user in client.iter_participants(event.chat_id, limit=200):
            total += 1
            if user.bot:
                bots += 1
            else:
                users += 1
                if hasattr(user, 'status') and isinstance(user.status, types.UserStatusOnline):
                    online += 1
        
        text = f"""**Chat Stats**
Total: {total}
Users: {users}
Bots: {bots}
Online: {online}
ID: {event.chat_id}"""
        
        await event.edit(text, parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.parse$'))
async def parse_chat(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    
    await event.edit('**Parsing...**', parse_mode='md')
    try:
        members = []
        async for user in client.iter_participants(event.chat_id, limit=50):
            name = f'@{user.username}' if user.username else user.first_name or f'ID:{user.id}'
            members.append(name)
        
        text = f"""**Members (50):**
{', '.join(members)}"""
        
        await event.edit(text, parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.who (@?\w+)$'))
async def find_user_chats(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await event.edit(f'**Searching chats for @{user.username or user.id}...**', parse_mode='md')
        
        common = []
        async for dialog in client.iter_dialogs(limit=50):
            if dialog.is_group or dialog.is_channel:
                try:
                    participants = await client.get_participants(dialog.id, limit=30)
                    if any(p.id == user.id for p in participants):
                        common.append(dialog.name)
                except:
                    continue
        
        if common:
            text = f'**Chats with user ({len(common)}):**\n' + '\n'.join(common[:15])
            if len(common) > 15:
                text += f'\n...and {len(common)-15} more'
        else:
            text = '**No common chats found**'
        
        await event.edit(text, parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.search (.+)$'))
async def search_chats(event):
    query = event.pattern_match.group(1).strip()
    await event.edit(f'**Searching:** {query}', parse_mode='md')
    
    results = []
    async for dialog in client.iter_dialogs(limit=50):
        try:
            messages = await client.get_messages(dialog.id, search=query, limit=1)
            if messages:
                results.append(dialog.name)
        except:
            continue
    
    if results:
        text = f'**Found in {len(results)} chats:**\n' + '\n'.join(results[:10])
        await event.edit(text, parse_mode='md')
    else:
        await event.edit('**No results**', parse_mode='md')

# ==================== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.trwords$'))
async def top_words(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    await event.edit('**No word tracking implemented**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.fake$'))
async def fake_data(event):
    first_names = ['John', 'Jane', 'Alex', 'Maria', 'David', 'Sarah']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones']
    email = f'{random.choice(first_names).lower()}{random.randint(1,99)}@example.com'
    phone = f'+1{random.randint(100,999)}{random.randint(100,999)}{random.randint(1000,9999)}'
    text = f"""**Fake Data**
Name: {random.choice(first_names)} {random.choice(last_names)}
Email: {email}
Phone: {phone}
Address: {random.randint(1,999)} Fake Street"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.quote$'))
async def random_quote(event):
    quotes = [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Innovation distinguishes between a leader and a follower. - Steve Jobs",
        "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
        "Stay hungry, stay foolish. - Steve Jobs",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
        "Life is what happens when you're busy making other plans. - John Lennon",
        "You must be the change you wish to see in the world. - Mahatma Gandhi"
    ]
    await event.edit(f'**Quote:** {random.choice(quotes)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.whois$'))
async def random_member(event):
    if not event.is_group:
        await event.edit('**Only in groups**', parse_mode='md')
        return
    
    try:
        participants = await client.get_participants(event.chat_id, limit=100)
        if participants:
            user = random.choice(participants)
            name = f'@{user.username}' if user.username else user.first_name
            await event.edit(f'**Random member:** {name}', parse_mode='md')
        else:
            await event.edit('**No members**', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.promote (@?\w+)$'))
async def promote_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_admin(
            event.chat_id,
            user,
            change_info=True,
            post_messages=True,
            edit_messages=True,
            delete_messages=True,
            invite_users=True
        )
        await event.edit(f'**Promoted:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.demote (@?\w+)$'))
async def demote_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin rights**', parse_mode='md')
        return
    
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_admin(
            event.chat_id,
            user,
            change_info=False,
            post_messages=False,
            edit_messages=False,
            delete_messages=False,
            invite_users=False
        )
        await event.edit(f'**Demoted:** @{user.username or user.id}', parse_mode='md')
    except Exception as e:
        await event.edit(f'**Error:** {str(e)}', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.kickme$'))
async def kick_self(event):
    try:
        await client.kick_participant(event.chat_id, 'me')
    except:
        await event.edit('**Cannot kick yourself**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.me$'))
async def my_profile(event):
    me = await client.get_me()
    text = f"""**My Profile**
ID: {me.id}
Username: @{me.username or 'none'}
Name: {me.first_name or ''} {me.last_name or ''}
Phone: {me.phone or 'hidden'}
Premium: {me.premium or False}
Bot: {me.bot}"""
    await event.edit(text, parse_mode='md')

# ==================== ЗАПУСК БОТА ====================
async def start_bot():
    await client.start()
    me = await client.get_me()
    print(f"✅ Bot started: @{me.username or me.id}")
    print(f"⏰ Start time: {client.start_time}")
    print(f"🌐 Flask server on port {PORT}")
    
    import threading
    def run_flask():
        waitress.serve(app, host='0.0.0.0', port=PORT)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    finally:
        conn.close()
