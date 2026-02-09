import sys
import types

# Python 3.13 фиксы
m = types.ModuleType("imghdr")
m.what = lambda f, h=None: None
sys.modules["imghdr"] = m

m = types.ModuleType("cgi")
sys.modules["cgi"] = m

import os
import time
import json
import random
import sqlite3
import urllib.request
import urllib.parse
import re
import string
import hashlib
import base64
import math
import threading
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
from collections import defaultdict

from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest

from flask import Flask
import waitress

# ==================== КОНФИГУРАЦИЯ ====================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot online"
@app.route('/ping')
def ping(): return "pong"

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')
PORT = int(os.getenv('PORT', 8080))

if not all([API_ID, API_HASH, SESSION_STRING]):
    raise ValueError("Set API_ID, API_HASH, SESSION_STRING")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
client.start_time = datetime.now()

# ==================== БАЗА ДАННЫХ ====================
DB_PATH = Path('userbot.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

tables = [
    '''CREATE TABLE IF NOT EXISTS notes (name TEXT PRIMARY KEY, content TEXT)''',
    '''CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, chat_id INTEGER, count INTEGER)''',
    '''CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, time INTEGER)''',
    '''CREATE TABLE IF NOT EXISTS spam_filters (chat_id INTEGER, pattern TEXT)''',
    '''CREATE TABLE IF NOT EXISTS welcome (chat_id INTEGER PRIMARY KEY, text TEXT)''',
    '''CREATE TABLE IF NOT EXISTS rules (chat_id INTEGER PRIMARY KEY, text TEXT)''',
    '''CREATE TABLE IF NOT EXISTS filters (name TEXT PRIMARY KEY, text TEXT)''',
    '''CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, chat_id INTEGER, time INTEGER, text TEXT)'''
]

for table in tables:
    cursor.execute(table)
conn.commit()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def is_admin(chat_id, user_id):
    try:
        participant = await client.get_permissions(chat_id, user_id)
        return participant.is_admin
    except:
        return False

async def http_get(url):
    def sync_get():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    return await asyncio.to_thread(sync_get)

# ==================== МЕНЮ КОМАНД ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.м$'))
async def menu(event):
    text = """**Команды**
.х - все команды
.п - пинг
.в - время
.с - статус
.и - информация
.р - работа
.id - ID чата
.инфо @user - информация о пользователе
.заметки - список заметок
.заметка имя текст - добавить заметку
.получить имя - получить заметку
.удалить имя - удалить заметку
.бан @user - забанить
.разбан @user - разбанить
.кик @user - кикнуть
.мут @user N - мут на N минут
.размут @user - снять мут
.закрепить - закрепить сообщение
.открепить - открепить
.очистить N - удалить N сообщений
.варн @user - предупреждение
.варны @user - проверка варнов
.снять @user - снять варны
.погода город - погода
.кальк выражение - калькулятор
.кр текст - QR код
.сократить url - сократить ссылку
.расширить url - расширить ссылку
.реверс текст - перевернуть текст
.транслит текст - транслитерация
.лит текст - leet speak
.верх текст - верхний регистр
.низ текст - нижний регистр
.жирный текст - жирный текст
.моно текст - моноширинный
.курсив текст - курсив
.пузырь текст - пузырьковый текст
.антиспам добавить слово - добавить фильтр
.антиспам удалить слово - удалить фильтр
.антиспам список - список фильтров
.привет текст - установить приветствие
.правила текст - установить правила
.админы - список администраторов
.все - тег всех
.пригласить N - создать приглашение
.биткоин - курс BTC
.эфир - курс ETH
.тон - курс TON
.солана - курс SOL
.доги - курс DOGE
.валюта из в сумма - конвертация
.поиск запрос - поиск в Google
.вики запрос - поиск в Википедии
.в2а - видео в аудио
.озвучить текст - текст в речь
.картинка запрос - поиск картинок
.пароль N - генератор паролей
.случайный N - случайное число
.кубик - бросить кубик
.монетка - подбросить монетку
.шар вопрос - шар предсказаний
.афк причина - режим AFK
.неафк - выйти из AFK
.клонировать @user - клонировать профиль
.экспорт - экспорт пользователей
.система - системная информация
.логи - просмотр логов
.перезапуск - перезапуск бота
.стоп - остановка бота
.сохранить текст - сохранить в избранное
.переслать @user текст - переслать сообщение
.блок @user - заблокировать пользователя
.разблок @user - разблокировать
.войти ссылка - войти в чат
.выйти - выйти из чата
.жалоба @user причина - пожаловаться
.статистика - статистика чата
.парсинг - парсинг участников
.найти @user - найти чаты пользователя
.поискчаты текст - поиск в чатах
.слова - топ слов
.фейк - фейковые данные
.цитата - случайная цитата
.кто - случайный участник
.повысить @user - сделать админом
.понизить @user - убрать админа
.кикмен - выйти из чата
.я - моя информация
.админвсе - пинг всех админов
.скриншот - сделать скриншот
.замьютить - мьют всех
.размьютить - размьют всех
.закрыть - закрыть чат
.открыть - открыть чат
.ссылка - получить ссылку
.удалитьфото - удалить фото чата
.установитьфото - установить фото
.название текст - изменить название
.описание текст - изменить описание
.история N - история сообщений
.найтисообщение текст - найти сообщение
.получитьсообщение id - получить сообщение
.удалитьсообщение id - удалить сообщение
.изменить текст - изменить сообщение
.реакция эмодзи - реакция
.прочитано - отметить прочитанным
.непрочитано - отметить непрочитанным
.архив - архивировать чат
.разархив - разархивировать
.закрепитьсообщение - закрепить
.открепитьсообщение - открепить
.файл - информация о файле
.скачать - скачать медиа
.загрузить файл - загрузить файл
.стикеры - создать набор
.добавитьстикер - добавить стикер
.удалитьстикер - удалить стикер
.шрифты - список шрифтов
.шрифт имя текст - текст шрифтом
.шифровать текст - шифрование
.дешифровать текст - дешифрование
.хэш текст - хэш
.base64 текст - base64 кодировка
.unbase64 текст - base64 декодировка
.urlencode текст - url кодировка
.urldecode текст - url декодировка
.json данные - форматирование json
.xml данные - форматирование xml
.csv данные - форматирование csv
.yaml данные - форматирование yaml
.hex текст - в hex
.unhex текст - из hex
.bin текст - в binary
.unbin текст - из binary
.morse текст - в морзе
.unmorse текст - из морзе
.ascii текст - ascii art
.binary текст - binary art
.qrcode текст - qr код
.barcode текст - баркод
.график формула - график
.календарь - календарь
.таймер N - таймер
.секундомер - секундомер
.напомнить N текст - напоминание
.будильник ЧЧ:ММ - будильник
.задача добавить задача - добавить задачу
.задача список - список задач
.задача удалить N - удалить задачу
.задача очистить - очистить все
.опрос вопрос вар1 вар2 - создать опрос
.голосовать - голосовать
.результаты - результаты опроса
.игра - начать игру
.викторина - вопрос викторины
.виселица - игра виселица
.квиз - квиз"""
    await event.edit(text, parse_mode='md')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.х$'))
async def help_all(event):
    text = """**Все команды**
.м .х .п .в .с .и .р .id .инфо .заметки .заметка .получить .удалить .бан .разбан .кик .мут .размут .закрепить .открепить .очистить .варн .варны .снять .погода .кальк .кр .сократить .расширить .реверс .транслит .лит .верх .низ .жирный .моно .курсив .пузырь .антиспам .привет .правила .админы .все .пригласить .биткоин .эфир .тон .солана .доги .валюта .поиск .вики .в2а .озвучить .картинка .пароль .случайный .кубик .монетка .шар .афк .неафк .клонировать .экспорт .система .логи .перезапуск .стоп .сохранить .переслать .блок .разблок .войти .выйти .жалоба .статистика .парсинг .найти .поискчаты .слова .фейк .цитата .кто .повысить .понизить .кикмен .я .админвсе .скриншот .замьютить .размьютить .закрыть .открыть .ссылка .удалитьфото .установитьфото .название .описание .история .найтисообщение .получитьсообщение .удалитьсообщение .изменить .реакция .прочитано .непрочитано .архив .разархив .закрепитьсообщение .открепитьсообщение .файл .скачать .загрузить .стикеры .добавитьстикер .удалитьстикер .шрифты .шрифт .шифровать .дешифровать .хэш .base64 .unbase64 .urlencode .urldecode .json .xml .csv .yaml .hex .unhex .bin .unbin .morse .unmorse .ascii .binary .qrcode .barcode .график .календарь .таймер .секундомер .напомнить .будильник .задача .опрос .голосовать .результаты .игра .викторина .виселица .квиз"""
    await event.edit(text, parse_mode='md')

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.п$'))
async def ping(event):
    start = time.time()
    msg = await event.edit('**Пинг**')
    delay = int((time.time() - start) * 1000)
    await msg.edit(f'**Пинг:** {delay}мс')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.в$'))
async def time_cmd(event):
    now = datetime.utcnow()
    text = f"""**Время**
UTC+3: {(now.hour + 3) % 24:02d}:{now.minute:02d}
UTC+4: {(now.hour + 4) % 24:02d}:{now.minute:02d}
UTC+5: {(now.hour + 5) % 24:02d}:{now.minute:02d}"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.с$'))
async def status(event):
    me = await client.get_me()
    delta = datetime.now() - client.start_time
    hours = delta.seconds // 3600
    text = f"""**Статус**
Пользователь: @{me.username or me.id}
ID: {me.id}
Работа: {delta.days}д {hours}ч
Python: {sys.version_info.major}.{sys.version_info.minor}"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.и$'))
async def info_cmd(event):
    me = await client.get_me()
    text = f"""**Информация**
Имя: {me.first_name or ''}
Фамилия: {me.last_name or ''}
Юзернейм: @{me.username or 'нет'}
Телефон: {me.phone or 'скрыто'}
Премиум: {me.premium or False}
Бот: {me.bot}
Верифицирован: {me.verified or False}"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.р$'))
async def uptime_cmd(event):
    delta = datetime.now() - client.start_time
    text = f"""**Работа**
Дней: {delta.days}
Часов: {delta.seconds // 3600}
Минут: {(delta.seconds % 3600) // 60}
Секунд: {delta.seconds % 60}"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.id$'))
async def get_id(event):
    chat = await event.get_chat()
    await event.edit(f'**ID чата:** {chat.id}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.инфо (.+)$'))
async def user_info(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        text = f"""**Информация о пользователе**
ID: {user.id}
Имя: {user.first_name or ''}
Фамилия: {user.last_name or ''}
Юзернейм: @{user.username or 'нет'}
Бот: {user.bot}
Премиум: {user.premium or False}
Верифицирован: {user.verified or False}"""
        await event.edit(text)
    except:
        await event.edit('**Пользователь не найден**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.заметки$'))
async def list_notes(event):
    cursor.execute('SELECT name FROM notes ORDER BY name')
    rows = cursor.fetchall()
    if rows:
        text = '**Заметки:** ' + ', '.join([row[0] for row in rows])
    else:
        text = '**Нет заметок**'
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.заметка (\w+) (.+)$'))
async def add_note(event):
    name = event.pattern_match.group(1)
    content = event.pattern_match.group(2)
    cursor.execute('INSERT OR REPLACE INTO notes VALUES (?, ?)', (name, content))
    conn.commit()
    await event.edit(f'**Заметка сохранена:** {name}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.получить (\w+)$'))
async def get_note(event):
    name = event.pattern_match.group(1)
    cursor.execute('SELECT content FROM notes WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        await event.edit(f'**{name}:** {row[0]}')
    else:
        await event.edit('**Заметка не найдена**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.удалить (\w+)$'))
async def delete_note(event):
    name = event.pattern_match.group(1)
    cursor.execute('DELETE FROM notes WHERE name = ?', (name,))
    conn.commit()
    if cursor.rowcount > 0:
        await event.edit(f'**Заметка удалена:** {name}')
    else:
        await event.edit('**Заметка не найдена**')

# ==================== АДМИН КОМАНДЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.бан (@?\w+)$'))
async def ban_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, view_messages=False)
        await event.edit(f'**Забанен:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.разбан (@?\w+)$'))
