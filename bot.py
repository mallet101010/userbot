import sys
import types
import asyncio
import sqlite3
import urllib.request
import urllib.parse
import json
import random
import time
import re
import string
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from threading import Thread
from flask import Flask
import waitress

# Fix for Python 3.13
imghdr_module = types.ModuleType("imghdr")
imghdr_module.what = lambda f, h=None: None
sys.modules["imghdr"] = imghdr_module

cgi_module = types.ModuleType("cgi")
cgi_module.escape = lambda s: s
sys.modules["cgi"] = cgi_module

# Flask app for keep-alive
app = Flask(__name__)
@app.route('/')
def index():
    return "Userbot running"
@app.route('/ping')
def ping():
    return "pong"

# Configuration
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')
PORT = int(os.getenv('PORT', 8080))

if not all([API_ID, API_HASH, SESSION_STRING]):
    raise SystemExit("Set API_ID, API_HASH, SESSION_STRING")

from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
client.start_time = datetime.now()

# Database
db = sqlite3.connect('userbot.db', check_same_thread=False)
cursor = db.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS notes (name TEXT PRIMARY KEY, content TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, chat_id INTEGER, count INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, time INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, trigger TEXT, response TEXT)''')
db.commit()

# Helper functions
async def is_admin(chat_id, user_id):
    try:
        participant = await client.get_permissions(chat_id, user_id)
        return participant.is_admin
    except:
        return False

async def http_get(url):
    def sync_get():
        req = urllib.request.Request(url, headers={'User-Agent': 'Userbot'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    return await asyncio.to_thread(sync_get)

# ==================== MENU ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.m$'))
async def menu(event):
    text = """**Commands**
.ob - all commands
.p - ping
.t - time
.s - status
.i - info
.u - uptime
.id - get id
.info @user - user info
.notes - list notes
.note name text - save note
.getnote name - get note
.delnote name - delete note
.ban @user - ban
.unban @user - unban
.kick @user - kick
.mute @user N - mute N min
.unmute @user - unmute
.pin - pin message
.purge N - purge messages
.warn @user - warn
.warns @user - check warns
.clearwarns @user - clear warns
.weather city - weather
.calc expr - calculator
.qr text - qr code
.sh url - shorten
.long url - unshorten
.reverse text - reverse
.translit text - translit
.upper text - uppercase
.lower text - lowercase
.bold text - bold
.mono text - monospace
.afk reason - afk mode
.unafk - disable afk
.promote @user - promote
.demote @user - demote
.admins - list admins
.tagall - tag all
.invite N - create invite
.btc - bitcoin price
.eth - ethereum price
.ton - toncoin price
.doge - dogecoin price
.currency from to amount - convert
.google query - search
.wiki query - wikipedia
.tts text - text to speech
.img query - image search
.password N - gen password
.random N - random 1-N
.dice - dice
.coin - coin
.ball question - 8 ball
.clone @user - clone info
.export - export users
.sysinfo - system info
.logs - view logs
.restart - restart
.stop - stop
.save text - save to saved
.fwd @user text - forward
.block @user - block
.unblock @user - unblock
.join link - join
.leave - leave
.report @user - report
.stats - chat stats
.parse - parse members
.who @user - find chats
.search text - search
.fake - fake data
.quote - quote
.whois - random member"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ob$'))
async def help_all(event):
    text = """**All Commands**
.m .ob .p .t .s .i .u .id .info .notes .note .getnote .delnote .ban .unban .kick .mute .unmute .pin .purge .warn .warns .clearwarns .weather .calc .qr .sh .long .reverse .translit .upper .lower .bold .mono .afk .unafk .promote .demote .admins .tagall .invite .btc .eth .ton .doge .currency .google .wiki .tts .img .password .random .dice .coin .ball .clone .export .sysinfo .logs .restart .stop .save .fwd .block .unblock .join .leave .report .stats .parse .who .search .fake .quote .whois"""
    await event.edit(text, parse_mode='md')

# ==================== BASIC ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.p$'))
async def ping_cmd(event):
    start = time.time()
    msg = await event.edit('Ping')
    delay = int((time.time() - start) * 1000)
    await msg.edit(f'Pong: {delay}ms')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.t$'))
async def time_cmd(event):
    now = datetime.utcnow()
    text = f"""Time
UTC+3: {(now.hour + 3) % 24:02d}:{now.minute:02d}
UTC+4: {(now.hour + 4) % 24:02d}:{now.minute:02d}
UTC+5: {(now.hour + 5) % 24:02d}:{now.minute:02d}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.s$'))
async def status_cmd(event):
    me = await client.get_me()
    delta = datetime.now() - client.start_time
    text = f"""Status
User: @{me.username or me.id}
Uptime: {delta.days}d {delta.seconds // 3600}h
Platform: Render"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.i$'))
async def info_cmd(event):
    me = await client.get_me()
    text = f"""Info
ID: {me.id}
Username: @{me.username or 'none'}
Name: {me.first_name or ''} {me.last_name or ''}
Bot: {me.bot}
Premium: {me.premium or False}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.u$'))
async def uptime_cmd(event):
    delta = datetime.now() - client.start_time
    text = f"""Uptime
Days: {delta.days}
Hours: {delta.seconds // 3600}
Minutes: {(delta.seconds % 3600) // 60}"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.id$'))
async def get_id_cmd(event):
    chat = await event.get_chat()
    await event.edit(f'Chat ID: `{chat.id}`', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.info (.+)$'))
async def user_info_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        text = f"""User Info
ID: {user.id}
Name: {user.first_name or ''} {user.last_name or ''}
Username: @{user.username or 'none'}
Bot: {user.bot}
Premium: {user.premium or False}"""
        await event.edit(text, parse_mode='md')
    except:
        await event.edit('User not found')

# ==================== NOTES ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.notes$'))
async def notes_list(event):
    cursor.execute('SELECT name FROM notes')
    rows = cursor.fetchall()
    if rows:
        text = 'Notes: ' + ', '.join([row[0] for row in rows])
    else:
        text = 'No notes'
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.note (\w+) (.+)$'))
async def note_add(event):
    name = event.pattern_match.group(1)
    content = event.pattern_match.group(2)
    cursor.execute('INSERT OR REPLACE INTO notes VALUES (?, ?)', (name, content))
    db.commit()
    await event.edit(f'Note saved: {name}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.getnote (\w+)$'))
async def note_get(event):
    name = event.pattern_match.group(1)
    cursor.execute('SELECT content FROM notes WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        await event.edit(f'{name}: {row[0]}')
    else:
        await event.edit('Note not found')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.delnote (\w+)$'))
async def note_del(event):
    name = event.pattern_match.group(1)
    cursor.execute('DELETE FROM notes WHERE name = ?', (name,))
    db.commit()
    if cursor.rowcount > 0:
        await event.edit(f'Note deleted: {name}')
    else:
        await event.edit('Note not found')

# ==================== ADMIN ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ban (@?\w+)$'))
async def ban_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, view_messages=False)
        await event.edit(f'Banned: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unban (@?\w+)$'))
async def unban_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, view_messages=True)
        await event.edit(f'Unbanned: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.kick (@?\w+)$'))
async def kick_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.kick_participant(event.chat_id, user)
        await event.edit(f'Kicked: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.mute (@?\w+) (\d+)$'))
async def mute_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        minutes = int(event.pattern_match.group(2))
        until = datetime.now() + timedelta(minutes=minutes)
        await client.edit_permissions(event.chat_id, user, until_date=until, send_messages=False)
        await event.edit(f'Muted {minutes}m: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unmute (@?\w+)$'))
async def unmute_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, send_messages=True)
        await event.edit(f'Unmuted: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.pin$'))
async def pin_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        await event.message.pin()
        await event.edit('Pinned')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.purge (\d+)$'))
async def purge_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        count = min(int(event.pattern_match.group(1)), 100)
        await event.delete()
        deleted = 0
        async for msg in client.iter_messages(event.chat_id, limit=count):
            await msg.delete()
            deleted += 1
            await asyncio.sleep(0.1)
        msg = await client.send_message(event.chat_id, f'Purged: {deleted}')
        await asyncio.sleep(2)
        await msg.delete()
    except:
        pass

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.warn (@?\w+)$'))
async def warn_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
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
        db.commit()
        
        await event.edit(f'Warning: @{user.username or user.id} ({new_count}/3)')
        
        if new_count >= 3:
            await client.kick_participant(event.chat_id, user)
            cursor.execute('DELETE FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
            db.commit()
            await event.edit(f'Banned 3 warns: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.warns (@?\w+)$'))
async def warns_check(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('SELECT count FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        row = cursor.fetchone()
        count = row[0] if row else 0
        await event.edit(f'Warnings: @{user.username or user.id} - {count}/3')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.clearwarns (@?\w+)$'))
async def warns_clear(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('DELETE FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        db.commit()
        await event.edit(f'Cleared: @{user.username or user.id}')
    except:
        await event.edit('Error')

# ==================== UTILS ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.weather (.+)$'))
async def weather_cmd(event):
    city = event.pattern_match.group(1).strip()
    try:
        text = await http_get(f'https://wttr.in/{urllib.parse.quote(city)}?format=3')
        await event.edit(f'Weather: {text}')
    except:
        await event.edit('Weather error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.calc (.+)$'))
async def calc_cmd(event):
    try:
        expr = event.pattern_match.group(1).strip()
        allowed = {'abs': abs, 'max': max, 'min': min, 'pow': pow, 'round': round}
        result = eval(expr, {"__builtins__": {}}, allowed)
        await event.edit(f'Result: {result}')
    except:
        await event.edit('Calc error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.qr (.+)$'))
async def qr_cmd(event):
    text = event.pattern_match.group(1).strip()
    try:
        import qrcode
        qr = qrcode.make(text)
        bio = BytesIO()
        qr.save(bio, 'PNG')
        bio.seek(0)
        await client.send_file(event.chat_id, bio, caption=f'QR: {text[:30]}')
        await event.delete()
    except ImportError:
        await event.edit('Install qrcode[pil]')
    except:
        await event.edit('QR error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.sh (.+)$'))
async def shorten_cmd(event):
    url = event.pattern_match.group(1).strip()
    try:
        text = await http_get(f'https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}')
        await event.edit(f'Short: {text}')
    except:
        await event.edit('Shorten error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.long (.+)$'))
async def unshorten_cmd(event):
    url = event.pattern_match.group(1).strip()
    try:
        def sync_get():
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.geturl()
        result = await asyncio.to_thread(sync_get)
        await event.edit(f'Original: {result}')
    except:
        await event.edit('Unshorten error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.reverse (.+)$'))
async def reverse_cmd(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'Reverse: {text[::-1]}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.translit (.+)$'))
async def translit_cmd(event):
    text = event.pattern_match.group(1).strip().lower()
    table = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
             'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
             'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
             'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu',
             'я':'ya'}
    result = ''.join(table.get(c, c) for c in text)
    await event.edit(f'Translit: {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.upper (.+)$'))
async def upper_cmd(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'Upper: {text.upper()}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.lower (.+)$'))
async def lower_cmd(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'Lower: {text.lower()}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.bold (.+)$'))
async def bold_cmd(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'Bold: **{text}**', parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.mono (.+)$'))
async def mono_cmd(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'Mono: `{text}`', parse_mode='md')

# ==================== AFK ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.afk (.+)$'))
async def afk_set(event):
    reason = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR REPLACE INTO afk VALUES (?, ?, ?)', 
                  (event.sender_id, reason, int(time.time())))
    db.commit()
    await event.edit(f'AFK: {reason}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unafk$'))
async def afk_unset(event):
    cursor.execute('DELETE FROM afk WHERE user_id = ?', (event.sender_id,))
    db.commit()
    await event.edit('AFK off')

@client.on(events.NewMessage(incoming=True))
async def afk_check(event):
    if event.is_private and not event.out:
        cursor.execute('SELECT reason, time FROM afk WHERE user_id = ?', (event.sender_id,))
        row = cursor.fetchone()
        if row:
            reason, afk_time = row
            delta = int(time.time()) - afk_time
            mins = delta // 60
            await event.respond(f'AFK: {reason} ({mins}m)')

# ==================== GROUP ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.promote (@?\w+)$'))
async def promote_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_admin(event.chat_id, user, 
                               change_info=True, post_messages=True,
                               edit_messages=True, delete_messages=True)
        await event.edit(f'Promoted: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.demote (@?\w+)$'))
async def demote_cmd(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_admin(event.chat_id, user,
                               change_info=False, post_messages=False,
                               edit_messages=False, delete_messages=False)
        await event.edit(f'Demoted: @{user.username or user.id}')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.admins$'))
async def admins_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    try:
        participants = await client.get_participants(event.chat_id, limit=50)
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
            await event.edit('Admins:\n' + '\n'.join(admins[:15]))
        else:
            await event.edit('No admins')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tagall$'))
async def tagall_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        participants = await client.get_participants(event.chat_id, limit=30)
        mentions = []
        for user in participants:
            if not user.bot:
                mention = f'@{user.username}' if user.username else f'[{user.first_name}](tg://user?id={user.id})'
                mentions.append(mention)
        if mentions:
            await event.edit(' '.join(mentions), parse_mode='md')
        else:
            await event.edit('No users')
    except:
        await event.edit('Error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.invite (\d+)$'))
async def invite_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('Need admin')
        return
    try:
        limit = int(event.pattern_match.group(1))
        result = await client(functions.messages.ExportChatInviteRequest(
            peer=event.chat_id,
            expire_date=None,
            usage_limit=limit if limit > 0 else None
        ))
        await event.edit(f'Invite: {result.link}')
    except:
        await event.edit('Error')

# ==================== CRYPTO ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.btc$'))
async def btc_cmd(event):
    try:
        text = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
        data = json.loads(text)
        price = data['bitcoin']['usd']
        await event.edit(f'BTC: ${price:,.2f}')
    except:
        await event.edit('Price error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.eth$'))
async def eth_cmd(event):
    try:
        text = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')
        data = json.loads(text)
        price = data['ethereum']['usd']
        await event.edit(f'ETH: ${price:,.2f}')
    except:
        await event.edit('Price error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ton$'))
async def ton_cmd(event):
    try:
        text = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd')
        data = json.loads(text)
        price = data['the-open-network']['usd']
        await event.edit(f'TON: ${price:,.2f}')
    except:
        await event.edit('Price error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.doge$'))
async def doge_cmd(event):
    try:
        text = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd')
        data = json.loads(text)
        price = data['dogecoin']['usd']
        await event.edit(f'DOGE: ${price:,.4f}')
    except:
        await event.edit('Price error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.currency (\w+) (\w+) ([\d\.]+)$'))
async def currency_cmd(event):
    try:
        from_curr = event.pattern_match.group(1).upper()
        to_curr = event.pattern_match.group(2).upper()
        amount = float(event.pattern_match.group(3))
        
        text = await http_get(f'https://api.exchangerate-api.com/v4/latest/{from_curr}')
        data = json.loads(text)
        rate = data['rates'].get(to_curr)
        if rate:
            converted = amount * rate
            await event.edit(f'{amount} {from_curr} = {converted:.2f} {to_curr}')
        else:
            await event.edit('Currency error')
    except:
        await event.edit('Convert error')

# ==================== SEARCH ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.google (.+)$'))
async def google_cmd(event):
    query = event.pattern_match.group(1).strip()
    url = f'https://www.google.com/search?q={urllib.parse.quote(query)}'
    await event.edit(f'Google: {url}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.wiki (.+)$'))
async def wiki_cmd(event):
    query = event.pattern_match.group(1).strip()
    try:
        text = await http_get(f'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8=1&srlimit=1')
        data = json.loads(text)
        if data['query']['search']:
            title = data['query']['search'][0]['title']
            url = f'https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(" ", "_"))}'
            await event.edit(f'Wiki: {url}')
        else:
            await event.edit('No results')
    except:
        await event.edit('Wiki error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tts (.+)$'))
async def tts_cmd(event):
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
        await event.edit('Install gtts')
    except:
        await event.edit('TTS error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.img (.+)$'))
async def img_cmd(event):
    query = event.pattern_match.group(1).strip()
    try:
        def sync_img():
            req = urllib.request.Request(
                f'https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8')
                import re
                urls = re.findall(r'\"ou\":\"([^\"]+)\"', html)
                return urls[0] if urls else None
        url = await asyncio.to_thread(sync_img)
        if url:
            await client.send_file(event.chat_id, url, caption=f'Image: {query[:30]}')
            await event.delete()
        else:
            await event.edit('No images')
    except:
        await event.edit('Image error')

# ==================== FUN ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.password (\d+)$'))
async def password_cmd(event):
    try:
        length = int(event.pattern_match.group(1).strip())
        length = max(4, min(length, 50))
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        await event.edit(f'Password: `{password}`', parse_mode='md')
    except:
        await event.edit('Password error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.random (\d+)$'))
async def random_cmd(event):
    try:
        max_num = int(event.pattern_match.group(1).strip())
        result = random.randint(1, max_num)
        await event.edit(f'Random 1-{max_num}: {result}')
    except:
        await event.edit('Random error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.dice$'))
async def dice_cmd(event):
    result = random.randint(1, 6)
    await event.edit(f'Dice: {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.coin$'))
async def coin_cmd(event):
    result = random.choice(['Heads', 'Tails'])
    await event.edit(f'Coin: {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ball (.+)$'))
async def ball_cmd(event):
    answers = ['Yes', 'No', 'Maybe', 'Ask later', 'Certainly', 'Never', 'Probably', 'Unlikely']
    await event.edit(f'8ball: {random.choice(answers)}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.clone (.+)$'))
async def clone_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await event.edit(f'Clone @{user.username or user.id}:\nName: {user.first_name or ""} {user.last_name or ""}\nBio: {getattr(user, "about", "No bio")}')
    except:
        await event.edit('Clone error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.export$'))
async def export_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    try:
        users = []
        async for user in client.iter_participants(event.chat_id, limit=100):
            if not user.bot:
                users.append(f'{user.id}|{user.username or ""}|{user.first_name or ""}')
        if users:
            filename = f'export_{event.chat_id}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(users))
            await client.send_file(event.chat_id, filename, caption=f'Exported {len(users)} users')
            await event.delete()
            os.remove(filename)
        else:
            await event.edit('No users')
    except:
        await event.edit('Export error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.sysinfo$'))
async def sysinfo_cmd(event):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        text = f"""System
CPU: {cpu}%
RAM: {mem.percent}%
Disk: {disk.percent}%
Uptime: {time.time() - psutil.boot_time():.0f}s"""
        await event.edit(text)
    except ImportError:
        await event.edit('Install psutil')
    except:
        await event.edit('Sysinfo error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.logs$'))
async def logs_cmd(event):
    try:
        if os.path.exists('bot.log'):
            with open('bot.log', 'r') as f:
                logs = f.read()[-1500:]
            await event.edit(f'Logs:\n```{logs}```', parse_mode='md')
        else:
            await event.edit('No logs')
    except:
        await event.edit('Logs error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.restart$'))
async def restart_cmd(event):
    await event.edit('Restarting')
    os.execv(sys.executable, [sys.executable] + sys.argv)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stop$'))
async def stop_cmd(event):
    await event.edit('Stopping')
    await client.disconnect()
    import sys
    sys.exit(0)

# ==================== MESSAGING ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.save (.+)$'))
async def save_cmd(event):
    text = event.pattern_match.group(1).strip()
    await client.send_message('me', text)
    await event.edit('Saved')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.fwd (@?\w+) (.+)$'))
async def fwd_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        text = event.pattern_match.group(2).strip()
        await client.send_message(user, text)
        await event.edit('Forwarded')
    except:
        await event.edit('Forward error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.block (@?\w+)$'))
async def block_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client(functions.contacts.BlockRequest(id=user))
        await event.edit(f'Blocked: @{user.username or user.id}')
    except:
        await event.edit('Block error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.unblock (@?\w+)$'))
async def unblock_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client(functions.contacts.UnblockRequest(id=user))
        await event.edit(f'Unblocked: @{user.username or user.id}')
    except:
        await event.edit('Unblock error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.join (.+)$'))
async def join_cmd(event):
    link = event.pattern_match.group(1).strip()
    try:
        if 't.me/' in link:
            username = link.split('t.me/')[-1].replace('@', '')
            await client(functions.channels.JoinChannelRequest(username))
            await event.edit('Joined')
        else:
            await event.edit('Invalid link')
    except:
        await event.edit('Join error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.leave$'))
async def leave_cmd(event):
    try:
        await client(functions.channels.LeaveChannelRequest(event.chat_id))
    except:
        await event.edit('Leave error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.report (@?\w+) (.+)$'))
async def report_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        reason = event.pattern_match.group(2).strip()
        await event.edit(f'Reported @{user.username or user.id}: {reason}')
    except:
        await event.edit('Report error')

# ==================== CHAT ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stats$'))
async def stats_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    try:
        total = 0
        users = 0
        bots = 0
        async for user in client.iter_participants(event.chat_id, limit=150):
            total += 1
            if user.bot:
                bots += 1
            else:
                users += 1
        await event.edit(f'Stats:\nTotal: {total}\nUsers: {users}\nBots: {bots}')
    except:
        await event.edit('Stats error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.parse$'))
async def parse_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    try:
        members = []
        async for user in client.iter_participants(event.chat_id, limit=30):
            name = f'@{user.username}' if user.username else user.first_name or f'ID:{user.id}'
            members.append(name)
        await event.edit('Members (30):\n' + ', '.join(members))
    except:
        await event.edit('Parse error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.who (@?\w+)$'))
async def who_cmd(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await event.edit(f'Searching @{user.username or user.id}...')
        common = []
        async for dialog in client.iter_dialogs(limit=50):
            if dialog.is_group or dialog.is_channel:
                try:
                    participants = await client.get_participants(dialog.id, limit=20)
                    if any(p.id == user.id for p in participants):
                        common.append(dialog.name)
                except:
                    continue
        if common:
            await event.edit(f'Chats ({len(common)}):\n' + '\n'.join(common[:10]))
        else:
            await event.edit('No common chats')
    except:
        await event.edit('Who error')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.search (.+)$'))
async def search_cmd(event):
    query = event.pattern_match.group(1).strip()
    await event.edit(f'Search: {query}')
    results = []
    async for dialog in client.iter_dialogs(limit=50):
        try:
            messages = await client.get_messages(dialog.id, search=query, limit=1)
            if messages:
                results.append(dialog.name)
        except:
            continue
    if results:
        await event.edit(f'Found ({len(results)}):\n' + '\n'.join(results[:8]))
    else:
        await event.edit('No results')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.fake$'))
async def fake_cmd(event):
    first = random.choice(['John','Jane','Alex','Maria','David','Sarah'])
    last = random.choice(['Smith','Johnson','Williams','Brown','Jones'])
    email = f'{first.lower()}{random.randint(1,99)}@example.com'
    phone = f'+1{random.randint(100,999)}{random.randint(100,999)}{random.randint(1000,9999)}'
    text = f"""Fake
Name: {first} {last}
Email: {email}
Phone: {phone}
Address: {random.randint(1,999)} Fake St"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.quote$'))
async def quote_cmd(event):
    quotes = [
        "The only way to do great work is to love what you do.",
        "Innovation distinguishes between a leader and a follower.",
        "Your time is limited, don't waste it living someone else's life.",
        "Stay hungry, stay foolish.",
        "The future belongs to those who believe in the beauty of their dreams."
    ]
    await event.edit(f'Quote: {random.choice(quotes)}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.whois$'))
async def whois_cmd(event):
    if not event.is_group:
        await event.edit('Group only')
        return
    try:
        participants = await client.get_participants(event.chat_id, limit=80)
        if participants:
            user = random.choice(participants)
            name = f'@{user.username}' if user.username else user.first_name
            await event.edit(f'Random: {name}')
        else:
            await event.edit('No members')
    except:
        await event.edit('Whois error')

# ==================== START ====================
async def start_bot():
    await client.start()
    me = await client.get_me()
    print(f"Started: @{me.username or me.id}")
    print(f"Time: {client.start_time}")
    
    def run_flask():
        waitress.serve(app, host='0.0.0.0', port=PORT)
    
    Thread(target=run_flask, daemon=True).start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    import os
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        db.close()
