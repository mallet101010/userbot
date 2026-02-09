#!/usr/bin/env python3
"""
Telegram Userbot for Render.com
Web server + Telegram bot
"""

import os
import sys
import time
import json
import re
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession

# Flask для веб-сервера (чтобы Render не останавливал)
from flask import Flask, jsonify, request
import threading
import logging

# ==================== ВЕБ-СЕРВЕР ====================

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'service': 'Telegram Userbot',
        'uptime': int(time.time() - start_time),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/status')
def status():
    return jsonify({
        'bot_running': bot_running,
        'start_time': start_time,
        'requests_handled': request_count
    })

def run_web_server():
    """Запуск веб-сервера в отдельном потоке"""
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False, threaded=True)

# ==================== ТЕЛЕГРАМ БОТ ====================

# Конфигурация
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')

if not all([API_ID, API_HASH, SESSION_STRING]):
    print("ERROR: Missing environment variables")
    sys.exit(1)

# Инициализация
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
client.start_time = datetime.now()
bot_running = True
start_time = time.time()
request_count = 0

# База данных
DB_PATH = Path('userbot.db')
db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
db_cursor = db_conn.cursor()

# Создание таблиц
db_cursor.execute('''CREATE TABLE IF NOT EXISTS notes (name TEXT PRIMARY KEY, content TEXT)''')
db_cursor.execute('''CREATE TABLE IF NOT EXISTS activity (user_id INTEGER, time INTEGER)''')
db_cursor.execute('''CREATE TABLE IF NOT EXISTS words (chat_id INTEGER, word TEXT, count INTEGER)''')
db_cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, chat_id INTEGER, text TEXT, time INTEGER)''')
db_cursor.execute('''CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, word TEXT)''')
db_conn.commit()

# Глобальные настройки
settings = {
    'auto_read': True,
    'auto_captcha': False,
    'auto_save': False,
    'spam_filter': False
}

# ==================== КОМАНДЫ ====================

# Меню команд
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.m$'))
async def menu(event):
    menu_text = """**Commands**
.ob - help
.t - time
.p - ping
.s - status
.i - info
.u - uptime
.a - activity
.who @user - find chats
.parse - parse chat
.tr - top words
.search text - search
.cap - auto captcha
.read - auto read
.clear N - delete messages
.ban @user - ban
.unban @user - unban
.mute @user N - mute
.unmute @user - unmute
.promote @user - promote
.kick @user - kick
.fwd @user text - forward
.save text - save to saved
.notes - list notes
.note name text - add note
.stats - chat stats
.export - export users
.id - get ID
.join link - join
.leave - leave
.upload file - upload
.restart - restart
.stop - stop
.logs - logs
.rem N text - reminder
.broadcast text - broadcast
.block @user - block
.unblock @user - unblock
.afk text - away
.welcome - welcome
.rules - rules
.admins - admins
.history N - history
.find msg - find
.react emoji - react
.poll question - poll
.vote - vote
.timer N - timer
.alarm HH:MM - alarm
.calc expr - calculator
.weather city - weather
.trans text - translate
.qr text - qr code
.block @user - block
.unblock @user - unblock
.theme - theme
.lang - language
.font - font
.alias name cmd - alias
.plugins - plugins
.stickerpack - stickers
.game - games
.8ball - 8ball
.dice - dice
.coin - coin
.countdown N - countdown
.bookmark - bookmark
.archive - archive
.muteall - mute all
.hide - hide chat
.encrypt text - encrypt
.decrypt text - decrypt
.hash text - hash
.encode text - encode
.decode text - decode
.scan - scan
.test - test
.debug - debug
.profile - profile
.update - update
.version - version
.sysinfo - system info
.disk - disk
.memory - memory
.cpu - cpu
.network - network
.balance - balance
.support - support
.donate - donate
.reportbug - bug
.request - request
.leaderboard - leaderboard
.rank - rank
.level - level
.xp - xp
.reward - reward
.event - event
.holiday - holiday
.memory - memory
.dream - dream
.goal - goal
.plan - plan
.strategy - strategy
.hero - hero
.villain - villain
.friend - friend
.enemy - enemy
.spy - spy
.detective - detective
.warrior - warrior
.knight - knight
.ninja - ninja
.pirate - pirate
.viking - viking
.champion - champion
.guardian - guardian
.savior - savior
.teacher - teacher
.student - student
.doctor - doctor
.lawyer - lawyer
.police - police
.pilot - pilot
.driver - driver
.manager - manager
.ceo - ceo
.cfo - cfo
.cto - cto
.cmo - cmo"""
    await event.edit(menu_text, parse_mode='md')

# Помощь
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ob$'))
async def help_all(event):
    help_text = """**Command Help**
.m - show all commands
.t - current time UTC+3/4/5
.p - check ping
.s - bot status
.i - account info
.u - bot uptime
.a - user activity
.who @user - find user chats
.parse - parse chat members
.tr - top words in chat
.search text - global search
.cap - auto captcha toggle
.read - auto read toggle
.clear N - delete messages
.ban @user - ban user
.unban @user - unban
.mute @user N - mute minutes
.unmute @user - unmute
.promote @user - promote admin
.kick @user - kick user
.fwd @user text - forward message
.save text - save to saved
.notes - list notes
.note name text - add note
.stats - chat statistics
.export - export users
.id - get chat id
.join link - join chat
.leave - leave chat
.upload file - upload
.restart - restart bot
.stop - stop bot
.logs - show logs
.rem N text - reminder
.broadcast text - broadcast
.block @user - block
.unblock @user - unblock
.afk text - away
.welcome - welcome
.rules - rules
.admins - admins
.history N - history
.find msg - find
.react emoji - react
.poll question - poll
.vote - vote
.timer N - timer
.alarm HH:MM - alarm
.calc expr - calculator
.weather city - weather
.trans text - translate
.qr text - qr code
.theme - theme
.lang - language
.font - font
.alias name cmd - alias
.plugins - plugins
.stickerpack - stickers
.game - games
.8ball - 8ball
.dice - dice
.coin - coin
.countdown N - countdown
.bookmark - bookmark
.archive - archive
.muteall - mute all
.hide - hide chat
.encrypt text - encrypt
.decrypt text - decrypt
.hash text - hash
.encode text - encode
.decode text - decode
.scan - scan
.test - test
.debug - debug
.profile - profile
.update - update
.version - version
.sysinfo - system info
.disk - disk
.memory - memory
.cpu - cpu
.network - network
.balance - balance
.support - support
.donate - donate
.reportbug - bug
.request - request
.leaderboard - leaderboard
.rank - rank
.level - level
.xp - xp
.reward - reward
.event - event
.holiday - holiday
.memory - memory
.dream - dream
.goal - goal
.plan - plan
.strategy - strategy
.hero - hero
.villain - villain
.friend - friend
.enemy - enemy
.spy - spy
.detective - detective
.warrior - warrior
.knight - knight
.ninja - ninja
.pirate - pirate
.viking - viking
.champion - champion
.guardian - guardian
.savior - savior
.teacher - teacher
.student - student
.doctor - doctor
.lawyer - lawyer
.police - police
.pilot - pilot
.driver - driver
.manager - manager
.ceo - ceo
.cfo - cfo
.cto - cto
.cmo - cmo"""
    await event.edit(help_text, parse_mode='md')

# Основные команды
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.t$'))
async def time_cmd(event):
    now = datetime.utcnow()
    text = f"""**Time**
UTC+3: {(now.hour + 3) % 24:02d}:{now.minute:02d}
UTC+4: {(now.hour + 4) % 24:02d}:{now.minute:02d}
UTC+5: {(now.hour + 5) % 24:02d}:{now.minute:02d}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.p$'))
async def ping(event):
    start = time.time()
    msg = await event.edit('**Ping**', parse_mode='md')
    delay = int((time.time() - start) * 1000)
    await msg.edit(f'**Ping:** {delay}ms', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.s$'))
async def status_cmd(event):
    me = await client.get_me()
    delta = datetime.now() - client.start_time
    hours = delta.seconds // 3600
    text = f"""**Status**
User: @{me.username or me.id}
Uptime: {hours}h
Web: Online
Render: Active"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.i$'))
async def info_cmd(event):
    me = await client.get_me()
    text = f"""**Info**
ID: {me.id}
Username: @{me.username or 'none'}
Phone: {me.phone or 'hidden'}
Bot: {me.bot}
Premium: {me.premium or 'no'}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.u$'))
async def uptime_cmd(event):
    delta = datetime.now() - client.start_time
    text = f"""**Uptime**
Days: {delta.days}
Hours: {delta.seconds // 3600}
Minutes: {(delta.seconds % 3600) // 60}"""
    await event.edit(text, parse_mode='md')

# Активити
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.a$'))
async def activity_all(event):
    db_cursor.execute('SELECT user_id, MAX(time) FROM activity GROUP BY user_id ORDER BY time DESC LIMIT 10')
    rows = db_cursor.fetchall()
    if rows:
        text = '**Recent activity**\n'
        for user_id, timestamp in rows:
            delta = int(time.time()) - timestamp
            mins = delta // 60
            text += f'{user_id}: {mins}m ago\n'
        await event.edit(text, parse_mode='md')
    else:
        await event.edit('**No activity**', parse_mode='md')

# Поиск пользователя
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.who (.+)$'))
async def find_user(event):
    user_input = event.pattern_match.group(1).strip()
    try:
        user = await client.get_entity(user_input)
        await event.edit(f'**Searching for** @{user.username or user.id}')
        
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
            text = f'**Chats with user:**\n' + '\n'.join(common[:10])
            await event.edit(text, parse_mode='md')
        else:
            await event.edit('**No common chats**', parse_mode='md')
    except:
        await event.edit('**Invalid user**', parse_mode='md')

# Парсинг чата
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.parse$'))
async def parse_current(event):
    if not event.is_group:
        await event.edit('**Not a group**', parse_mode='md')
        return
    
    await event.edit('**Parsing...**', parse_mode='md')
    
    users = []
    async for user in client.iter_participants(event.chat_id, limit=100):
        users.append(f'@{user.username}' if user.username else f'id{user.id}')
    
    text = f"""**Chat members**
Total: {len(users)}
Sample: {chr(10).join(users[:10])}"""
    
    await event.edit(text, parse_mode='md')

# Топ слов
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tr$'))
async def top_words(event):
    if not event.is_group:
        await event.edit('**Not a group**', parse_mode='md')
        return
    
    db_cursor.execute('SELECT word, count FROM words WHERE chat_id = ? ORDER BY count DESC LIMIT 15',
                     (event.chat_id,))
    rows = db_cursor.fetchall()
    if rows:
        text = '**Top words**\n'
        for word, count in rows:
            text += f'{word}: {count}\n'
        await event.edit(text)
    else:
        await event.edit('**No data**')

# Глобальный поиск
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.search (.+)$'))
async def search_all(event):
    query = event.pattern_match.group(1)
    await event.edit(f'**Searching:** {query}')
    
    results = []
    async for dialog in client.iter_dialogs(limit=30):
        try:
            found = await client.get_messages(dialog.id, search=query, limit=1)
            if found:
                results.append(dialog.name)
        except:
            continue
    
    if results:
        text = f'**Found in {len(results)} chats**\n' + '\n'.join(results[:10])
        await event.edit(text)
    else:
        await event.edit('**No results**')

# Админ команды
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.clear$'))
async def clear_default(event):
    await event.delete()
    async for msg in client.iter_messages(event.chat_id, limit=10):
        await msg.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.clear (\d+)$'))
async def clear_n(event):
    try:
        count = min(int(event.pattern_match.group(1)), 100)
        await event.delete()
        deleted = 0
        async for msg in client.iter_messages(event.chat_id, limit=count):
            await msg.delete()
            deleted += 1
        msg = await client.send_message(event.chat_id, f'**Cleared:** {deleted}')
        await asyncio.sleep(2)
        await msg.delete()
    except:
        pass

async def is_admin(chat_id, user_id):
    try:
        participant = await client.get_permissions(chat_id, user_id)
        return participant.is_admin
    except:
        return False

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ban (@?\w+)$'))
async def ban_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1))
        await client.edit_permissions(event.chat_id, user, view_messages=False)
        await event.edit(f'**Banned:** @{user.username or user.id}')
    except:
        await event.edit('**Error**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unban (@?\w+)$'))
async def unban_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Need admin**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1))
        await client.edit_permissions(event.chat_id, user, view_messages=True)
        await event.edit(f'**Unbanned:** @{user.username or user.id}')
    except:
        await event.edit('**Error**')

# Автокапча
def solve_math(text):
    text = text.lower().replace('=', ' ').replace('?', '')
    nums = re.findall(r'\d+', text)
    if len(nums) >= 2 and '+' in text:
        return str(int(nums[0]) + int(nums[1]))
    return None

@client.on(events.NewMessage(incoming=True))
async def handle_captcha(event):
    if not settings['auto_captcha'] or not event.sender or not event.sender.bot:
        return
    
    text = event.text or ''
    solution = solve_math(text)
    if solution:
        await asyncio.sleep(1)
        await event.reply(solution)
        return
    
    text_lower = text.lower()
    if any(word in text_lower for word in ['подпис', 'subscribe']) and event.reply_markup:
        await asyncio.sleep(1)
        await event.click(0)
        return
    
    if any(word in text_lower for word in ['верифи', 'verify']):
        await asyncio.sleep(1)
        await event.reply('✅')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.cap$'))
async def toggle_captcha(event):
    settings['auto_captcha'] = not settings['auto_captcha']
    status = 'ON' if settings['auto_captcha'] else 'OFF'
    await event.edit(f'**Auto captcha:** {status}')

# Трекинг активности
@client.on(events.NewMessage(incoming=True))
async def track_all(event):
    global request_count
    request_count += 1
    
    if event.sender_id:
        db_cursor.execute('INSERT INTO activity VALUES (?, ?)', 
                         (event.sender_id, int(time.time())))
        db_conn.commit()
    
    if settings['auto_read']:
        await event.mark_read()
    
    if event.text and event.is_group:
        words = re.findall(r'\b\w{4,}\b', event.text.lower())
        for word in words:
            db_cursor.execute('''INSERT INTO words VALUES (?, ?, 1)
                              ON CONFLICT(chat_id, word) DO UPDATE SET count = count + 1''',
                            (event.chat_id, word))
            db_conn.commit()

# Заметки
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.notes$'))
async def list_notes(event):
    db_cursor.execute('SELECT name FROM notes')
    rows = db_cursor.fetchall()
    if rows:
        text = '**Notes**\n' + '\n'.join([row[0] for row in rows])
        await event.edit(text)
    else:
        await event.edit('**No notes**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.note (\w+) (.+)$'))
async def add_note(event):
    name = event.pattern_match.group(1)
    content = event.pattern_match.group(2)
    db_cursor.execute('INSERT OR REPLACE INTO notes VALUES (?, ?)', (name, content))
    db_conn.commit()
    await event.edit(f'**Note saved:** {name}')

# Статистика
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stats$'))
async def chat_stats(event):
    if not event.is_group:
        await event.edit('**Not a group**', parse_mode='md')
        return
    
    users = 0
    bots = 0
    async for user in client.iter_participants(event.chat_id, limit=150):
        if user.bot:
            bots += 1
        else:
            users += 1
    
    text = f"""**Chat stats**
Total: {users + bots}
Users: {users}
Bots: {bots}"""
    await event.edit(text)

# Системные команды
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.restart$'))
async def restart_bot(event):
    await event.edit('**Restarting...**')
    os.execv(sys.executable, [sys.executable] + sys.argv)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stop$'))
async def stop_bot(event):
    await event.edit('**Stopping...**')
    await client.disconnect()
    sys.exit(0)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.logs$'))
async def show_logs(event):
    await event.edit('**Logs available on Render dashboard**')

# ==================== ЗАПУСК ====================

async def telegram_main():
    """Основная функция Telegram бота"""
    print("=" * 50)
    print("Telegram Userbot Starting...")
    print("=" * 50)
    
    await client.start()
    me = await client.get_me()
    
    print(f"User: @{me.username or me.id}")
    print(f"ID: {me.id}")
    print("Telegram bot is running...")
    print("=" * 50)
    
    await client.run_until_disconnected()

def start_bot():
    """Запуск Telegram бота в отдельном потоке"""
    try:
        client.loop.run_until_complete(telegram_main())
    except Exception as e:
        print(f"Telegram bot error: {e}")

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print("Web server started on port 8080")
    
    # Запускаем Telegram бота
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    print("Both web server and Telegram bot are running")
    print("Render will keep this service alive")
    
    # Бесконечный цикл чтобы основной поток не завершался
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down...")