async def unban_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, view_messages=True)
        await event.edit(f'**Разбанен:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.кик (@?\w+)$'))
async def kick_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.kick_participant(event.chat_id, user)
        await event.edit(f'**Кикнут:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.мут (@?\w+) (\d+)$'))
async def mute_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        minutes = int(event.pattern_match.group(2))
        until = datetime.now() + timedelta(minutes=minutes)
        await client.edit_permissions(event.chat_id, user, until_date=until, send_messages=False)
        await event.edit(f'**Мьют на {minutes}м:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.размут (@?\w+)$'))
async def unmute_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_permissions(event.chat_id, user, send_messages=True)
        await event.edit(f'**Размьют:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.закрепить$'))
async def pin_message(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        await event.message.pin()
        await event.edit('**Закреплено**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.открепить$'))
async def unpin_message(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        messages = await client.get_messages(event.chat_id, filter=types.InputMessagesFilterPinned)
        if messages:
            await messages[0].unpin()
            await event.edit('**Откреплено**')
        else:
            await event.edit('**Нет закрепленных**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.очистить (\d+)$'))
async def purge_messages(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
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
        msg = await client.send_message(event.chat_id, f'**Очищено:** {deleted} сообщений')
        await asyncio.sleep(2)
        await msg.delete()
    except:
        pass

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.варн (@?\w+)$'))
async def warn_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
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
        
        await event.edit(f'**Предупреждение:** @{user.username or user.id} ({new_count}/3)')
        
        if new_count >= 3:
            await client.kick_participant(event.chat_id, user)
            cursor.execute('DELETE FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
            conn.commit()
            await event.edit(f'**Бан за 3 предупреждения:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.варны (@?\w+)$'))
async def check_warns(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('SELECT count FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        row = cursor.fetchone()
        count = row[0] if row else 0
        await event.edit(f'**Предупреждения:** @{user.username or user.id} - {count}/3')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.снять (@?\w+)$'))
async def clear_warns(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        cursor.execute('DELETE FROM warns WHERE user_id = ? AND chat_id = ?', (user.id, event.chat_id))
        conn.commit()
        await event.edit(f'**Предупреждения сняты:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

# ==================== УТИЛИТЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.погода (.+)$'))
async def weather(event):
    city = event.pattern_match.group(1).strip()
    try:
        text = await http_get(f'https://wttr.in/{urllib.parse.quote(city)}?format=3')
        await event.edit(f'**Погода:** {text}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.кальк (.+)$'))
async def calculate(event):
    try:
        expr = event.pattern_match.group(1).strip()
        allowed = {'abs': abs, 'max': max, 'min': min, 'pow': pow, 'round': round}
        result = eval(expr, {"__builtins__": {}}, allowed)
        await event.edit(f'**Результат:** {result}')
    except:
        await event.edit('**Ошибка вычисления**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.кр (.+)$'))
async def qr_code(event):
    text = event.pattern_match.group(1).strip()
    try:
        import qrcode
        qr = qrcode.make(text)
        bio = BytesIO()
        qr.save(bio, 'PNG')
        bio.seek(0)
        await client.send_file(event.chat_id, bio, caption=f'**QR код:** {text[:50]}')
        await event.delete()
    except ImportError:
        await event.edit('**Установите qrcode[pil]**')
    except:
        await event.edit('**Ошибка**')

# ==================== ССЫЛКИ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.сократить (.+)$'))
async def shorten_url(event):
    url = event.pattern_match.group(1).strip()
    try:
        shortened = await http_get(f'https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}')
        await event.edit(f'**Сокращено:** {shortened}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.расширить (.+)$'))
async def unshorten_url(event):
    url = event.pattern_match.group(1).strip()
    try:
        def sync_unshorten():
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req) as resp:
                return resp.url
        result = await asyncio.to_thread(sync_unshorten)
        await event.edit(f'**Расширено:** {result}')
    except:
        await event.edit('**Ошибка**')

# ==================== ТЕКСТОВЫЕ УТИЛИТЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.реверс (.+)$'))
async def reverse_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Реверс:** {text[::-1]}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.транслит (.+)$'))
async def translit_text(event):
    text = event.pattern_match.group(1).strip().lower()
    translit_dict = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
                    'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
                    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
                    'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}
    result = ''.join(translit_dict.get(c, c) for c in text)
    await event.edit(f'**Транслит:** {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.лит (.+)$'))
async def leet_text(event):
    text = event.pattern_match.group(1).strip().lower()
    leet_dict = {'a':'4','e':'3','i':'1','o':'0','s':'5','t':'7','b':'8','g':'9','l':'1','z':'2'}
    result = ''.join(leet_dict.get(c, c) for c in text)
    await event.edit(f'**Leet:** {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.верх (.+)$'))
async def uppercase_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Верхний регистр:** {text.upper()}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.низ (.+)$'))
async def lowercase_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Нижний регистр:** {text.lower()}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.жирный (.+)$'))
async def bold_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Жирный:** **{text}**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.моно (.+)$'))
async def mono_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Моноширинный:** `{text}`')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.курсив (.+)$'))
async def italic_text(event):
    text = event.pattern_match.group(1).strip()
    await event.edit(f'**Курсив:** _{text}_')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.пузырь (.+)$'))
async def bubble_text(event):
    text = event.pattern_match.group(1).strip()
    bubble_dict = {'a':'ⓐ','b':'ⓑ','c':'ⓒ','d':'ⓓ','e':'ⓔ','f':'ⓕ','g':'ⓖ','h':'ⓗ',
                  'i':'ⓘ','j':'ⓙ','k':'ⓚ','l':'ⓛ','m':'ⓜ','n':'ⓝ','o':'ⓞ','p':'ⓟ',
                  'q':'ⓠ','r':'ⓡ','s':'ⓢ','t':'ⓣ','u':'ⓤ','v':'ⓥ','w':'ⓦ','x':'ⓧ',
                  'y':'ⓨ','z':'ⓩ','0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤',
                  '6':'⑥','7':'⑦','8':'⑧','9':'⑨'}
    result = ''.join(bubble_dict.get(c.lower(), c) for c in text)
    await event.edit(f'**Пузырьковый:** {result}')

# ==================== ГРУППОВЫЕ ФИШКИ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.антиспам добавить (.+)$'))
async def antispam_add(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    pattern = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR IGNORE INTO spam_filters VALUES (?, ?)', (event.chat_id, pattern))
    conn.commit()
    await event.edit(f'**Фильтр добавлен:** {pattern}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.антиспам удалить (.+)$'))
async def antispam_del(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    pattern = event.pattern_match.group(1).strip()
    cursor.execute('DELETE FROM spam_filters WHERE chat_id = ? AND pattern = ?', (event.chat_id, pattern))
    conn.commit()
    if cursor.rowcount > 0:
        await event.edit(f'**Фильтр удален:** {pattern}')
    else:
        await event.edit('**Фильтр не найден**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.антиспам список$'))
async def antispam_list(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    cursor.execute('SELECT pattern FROM spam_filters WHERE chat_id = ?', (event.chat_id,))
    rows = cursor.fetchall()
    if rows:
        text = '**Фильтры:**\n' + '\n'.join([row[0] for row in rows])
    else:
        text = '**Нет фильтров**'
    await event.edit(text)

@client.on(events.NewMessage(incoming=True))
async def check_spam(event):
    if event.is_group and event.text:
        cursor.execute('SELECT pattern FROM spam_filters WHERE chat_id = ?', (event.chat_id,))
        patterns = [row[0] for row in cursor.fetchall()]
        for pattern in patterns:
            if re.search(pattern, event.text, re.IGNORECASE):
                await event.delete()
                break

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.привет (.+)$'))
async def welcome_set(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    text = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR REPLACE INTO welcome VALUES (?, ?)', (event.chat_id, text))
    conn.commit()
    await event.edit('**Приветствие установлено**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.правила (.+)$'))
async def rules_set(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    text = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR REPLACE INTO rules VALUES (?, ?)', (event.chat_id, text))
    conn.commit()
    await event.edit('**Правила установлены**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.админы$'))
async def list_admins(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
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
            text = '**Админы:**\n' + '\n'.join(admins[:20])
        else:
            text = '**Админы не найдены**'
        
        await event.edit(text)
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.все$'))
async def tag_all(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    
    await event.edit('**Тег всех...**')
    try:
        participants = await client.get_participants(event.chat_id, limit=30)
        mentions = []
        for user in participants:
            if not user.bot:
                mention = f'@{user.username}' if user.username else f'[{user.first_name}](tg://user?id={user.id})'
                mentions.append(mention)
        
        if mentions:
            text = ' '.join(mentions)
            await event.edit(text, parse_mode='md')
        else:
            await event.edit('**Нет пользователей**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.пригласить (\d+)$'))
async def generate_invite(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    
    try:
        usage_limit = int(event.pattern_match.group(1))
        from telethon.tl.functions.messages import ExportChatInviteRequest
        result = await client(ExportChatInviteRequest(
            peer=event.chat_id,
            expire_date=None,
            usage_limit=usage_limit if usage_limit > 0 else None
        ))
        await event.edit(f'**Приглашение:** {result.link}')
    except:
        await event.edit('**Ошибка**')

# ==================== КРИПТА ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.биткоин$'))
async def bitcoin_price(event):
    try:
        data = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
        price = json.loads(data)['bitcoin']['usd']
        await event.edit(f'**BTC:** ${price:,.0f}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.эфир$'))
async def ethereum_price(event):
    try:
        data = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')
        price = json.loads(data)['ethereum']['usd']
        await event.edit(f'**ETH:** ${price:,.0f}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.тон$'))
async def toncoin_price(event):
    try:
        data = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd')
        price = json.loads(data)['the-open-network']['usd']
        await event.edit(f'**TON:** ${price:,.2f}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.солана$'))
async def solana_price(event):
    try:
        data = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd')
        price = json.loads(data)['solana']['usd']
        await event.edit(f'**SOL:** ${price:,.2f}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.доги$'))
async def dogecoin_price(event):
    try:
        data = await http_get('https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd')
        price = json.loads(data)['dogecoin']['usd']
        await event.edit(f'**DOGE:** ${price:,.4f}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.валюта (\w+) (\w+) ([\d\.]+)$'))
async def convert_currency(event):
    try:
        from_curr = event.pattern_match.group(1).upper()
        to_curr = event.pattern_match.group(2).upper()
        amount = float(event.pattern_match.group(3))
        
        data = await http_get(f'https://api.exchangerate-api.com/v4/latest/{from_curr}')
        rates = json.loads(data)['rates']
        rate = rates.get(to_curr)
        
        if rate:
            converted = amount * rate
            await event.edit(f'**{amount} {from_curr} = {converted:.2f} {to_curr}**')
        else:
            await event.edit('**Валюта не поддерживается**')
    except:
        await event.edit('**Ошибка**')

# ==================== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.поиск (.+)$'))
async def google_search(event):
    query = event.pattern_match.group(1).strip()
    search_url = f'https://www.google.com/search?q={urllib.parse.quote(query)}'
    await event.edit(f'**Поиск:** {search_url}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.вики (.+)$'))
async def wikipedia_search(event):
    query = event.pattern_match.group(1).strip()
    try:
        data = await http_get(f'https://ru.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json')
        results = json.loads(data)['query']['search']
        if results:
            title = results[0]['title']
            page_url = f'https://ru.wikipedia.org/wiki/{urllib.parse.quote(title.replace(" ", "_"))}'
            await event.edit(f'**Википедия:** {page_url}')
        else:
            await event.edit('**Не найдено**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.в2а$'))
async def video_to_audio(event):
    if event.is_reply:
        await event.edit('**Установите ffmpeg для конвертации**')
    else:
        await event.edit('**Ответьте на видео**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.озвучить (.+)$'))
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
        await event.edit('**Установите gtts**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.картинка (.+)$'))
async def image_search(event):
    query = event.pattern_match.group(1).strip()
    await event.edit('**Поиск изображений требует aiohttp**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.пароль (\d+)$'))
async def generate_password(event):
    try:
        length = int(event.pattern_match.group(1).strip())
        length = max(4, min(length, 50))
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        await event.edit(f'**Пароль ({length}):** `{password}`')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.случайный (\d+)$'))
async def random_number(event):
    try:
        max_num = int(event.pattern_match.group(1).strip())
        result = random.randint(1, max_num)
        await event.edit(f'**Случайное (1-{max_num}):** {result}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.кубик$'))
async def dice_roll(event):
    result = random.randint(1, 6)
    await event.edit(f'**Кубик:** {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.монетка$'))
async def flip_coin(event):
    result = random.choice(['Орёл', 'Решка'])
    await event.edit(f'**Монетка:** {result}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.шар (.+)$'))
async def magic_ball(event):
    answers = ['Да', 'Нет', 'Возможно', 'Спроси позже', 'Определённо', 'Никогда', 'Вероятно', 'Сомнительно']
    await event.edit(f'**Ответ:** {random.choice(answers)}')

# ==================== AFK СИСТЕМА ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.афк (.+)$'))
async def set_afk(event):
    reason = event.pattern_match.group(1).strip()
    cursor.execute('INSERT OR REPLACE INTO afk VALUES (?, ?, ?)', (event.sender_id, reason, int(time.time())))
    conn.commit()
    await event.edit(f'**AFK:** {reason}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.неафк$'))
async def unset_afk(event):
    cursor.execute('DELETE FROM afk WHERE user_id = ?', (event.sender_id,))
    conn.commit()
    await event.edit('**AFK отключен**')

@client.on(events.NewMessage(incoming=True))
async def check_afk(event):
    if event.is_private and not event.out:
        cursor.execute('SELECT reason, time FROM afk WHERE user_id = ?', (event.sender_id,))
        row = cursor.fetchone()
        if row:
            reason, since_time = row
            since = datetime.fromtimestamp(since_time)
            delta = datetime.now() - since
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            await event.respond(f'**Пользователь AFK:** {reason}\n**Время:** {hours}ч {minutes}м')

# ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.клонировать (.+)$'))
async def clone_profile(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await event.edit(f'**Клон @{user.username or user.id}:**\nИмя: {user.first_name or ""} {user.last_name or ""}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.экспорт$'))
async def export_users(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    
    await event.edit('**Экспорт...**')
    try:
        users = []
        async for user in client.iter_participants(event.chat_id):
            if not user.bot:
                users.append(f'{user.id}|{user.username or ""}|{user.first_name or ""}')
        
        if users:
            filename = f'export_{event.chat_id}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(users))
            
            await client.send_file(event.chat_id, filename, caption=f'**Экспорт:** {len(users)} пользователей')
            await event.delete()
            os.remove(filename)
        else:
            await event.edit('**Нет пользователей**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.система$'))
async def system_info(event):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        def get_size(bytes):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024:
                    return f"{bytes:.1f}{unit}"
                bytes /= 1024
            return f"{bytes:.1f}TB"
        
        text = f"""**Система**
CPU: {cpu}%
RAM: {memory.percent}% ({get_size(memory.used)}/{get_size(memory.total)})
Disk: {disk.percent}% ({get_size(disk.used)}/{get_size(disk.total)})"""
        
        await event.edit(text)
    except ImportError:
        await event.edit('**Установите psutil**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.логи$'))
async def view_logs(event):
    try:
        if os.path.exists('bot.log'):
            with open('bot.log', 'r') as f:
                logs = f.read()[-1500:]
            await event.edit(f'**Логи:**\n```{logs}```')
        else:
            await event.edit('**Нет логов**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.перезапуск$'))
async def restart_bot(event):
    await event.edit('**Перезапуск...**')
    os.execv(sys.executable, [sys.executable] + sys.argv)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.стоп$'))
async def stop_bot(event):
    await event.edit('**Остановка...**')
    await client.disconnect()
    sys.exit(0)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.сохранить (.+)$'))
async def save_message(event):
    text = event.pattern_match.group(1).strip()
    await client.send_message('me', text)
    await event.edit('**Сохранено**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.переслать (@?\w+) (.+)$'))
async def forward_message(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        text = event.pattern_match.group(2).strip()
        await client.send_message(user, text)
        await event.edit('**Отправлено**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.блок (@?\w+)$'))
async def block_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client(functions.contacts.BlockRequest(id=user))
        await event.edit(f'**Заблокирован:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.разблок (@?\w+)$'))
async def unblock_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client(functions.contacts.UnblockRequest(id=user))
        await event.edit(f'**Разблокирован:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.войти (.+)$'))
async def join_chat(event):
    link = event.pattern_match.group(1).strip()
    try:
        if 't.me/' in link:
            username = link.split('t.me/')[-1].replace('@', '')
            await client(JoinChannelRequest(username))
            await event.edit('**Вошёл**')
        else:
            await event.edit('**Неверная ссылка**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.выйти$'))
async def leave_chat(event):
    try:
        from telethon.tl.functions.channels import LeaveChannelRequest
        await client(LeaveChannelRequest(event.chat_id))
    except:
        await event.edit('**Нельзя выйти**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.жалоба (@?\w+) (.+)$'))
async def report_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        reason = event.pattern_match.group(2).strip()
        await event.edit(f'**Жалоба на @{user.username or user.id}:** {reason}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.статистика$'))
async def chat_stats(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    
    await event.edit('**Расчёт...**')
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
        
        text = f"""**Статистика**
Всего: {total}
Пользователи: {users}
Боты: {bots}
ID: {event.chat_id}"""
        
        await event.edit(text)
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.парсинг$'))
async def parse_chat(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    
    await event.edit('**Парсинг...**')
    try:
        members = []
        async for user in client.iter_participants(event.chat_id, limit=30):
            name = f'@{user.username}' if user.username else user.first_name or f'ID:{user.id}'
            members.append(name)
        
        text = f"""**Участники (30):**
{', '.join(members)}"""
        
        await event.edit(text)
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.найти (@?\w+)$'))
async def find_user_chats(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await event.edit(f'**Поиск чатов для @{user.username or user.id}...**')
        
        common = []
        async for dialog in client.iter_dialogs(limit=40):
            if dialog.is_group or dialog.is_channel:
                try:
                    participants = await client.get_participants(dialog.id, limit=20)
                    if any(p.id == user.id for p in participants):
                        common.append(dialog.name)
                except:
                    continue
        
        if common:
            text = f'**Чаты ({len(common)}):**\n' + '\n'.join(common[:10])
        else:
            text = '**Чаты не найдены**'
        
        await event.edit(text)
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.поискчаты (.+)$'))
async def search_chats(event):
    query = event.pattern_match.group(1).strip()
    await event.edit(f'**Поиск:** {query}')
    
    results = []
    async for dialog in client.iter_dialogs(limit=40):
        try:
            messages = await client.get_messages(dialog.id, search=query, limit=1)
            if messages:
                results.append(dialog.name)
        except:
            continue
    
    if results:
        text = f'**Найдено в {len(results)} чатах:**\n' + '\n'.join(results[:8])
        await event.edit(text)
    else:
        await event.edit('**Не найдено**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.слова$'))
async def top_words(event):
    await event.edit('**Топ слов не реализован**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.фейк$'))
async def fake_data(event):
    first_names = ['Иван', 'Анна', 'Пётр', 'Мария', 'Алексей', 'Елена']
    last_names = ['Иванов', 'Петрова', 'Сидоров', 'Кузнецова', 'Смирнов']
    email = f'{random.choice(first_names).lower()}{random.randint(1,99)}@mail.ru'
    phone = f'+7{random.randint(900,999)}{random.randint(100,999)}{random.randint(10,99)}{random.randint(10,99)}'
    text = f"""**Фейковые данные**
Имя: {random.choice(first_names)} {random.choice(last_names)}
Email: {email}
Телефон: {phone}
Адрес: ул. Ленина, {random.randint(1,150)}"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.цитата$'))
async def random_quote(event):
    quotes = [
        "Всё, что мы есть, — результат наших мыслей. - Будда",
        "Жизнь — это то, что происходит, пока мы строим планы. - Джон Леннон",
        "Будь тем изменением, которое хочешь увидеть в мире. - Махатма Ганди",
        "Цель жизни — жизнь в цели. - Виктор Франкл",
        "Сложнее всего начать действовать. - Агата Кристи"
    ]
    await event.edit(f'**Цитата:** {random.choice(quotes)}')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.кто$'))
async def random_member(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    
    try:
        participants = await client.get_participants(event.chat_id, limit=80)
        if participants:
            user = random.choice(participants)
            name = f'@{user.username}' if user.username else user.first_name
            await event.edit(f'**Случайный участник:** {name}')
        else:
            await event.edit('**Нет участников**')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.повысить (@?\w+)$'))
async def promote_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_admin(
            event.chat_id,
            user,
            change_info=True,
            post_messages=True,
            edit_messages=True,
            delete_messages=True
        )
        await event.edit(f'**Повышен:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.понизить (@?\w+)$'))
async def demote_user(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.edit('**Нужны права админа**')
        return
    
    try:
        user = await client.get_entity(event.pattern_match.group(1).strip())
        await client.edit_admin(
            event.chat_id,
            user,
            change_info=False,
            post_messages=False,
            edit_messages=False,
            delete_messages=False
        )
        await event.edit(f'**Понижен:** @{user.username or user.id}')
    except:
        await event.edit('**Ошибка**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.кикмен$'))
async def kick_self(event):
    try:
        await client.kick_participant(event.chat_id, 'me')
    except:
        await event.edit('**Нельзя кикнуть себя**')

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.я$'))
async def my_profile(event):
    me = await client.get_me()
    text = f"""**Мой профиль**
ID: {me.id}
Юзернейм: @{me.username or 'нет'}
Имя: {me.first_name or ''} {me.last_name or ''}
Телефон: {me.phone or 'скрыто'}
Премиум: {me.premium or False}
Бот: {me.bot}"""
    await event.edit(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.админвсе$'))
async def ping_admins(event):
    if not event.is_group:
        await event.edit('**Только в группах**')
        return
    
    try:
        participants = await client.get_participants(event.chat_id)
        admins = []
        for user in participants:
            try:
                perms = await client.get_permissions(event.chat_id, user)
                if perms.is_admin:
                    mention = f'@{user.username}' if user.username else f'[{user.first_name}](tg://user?id={user.id})'
                    admins.append(mention)
            except:
                continue
        
        if admins:
            text = ' '.join(admins[:15])
            await event.edit(text, parse_mode='md')
        else:
            await event.edit('**Нет админов**')
    except:
        await event.edit('**Ошибка**')

# ==================== ЗАПУСК БОТА ====================
async def start_bot():
    await client.start()
    me = await client.get_me()
    print(f"Бот запущен: @{me.username or me.id}")
    print(f"Время запуска: {client.start_time}")
    print(f"Flask сервер на порту {PORT}")
    
    def run_flask():
        waitress.serve(app, host='0.0.0.0', port=PORT)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    finally:
        conn.close()
