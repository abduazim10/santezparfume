import asyncio
import logging
import os
from datetime import datetime, timedelta
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove,
)
from dotenv import load_dotenv

from database import Database

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB_PATH = os.getenv("DB_PATH", "santezparfume.db")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Put your Telegram bot token in .env")
if not ADMIN_IDS:
    raise RuntimeError("ADMIN_IDS is missing. Put at least one admin Telegram ID in .env")

logging.basicConfig(level=logging.INFO)
db = Database(DB_PATH)
bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

TEXT = {
 "ru": {
  "choose_lang":"Выберите язык / Tilni tanlang:","welcome":"Добро пожаловать в <b>Santez Parfume</b>!\nВыберите раздел:",
  "catalog":"Каталог","prices":"Цены","order":"Заказать","shops":"Для магазинов","contact":"Связаться","back":"⬅️ Назад","search":"🔎 Поиск ароматов","search_prompt":"Введите название аромата или бренда:","search_empty":"Ничего не найдено. Попробуйте другое название.","brands_menu":"🏷 Бренды","collections_menu":"✨ Подборки","page_count":"Страница {page}/{pages}","admin_search":"🔎 Найти парфюм","admin_perfume":"Парфюм: {name}\nНаличие: {status}\n10 мл: {p10}\n50 мл: {p50}\n100 мл: {p100}","back_list":"⬅️ К списку",
  "men":"Мужские ароматы","women":"Женские ароматы","brands":"Бренды","categories":"Подборки","choose":"Выберите раздел:",
  "empty":"В этой категории пока нет ароматов.","choose_perfume":"Выберите аромат:","volume":"Выберите объём:","qty":"Выберите количество кнопкой (или напишите число):",
  "name":"Введите ваше имя:","phone":"Отправьте номер телефона кнопкой или напишите его:","share_phone":"📱 Отправить номер телефона",
  "delivery":"Отправьте геолокацию или напишите адрес. Доставку и способ оплаты согласуем по телефону.",
  "share_location":"📍 Отправить геолокацию","order_done":"✅ Заявка отправлена! Администратор свяжется с вами для подтверждения заказа, доставки и оплаты.",
  "prices_info":"Цены указаны отдельно для каждого аромата и объёма в карточке аромата.","shops_info":"Для сотрудничества напишите администратору — условия обсудите напрямую.",
  "contact_info":"Связаться с администратором: {contacts}","status_stock":"✅ Есть в наличии","status_day":"🕒 Сделаем за 1 день","status_unknown":"Уточним наличие",
  "admin_only":"Эта команда доступна только администратору.","admin_menu":"<b>Админ-панель Santez Parfume</b>","orders":"📥 Заявки","add_perfume":"➕ Добавить парфюм",
  "add_gender":"➕ Добавить gender","add_brand":"➕ Добавить бренд","add_category":"➕ Добавить категорию","set_status":"🔄 Наличие парфюма",
  "set_prices":"💰 Изменить цены","assign_category":"🏷 Добавить в подборку","directories":"📚 Справочники","enter_name":"Введите название:",
  "pick_gender":"Выберите gender:","pick_brand":"Выберите бренд:","enter_p10":"Введите цену за 10 мл в сумах (только число):","enter_p50":"Введите цену за 50 мл в сумах (только число):",
  "enter_p100":"Введите цену за 100 мл в сумах (только число):","pick_status":"Выберите наличие:","added":"Сохранено.","pick_perfume":"Выберите парфюм:",
  "pick_category":"Выберите подборку:","no_categories":"Подборок пока нет. Сначала добавьте категорию.","enter_price_error":"Введите целое число 0 или больше.",
  "invalid_qty":"Введите целое число больше нуля.","cancel":"Отменено.","cancel_btn":"❌ Отмена","orders_empty":"Заявок пока нет.","not_priced":"Цена для этого объёма пока не указана. Пожалуйста, свяжитесь с администратором.",
  "shops":"Для магазинов","price_line":"10 мл: {p10}\n50 мл: {p50}\n100 мл: {p100}","order_admin":"🆕 <b>Заявка #{id}</b>\nПарфюм: {perfume}\nОбъём: {volume}\nЦена за шт.: {price}\nКоличество: {qty}\nСумма: {total}\nИмя: {name}\nТелефон: {phone}\nДоставка: {delivery}\nTelegram: {user}",
  "admin_price_saved":"Цены обновлены.","select_action":"Выберите действие:","price_prompt":"Введите три цены по очереди.","availability":"Наличие","gender":"Пол","brand":"Бренд",
  "qty_chosen":"Количество: {qty}","enter_photo":"Отправьте фото парфюма (именно как фото, не файлом) или нажмите «Пропустить». Фото необязательно.","skip":"⏭ Пропустить",
  "photo_wrong":"Нужна фотография. Отправьте фото или нажмите «Пропустить» / «Отмена».","photo_saved":"✅ Фото сохранено.","photo_removed":"Фото удалено.","set_photo":"🖼 Фото","remove_photo":"🗑 Убрать фото",
  "enter_photo_edit":"Отправьте новое фото парфюма (как фото, не файлом):","stale":"Сессия устарела. Выберите аромат в каталоге и начните заказ заново."
 },
 "uz": {
  "choose_lang":"Tilni tanlang / Выберите язык:","welcome":"<b>Santez Parfume</b> ga xush kelibsiz!\nBo‘limni tanlang:",
  "catalog":"Katalog","prices":"Narxlar","order":"Buyurtma berish","shops":"Do‘konlar uchun","contact":"Bog‘lanish","back":"⬅️ Orqaga","search":"🔎 Atir qidirish","search_prompt":"Atir yoki brend nomini kiriting:","search_empty":"Hech narsa topilmadi. Boshqa nom bilan urinib ko‘ring.","brands_menu":"🏷 Brendlar","collections_menu":"✨ To‘plamlar","page_count":"Sahifa {page}/{pages}","admin_search":"🔎 Atirni qidirish","admin_perfume":"Atir: {name}\nMavjudligi: {status}\n10 ml: {p10}\n50 ml: {p50}\n100 ml: {p100}","back_list":"⬅️ Ro‘yxatga",
  "men":"Erkaklar atirlari","women":"Ayollar atirlari","brands":"Brendlar","categories":"To‘plamlar","choose":"Bo‘limni tanlang:",
  "empty":"Bu bo‘limda hozircha atirlar yo‘q.","choose_perfume":"Atirni tanlang:","volume":"Hajmni tanlang:","qty":"Miqdorni tugma bilan tanlang (yoki raqam yozing):",
  "name":"Ismingizni kiriting:","phone":"Telefon raqamingizni tugma orqali yuboring yoki yozing:","share_phone":"📱 Telefon raqamni yuborish",
  "delivery":"Geolokatsiyani yuboring yoki manzilni yozing. Yetkazib berish va to‘lov telefon orqali kelishiladi.",
  "share_location":"📍 Geolokatsiyani yuborish","order_done":"✅ Buyurtmangiz yuborildi! Administrator tasdiqlash, yetkazib berish va to‘lovni kelishish uchun siz bilan bog‘lanadi.",
  "prices_info":"Narxlar har bir atir kartasida hajm bo‘yicha alohida ko‘rsatiladi.","shops_info":"Hamkorlik uchun administratorga yozing — shartlarni bevosita kelishasiz.",
  "contact_info":"Administrator bilan bog‘lanish: {contacts}","status_stock":"✅ Mavjud","status_day":"🕒 1 kunda tayyorlaymiz","status_unknown":"Mavjudligini aniqlaymiz",
  "admin_only":"Bu bo‘lim faqat administrator uchun.","admin_menu":"<b>Santez Parfume admin paneli</b>","orders":"📥 Buyurtmalar","add_perfume":"➕ Atir qo‘shish",
  "add_gender":"➕ Gender qo‘shish","add_brand":"➕ Brend qo‘shish","add_category":"➕ Kategoriya qo‘shish","set_status":"🔄 Atir mavjudligi",
  "set_prices":"💰 Narxlarni o‘zgartirish","assign_category":"🏷 To‘plamga qo‘shish","directories":"📚 Ro‘yxatlar","enter_name":"Nomini kiriting:",
  "pick_gender":"Genderni tanlang:","pick_brand":"Brendni tanlang:","enter_p10":"10 ml narxini so‘mda kiriting (faqat raqam):","enter_p50":"50 ml narxini so‘mda kiriting (faqat raqam):",
  "enter_p100":"100 ml narxini so‘mda kiriting (faqat raqam):","pick_status":"Mavjudlik holatini tanlang:","added":"Saqlandi.","pick_perfume":"Atirni tanlang:",
  "pick_category":"To‘plamni tanlang:","no_categories":"Hozircha to‘plamlar yo‘q. Avval kategoriya qo‘shing.","enter_price_error":"0 yoki undan katta butun son kiriting.",
  "invalid_qty":"Noldan katta butun son kiriting.","cancel":"Bekor qilindi.","cancel_btn":"❌ Bekor qilish","orders_empty":"Hozircha buyurtmalar yo‘q.","not_priced":"Bu hajm uchun narx kiritilmagan. Administrator bilan bog‘laning.",
  "price_line":"10 ml: {p10}\n50 ml: {p50}\n100 ml: {p100}","order_admin":"🆕 <b>Buyurtma #{id}</b>\nAtir: {perfume}\nHajm: {volume}\nDona narxi: {price}\nMiqdor: {qty}\nJami: {total}\nIsm: {name}\nTelefon: {phone}\nYetkazib berish: {delivery}\nTelegram: {user}",
  "admin_price_saved":"Narxlar yangilandi.","select_action":"Amalni tanlang:","price_prompt":"Uchta narxni ketma-ket kiriting.","availability":"Mavjudligi","gender":"Jinsi","brand":"Brend",
  "qty_chosen":"Miqdor: {qty}","enter_photo":"Atir rasmini yuboring (fayl emas, aynan rasm sifatida) yoki «O‘tkazib yuborish» tugmasini bosing. Rasm majburiy emas.","skip":"⏭ O‘tkazib yuborish",
  "photo_wrong":"Rasm kerak. Rasm yuboring yoki «O‘tkazib yuborish» / «Bekor qilish» tugmasini bosing.","photo_saved":"✅ Rasm saqlandi.","photo_removed":"Rasm o‘chirildi.","set_photo":"🖼 Rasm","remove_photo":"🗑 Rasmni o‘chirish",
  "enter_photo_edit":"Atirning yangi rasmini yuboring (fayl emas, rasm sifatida):","stale":"Sessiya eskirdi. Katalogdan atirni tanlab, buyurtmani qaytadan boshlang."
 }
}

def tr(lang, key, **kw):
    return TEXT.get(lang, TEXT['ru']).get(key, TEXT['ru'].get(key, key)).format(**kw)

class OrderFlow(StatesGroup):
    quantity=State(); name=State(); phone=State(); delivery=State()
class DirectoryFlow(StatesGroup):
    name=State()
class PerfumeFlow(StatesGroup):
    name=State(); gender=State(); brand=State(); p10=State(); p50=State(); p100=State(); photo=State(); status=State()
class PhotoFlow(StatesGroup):
    photo=State()
class PriceFlow(StatesGroup):
    p10=State(); p50=State(); p100=State()
class SearchFlow(StatesGroup):
    query=State()

GENDER_SEEDS = ['Мужской','Женский']
BRAND_SEEDS = ['Louis Vuitton','Tom Ford','Parfums de Marly','Dior','Amouage','Gucci','Giorgio Armani','Yves Saint Laurent','Chanel','HFC','Creed','Bvlgari','Roja','Emporio Armani','Montblanc','Jean Paul Gaultier','Kilian','Bleu','Victoria’s Secret','Versace','Yves Rocher','Другие']
INITIAL = {
 'Женский': ["HFC Devil’s Intrigue","Parfums de Marly Delina","Dior Miss Dior Blooming Bouquet","Amouage Guidance","Gucci Gorgeous Gardenia","Giorgio Armani My Way","Yves Saint Laurent Libre","Parfums de Marly Valaya Exclusif","Louis Vuitton Elves","Chanel Chance Eau Tendre"],
 'Мужской': ["Creed Aventus","Bvlgari Tygar","Roja Elysium","Emporio Armani Stronger With You","Bleu Eagle Sport","Parfums de Marly Layton","Montblanc Explorer","Bleu de Chanel","Parfums de Marly Althaïr","Blue Seduction"]
}
LV_NAMES = ["Louis Vuitton Imagination","Louis Vuitton L’Immensité","Louis Vuitton Pacific Chill","Louis Vuitton Symphony","Louis Vuitton Afternoon Swim","Louis Vuitton Ombre Nomade","Louis Vuitton Stellar Times","Louis Vuitton Lovers","Louis Vuitton California Dream","Louis Vuitton Météore","Louis Vuitton Myriad","Louis Vuitton Cosmic Cloud","Louis Vuitton City of Stars","Louis Vuitton Les Sables Roses","Louis Vuitton Sun Song","Louis Vuitton Matière Noire","Louis Vuitton Cœur Battant","Louis Vuitton Moon Tale","Louis Vuitton Ink Mark","Louis Vuitton Rain Tea","Louis Vuitton Elves"]
EXTRA = ["Kilian Angels’ Share","Tom Ford Tobacco Vanille","Jean Paul Gaultier Le Male Elixir"]

def status_text(lang, status):
    return {'stock':tr(lang,'status_stock'),'day':tr(lang,'status_day'),'unknown':tr(lang,'status_unknown')}.get(status,tr(lang,'status_unknown'))
def money(value):
    return f"{value:,}".replace(',', ' ') + " сум" if value is not None else "не указана"
def main_keyboard(lang):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=tr(lang,'catalog')),KeyboardButton(text=tr(lang,'search'))],[KeyboardButton(text=tr(lang,'prices')),KeyboardButton(text=tr(lang,'order'))],[KeyboardButton(text=tr(lang,'shops')),KeyboardButton(text=tr(lang,'contact'))]],resize_keyboard=True)
def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🇷🇺 Русский',callback_data='lang:ru'),InlineKeyboardButton(text='🇺🇿 O‘zbekcha',callback_data='lang:uz')]])
def cancel_keyboard(lang):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=tr(lang,'cancel_btn'))]],resize_keyboard=True)
def is_admin(user_id): return user_id in ADMIN_IDS

# Подписи кнопок главного меню на обоих языках: нужны, чтобы посреди заказа нажатие
# «Каталог» не записалось как имя, телефон или адрес клиента.
MENU_LABELS = {TEXT[l][k] for l in TEXT for k in ('catalog','search','prices','order','shops','contact')}

def skip_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,'skip'),callback_data='pphoto:skip')]])

def qty_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(n),callback_data=f'qty:{n}') for n in range(1,6)],
        [InlineKeyboardButton(text=tr(lang,'cancel_btn'),callback_data='qty:cancel')]])

async def safe_edit(msg, text, markup=None):
    """Заменяет сообщение с кнопками. Сообщение с фото нельзя превратить в текстовое,
    поэтому в этом случае отправляем новое и удаляем старое."""
    if getattr(msg,'photo',None):
        await msg.answer(text, reply_markup=markup)
        try: await msg.delete()
        except Exception: pass
        return
    try: await msg.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if 'message is not modified' not in str(e): raise

async def show_card(c, text, markup, photo=None):
    """Карточка парфюма: с фото, если оно есть; если фото не отправилось, показываем текстом."""
    if photo:
        try:
            await c.message.answer_photo(photo, caption=text, reply_markup=markup)
            try: await c.message.delete()
            except Exception: pass
            return
        except TelegramBadRequest:
            logging.warning('Не удалось отправить фото (file_id=%s): показываем карточку без фото', photo)
    await safe_edit(c.message, text, markup)

# ---- заявки: статусы и кнопки для администратора
STATUS_RU = {'new':'🆕 Новая, ждёт обработки','confirmed':'✅ Подтверждена','cancelled':'❌ Отменена'}

def tashkent_time(ts):
    """База хранит UTC; администратору показываем время Ташкента (UTC+5, без перехода на летнее)."""
    try: return (datetime.strptime(ts,'%Y-%m-%d %H:%M:%S')+timedelta(hours=5)).strftime('%d.%m %H:%M')
    except (TypeError,ValueError): return ts or ''

def order_text(o):
    total=money(o['total_price']) if o['total_price'] is not None else 'не рассчитана'
    user=f"@{o['username']}" if o['username'] else str(o['telegram_id'])
    lines=[f"<b>Заявка #{o['id']}</b> · {STATUS_RU.get(o['status'],o['status'])}",
           f"Парфюм: {escape(o['perfume_name'])}",f"Объём: {escape(o['volume'])}",f"Цена за шт.: {money(o['unit_price'])}",
           f"Количество: {o['quantity']}",f"Сумма: {total}",f"Имя: {escape(o['customer_name'])}",f"Телефон: {escape(o['phone'])}",
           f"Доставка: {escape(o['delivery'])}",f"Telegram: {escape(user)}",f"Создана: {tashkent_time(o['created_at'])}"]
    if o['status']!='new' and o['processed_by_name']:
        verb='Подтвердил' if o['status']=='confirmed' else 'Отменил'
        lines.append(f"{verb}: {escape(o['processed_by_name'])} · {tashkent_time(o['processed_at'])}")
    return "\n".join(lines)

def order_keyboard(o):
    if o['status']=='new':
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Подтвердить',callback_data=f"ord:confirm:{o['id']}"),InlineKeyboardButton(text='❌ Отменить',callback_data=f"ord:cancel:{o['id']}")]])
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Вернуть в новые',callback_data=f"ord:reopen:{o['id']}")]])

async def refresh_order_messages(o, pressed=None):
    """Обновляет карточку заявки у всех администраторов, у кого она есть, и в нажатом сообщении."""
    text,kb=order_text(o),order_keyboard(o)
    targets={(m['chat_id'],m['message_id']) for m in await db.get_order_messages(o['id'])}
    if pressed is not None: targets.add((pressed.chat.id,pressed.message_id))
    for chat_id,message_id in targets:
        try: await bot.edit_message_text(text,chat_id=chat_id,message_id=message_id,reply_markup=kb)
        except TelegramBadRequest as e:
            if 'message is not modified' not in str(e): logging.warning('Не удалось обновить заявку #%s в чате %s: %s',o['id'],chat_id,e)
        except Exception: logging.exception('Не удалось обновить заявку #%s в чате %s',o['id'],chat_id)

def rows_keyboard(rows, prefix, back='admin:home'):
    buttons=[[InlineKeyboardButton(text=str(r['name']),callback_data=f'{prefix}:{r["id"]}')] for r in rows]
    buttons.append([InlineKeyboardButton(text='⬅️ Назад',callback_data=back)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_keyboard(lang,new_orders=0):
    labels=[('orders','orders'),('adminsearch','admin_search'),('addperfume','add_perfume'),('addgender','add_gender'),('addbrand','add_brand'),('addcategory','add_category'),('status','set_status'),('prices','set_prices'),('assign','assign_category')]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,k)+(f' ({new_orders})' if k=='orders' and new_orders else ''),callback_data=f'admin:{a}')] for a,k in labels])

async def seed_catalog():
    await db.seed_directories(GENDER_SEEDS, BRAND_SEEDS)
    genders={r['name']:r['id'] for r in await db.list_genders(False)}
    brands={r['name']:r['id'] for r in await db.list_brands(False)}
    brand_patterns=[('Louis Vuitton','Louis Vuitton'),('Tom Ford','Tom Ford'),('Parfums de Marly','Parfums de Marly'),('Dior','Dior'),('Amouage','Amouage'),('Gucci','Gucci'),('Giorgio Armani','Giorgio Armani'),('Emporio Armani','Emporio Armani'),('Yves Saint Laurent','Yves Saint Laurent'),('Chanel','Chanel'),('HFC','HFC'),('Creed','Creed'),('Bvlgari','Bvlgari'),('Roja','Roja'),('Montblanc','Montblanc'),('Jean Paul Gaultier','Jean Paul Gaultier'),('Kilian','Kilian'),('Bleu','Bleu')]
    async def ensure(name, gender=None):
        bname=next((b for pattern,b in brand_patterns if pattern.casefold() in name.casefold()),None)
        bid=brands.get(bname) if bname else None
        cur=await db.conn.execute('INSERT OR IGNORE INTO perfumes(name,gender_id,brand_id,price_10ml,price_50ml,price_100ml,availability_status) VALUES(?,?,?,?,?,?,?)',(name,genders.get(gender),bid,80000,300000,600000,'stock'))
        if cur.rowcount == 0:
            await db.conn.execute("UPDATE perfumes SET gender_id=COALESCE(gender_id,?),brand_id=COALESCE(brand_id,?),price_10ml=COALESCE(price_10ml,80000),price_50ml=COALESCE(price_50ml,300000),price_100ml=COALESCE(price_100ml,600000),availability_status=CASE WHEN availability_status='unknown' THEN 'stock' ELSE availability_status END WHERE name=?",(genders.get(gender),bid,name))
    for gender,names in INITIAL.items():
        for name in names: await ensure(name,gender)
    for name in LV_NAMES: await ensure(name, None)
    for name in EXTRA: await ensure(name,None)
    # Apply the requested temporary defaults once, without overwriting later admin edits.
    cur=await db.conn.execute("SELECT value FROM app_settings WHERE key='catalog_defaults_applied'")
    applied=await cur.fetchone()
    if not applied:
        await db.conn.execute("UPDATE perfumes SET price_10ml=80000,price_50ml=300000,price_100ml=600000,availability_status='stock'")
        await db.conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('catalog_defaults_applied','1')")
    await db.conn.commit()

@dp.message(Command('start'))
async def start(m:Message):
    lang=await db.get_language(m.from_user.id)
    if lang: await m.answer(tr(lang,'welcome'),reply_markup=main_keyboard(lang))
    else: await m.answer(tr('ru','choose_lang'),reply_markup=lang_keyboard())

@dp.callback_query(F.data.startswith('lang:'))
async def choose_lang(c:CallbackQuery):
    lang=c.data.split(':')[1]; await db.set_language(c.from_user.id,lang)
    await c.message.answer(tr(lang,'welcome'),reply_markup=main_keyboard(lang)); await c.answer()

@dp.message(Command('language'))
async def language(m:Message): await m.answer(tr('ru','choose_lang'),reply_markup=lang_keyboard())

@dp.message(Command('cancel'))
async def cancel_any(m:Message,state:FSMContext):
    await state.clear(); lang=await db.get_language(m.from_user.id) or 'ru'
    await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))

@dp.message(Command('admin'))
async def admin(m:Message):
    if not is_admin(m.from_user.id): return await m.answer(tr(await db.get_language(m.from_user.id) or 'ru','admin_only'))
    lang=await db.get_language(m.from_user.id) or 'ru'; await m.answer(tr(lang,'admin_menu'),reply_markup=admin_keyboard(lang,(await db.count_orders())['new']))

@dp.callback_query(F.data=='admin:home')
async def admin_home(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'admin_menu'),reply_markup=admin_keyboard(lang,(await db.count_orders())['new'])); await c.answer()

@dp.callback_query(F.data=='admin:orders')
async def admin_orders(c:CallbackQuery):
    """Сводка по заявкам со счётчиками и кнопками-фильтрами."""
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    n=await db.count_orders()
    text=(f"<b>📥 Заявки</b>\n🆕 Новые (ждут обработки): <b>{n['new']}</b>\n✅ Подтверждённые: {n['confirmed']}\n❌ Отменённые: {n['cancelled']}")
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🆕 Новые ({n['new']})",callback_data='ordlist:new')],
        [InlineKeyboardButton(text=f"✅ Подтверждённые ({n['confirmed']})",callback_data='ordlist:confirmed'),InlineKeyboardButton(text=f"❌ Отменённые ({n['cancelled']})",callback_data='ordlist:cancelled')],
        [InlineKeyboardButton(text='📋 Все последние',callback_data='ordlist:all')],
        [InlineKeyboardButton(text='⬅️ Назад',callback_data='admin:home')]])
    await c.message.answer(text,reply_markup=kb); await c.answer()

@dp.callback_query(F.data.startswith('ordlist:'))
async def admin_orders_list(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    kind=c.data.split(':')[1]; status=None if kind=='all' else kind
    if status is not None and status not in db.ORDER_STATUSES: return await c.answer()
    orders=await db.list_orders(status,limit=15)
    if not orders:
        await c.message.answer('Заявок в этом разделе нет.'); return await c.answer()
    for o in orders: await c.message.answer(order_text(o),reply_markup=order_keyboard(o))
    total=(await db.count_orders()).get(status) if status else sum((await db.count_orders()).values())
    if total and total>len(orders): await c.message.answer(f'Показаны {len(orders)} из {total}.')
    await c.answer()

@dp.callback_query(F.data.startswith('ord:'))
async def admin_order_action(c:CallbackQuery):
    """Подтвердить / отменить заявку после разговора с клиентом, либо вернуть её в новые."""
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    try: _,action,oid=c.data.split(':'); oid=int(oid)
    except ValueError: return await c.answer()
    target={'confirm':'confirmed','cancel':'cancelled','reopen':'new'}.get(action)
    if target is None: return await c.answer()
    o=await db.get_order(oid)
    if o is None: return await c.answer('Заявка не найдена',show_alert=True)
    name=c.from_user.full_name or (f'@{c.from_user.username}' if c.from_user.username else str(c.from_user.id))
    allowed=('confirmed','cancelled') if target=='new' else ('new',)
    changed=await db.set_order_status(oid,target,c.from_user.id,name,allowed)
    o=await db.get_order(oid)
    if changed:
        await c.answer({'confirmed':'Заявка подтверждена','cancelled':'Заявка отменена','new':'Заявка возвращена в новые'}[target])
    else:  # другой администратор уже изменил статус: показываем актуальное состояние
        who=f" ({o['processed_by_name']})" if o['processed_by_name'] else ''
        await c.answer(f"Статус уже изменён: {STATUS_RU.get(o['status'],o['status'])}{who}",show_alert=True)
    await refresh_order_messages(o,c.message)

@dp.callback_query(F.data.in_({'admin:addgender','admin:addbrand','admin:addcategory'}))
async def directory_add_start(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    table={'admin:addgender':'genders','admin:addbrand':'brands','admin:addcategory':'categories'}[c.data]
    await state.update_data(directory_table=table); await state.set_state(DirectoryFlow.name)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'enter_name'),reply_markup=cancel_keyboard(lang)); await c.answer()

@dp.message(DirectoryFlow.name)
async def directory_add_save(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    name=(m.text or '').strip()
    if not name or len(name)>60: return await m.answer('Название должно содержать от 1 до 60 символов.')
    data=await state.get_data()
    try: await db.add_directory_item(data['directory_table'],name)
    except Exception: return await m.answer('Такая запись уже существует. Введите другое название.')
    await state.clear(); await m.answer(tr(lang,'added'),reply_markup=main_keyboard(lang))

@dp.callback_query(F.data=='admin:addperfume')
async def add_perfume_start(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'; await state.set_state(PerfumeFlow.name)
    await c.message.answer(tr(lang,'enter_name'),reply_markup=cancel_keyboard(lang)); await c.answer()

@dp.message(PerfumeFlow.name)
async def perfume_name(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    name=(m.text or '').strip()
    if not name or len(name)>100: return await m.answer('Введите название длиной до 100 символов.')
    await state.update_data(name=name); await state.set_state(PerfumeFlow.gender)
    genders=await db.list_genders()
    await m.answer(tr(lang,'pick_gender'),reply_markup=rows_keyboard(genders,'pgender','admin:home'))

@dp.callback_query(PerfumeFlow.gender,F.data.startswith('pgender:'))
async def perfume_gender(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    await state.update_data(gender_id=int(c.data.split(':')[1])); await state.set_state(PerfumeFlow.brand)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'pick_brand'),reply_markup=rows_keyboard(await db.list_brands(),'pbrand','admin:home')); await c.answer()

@dp.callback_query(PerfumeFlow.brand,F.data.startswith('pbrand:'))
async def perfume_brand(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    await state.update_data(brand_id=int(c.data.split(':')[1])); await state.set_state(PerfumeFlow.p10)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'enter_p10'),reply_markup=cancel_keyboard(lang)); await c.answer()

async def parse_price(m,lang):
    try: value=int((m.text or '').replace(' ','').replace(',',''))
    except ValueError: value=-1
    if value<0: await m.answer(tr(lang,'enter_price_error')); return None
    return value

@dp.message(PerfumeFlow.p10)
async def perfume_p10(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    v=await parse_price(m,lang)
    if v is None:return
    await state.update_data(p10=v); await state.set_state(PerfumeFlow.p50); await m.answer(tr(lang,'enter_p50'))

@dp.message(PerfumeFlow.p50)
async def perfume_p50(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'; v=await parse_price(m,lang)
    if v is None:return
    await state.update_data(p50=v); await state.set_state(PerfumeFlow.p100); await m.answer(tr(lang,'enter_p100'))

@dp.message(PerfumeFlow.p100)
async def perfume_p100(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'; v=await parse_price(m,lang)
    if v is None:return
    await state.update_data(p100=v); await state.set_state(PerfumeFlow.photo)
    await m.answer(tr(lang,'enter_photo'),reply_markup=skip_keyboard(lang))

async def ask_perfume_status(message,lang):
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,'status_stock'),callback_data='pstatus:stock')],[InlineKeyboardButton(text=tr(lang,'status_day'),callback_data='pstatus:day')],[InlineKeyboardButton(text=tr(lang,'status_unknown'),callback_data='pstatus:unknown')]])
    await message.answer(tr(lang,'pick_status'),reply_markup=kb)

@dp.message(PerfumeFlow.photo,F.photo)
async def perfume_photo(m:Message,state:FSMContext):
    """Фото необязательно. Сохраняем Telegram file_id самой крупной версии фото."""
    if not is_admin(m.from_user.id): return
    lang=await db.get_language(m.from_user.id) or 'ru'
    await state.update_data(image_file_id=m.photo[-1].file_id); await state.set_state(PerfumeFlow.status)
    await m.answer(tr(lang,'photo_saved')); await ask_perfume_status(m,lang)

@dp.callback_query(PerfumeFlow.photo,F.data=='pphoto:skip')
async def perfume_photo_skip(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'
    await state.update_data(image_file_id=None); await state.set_state(PerfumeFlow.status)
    await ask_perfume_status(c.message,lang); await c.answer()

@dp.message(PerfumeFlow.photo)
async def perfume_photo_other(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    await m.answer(tr(lang,'photo_wrong'),reply_markup=skip_keyboard(lang))

@dp.callback_query(PerfumeFlow.status,F.data.startswith('pstatus:'))
async def perfume_save(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    d=await state.get_data(); status=c.data.split(':')[1]
    try: await db.add_perfume(d['name'],d['gender_id'],d['brand_id'],d['p10'],d['p50'],d['p100'],status,image_file_id=d.get('image_file_id'))
    except Exception: await c.message.answer('Парфюм с таким названием уже существует.'); await state.clear(); return await c.answer()
    await state.clear(); lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'added'),reply_markup=admin_keyboard(lang)); await c.answer()

@dp.callback_query(F.data=='admin:status')
async def status_start(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'pick_perfume'),reply_markup=rows_keyboard(await db.list_perfumes(),'astatus')); await c.answer()

@dp.callback_query(F.data.startswith('astatus:'))
async def status_choose(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    pid=int(c.data.split(':')[1]); lang=await db.get_language(c.from_user.id) or 'ru'
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,'status_stock'),callback_data=f'save_status:{pid}:stock')],[InlineKeyboardButton(text=tr(lang,'status_day'),callback_data=f'save_status:{pid}:day')],[InlineKeyboardButton(text=tr(lang,'status_unknown'),callback_data=f'save_status:{pid}:unknown')]])
    await c.message.answer(tr(lang,'pick_status'),reply_markup=kb); await c.answer()

@dp.callback_query(F.data.startswith('save_status:'))
async def status_save(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    _,pid,status=c.data.split(':'); await db.set_availability(int(pid),status)
    await c.message.answer(tr(await db.get_language(c.from_user.id) or 'ru','added')); await c.answer()

@dp.callback_query(F.data=='admin:prices')
async def prices_start(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'pick_perfume'),reply_markup=rows_keyboard(await db.list_perfumes(),'aprice')); await c.answer()

@dp.callback_query(F.data.startswith('aprice:'))
async def prices_choose(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    pid=int(c.data.split(':')[1]); await state.update_data(perfume_id=pid); await state.set_state(PriceFlow.p10)
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'enter_p10'),reply_markup=cancel_keyboard(lang)); await c.answer()

@dp.message(PriceFlow.p10)
async def price_edit_10(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'; v=await parse_price(m,lang)
    if v is None:return
    await state.update_data(p10=v); await state.set_state(PriceFlow.p50); await m.answer(tr(lang,'enter_p50'))
@dp.message(PriceFlow.p50)
async def price_edit_50(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'; v=await parse_price(m,lang)
    if v is None:return
    await state.update_data(p50=v); await state.set_state(PriceFlow.p100); await m.answer(tr(lang,'enter_p100'))
@dp.message(PriceFlow.p100)
async def price_edit_100(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'; v=await parse_price(m,lang)
    if v is None:return
    d=await state.get_data(); await db.set_prices(d['perfume_id'],d['p10'],d['p50'],v); await state.clear()
    await m.answer(tr(lang,'admin_price_saved'),reply_markup=admin_keyboard(lang))


@dp.callback_query(F.data=='admin:adminsearch')
async def admin_search_start(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'; await state.update_data(search_mode='admin'); await state.set_state(SearchFlow.query)
    await c.message.edit_text(tr(lang,'search_prompt')); await c.answer()

@dp.callback_query(F.data.startswith('adminperfume:'))
async def admin_perfume_detail(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    parts=c.data.split(':'); pid=int(parts[1]); p=await db.get_perfume(pid); lang=await db.get_language(c.from_user.id) or 'ru'
    if not p: return await c.answer('Not found',show_alert=True)
    body=tr(lang,'admin_perfume',name=escape(p['name']),status=status_text(lang,p['availability_status']),p10=money(p['price_10ml']),p50=money(p['price_50ml']),p100=money(p['price_100ml']))
    photo_row=[InlineKeyboardButton(text=tr(lang,'set_photo'),callback_data=f'aphoto:{pid}')]
    if p['image_file_id']: photo_row.append(InlineKeyboardButton(text=tr(lang,'remove_photo'),callback_data=f'aphotodel:{pid}'))
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang,'set_prices'),callback_data=f'aprice:{pid}')],[InlineKeyboardButton(text=tr(lang,'set_status'),callback_data=f'astatus:{pid}')],photo_row,[InlineKeyboardButton(text=tr(lang,'back_list'),callback_data=f'adminsearch:return:{parts[2] if len(parts)>2 else 0}')]])
    await show_card(c,body,kb,p['image_file_id']); await c.answer()

@dp.callback_query(F.data.startswith('aphoto:'))
async def photo_edit_start(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'
    await state.update_data(photo_perfume_id=int(c.data.split(':')[1])); await state.set_state(PhotoFlow.photo)
    await c.message.answer(tr(lang,'enter_photo_edit'),reply_markup=cancel_keyboard(lang)); await c.answer()

@dp.message(PhotoFlow.photo,F.photo)
async def photo_edit_save(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    lang=await db.get_language(m.from_user.id) or 'ru'; d=await state.get_data()
    await db.set_image(d['photo_perfume_id'],m.photo[-1].file_id); await state.clear()
    await m.answer(tr(lang,'photo_saved'),reply_markup=admin_keyboard(lang))

@dp.message(PhotoFlow.photo)
async def photo_edit_other(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    await m.answer(tr(lang,'photo_wrong'))

@dp.callback_query(F.data.startswith('aphotodel:'))
async def photo_remove(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    await db.set_image(int(c.data.split(':')[1]),None)
    await c.message.answer(tr(await db.get_language(c.from_user.id) or 'ru','photo_removed')); await c.answer()

@dp.callback_query(F.data.startswith('adminsearch:return:'))
async def admin_search_return(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    page=int(c.data.split(':')[2]); d=await state.get_data(); query=d.get('search_query',''); rows=await db.search_perfumes(query); lang=await db.get_language(c.from_user.id) or 'ru'
    await render_search_results(c,lang,rows,page,'admin',query); await c.answer()

@dp.message(SearchFlow.query)
async def search_query(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'):
        await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang) if not is_admin(m.from_user.id) else admin_keyboard(lang))
    data=await state.get_data(); mode=data.get('search_mode','client'); query=(m.text or '').strip()
    await state.update_data(search_query=query,search_mode=mode,search_page=0)
    rows=await db.search_perfumes(query)
    await state.clear(); await state.update_data(search_query=query,search_mode=mode)
    if not rows: return await m.answer(tr(lang,'search_empty'),reply_markup=main_keyboard(lang) if mode!='admin' else admin_keyboard(lang))
    await render_search_results(m,lang,rows,0,mode,query)

async def render_search_results(target,lang,rows,page,mode,query):
    per=5; pages=max(1,(len(rows)+per-1)//per); page=max(0,min(page,pages-1)); subset=rows[page*per:(page+1)*per]
    prefix='adminperfume' if mode=='admin' else 'perfume'
    buttons=[[InlineKeyboardButton(text=(p['name'][:48]),callback_data=(f'adminperfume:{p["id"]}:{page}' if mode=='admin' else f'perfume:{p["id"]}:search:{page}'))] for p in subset]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton(text='⬅️',callback_data=f"searchpage:{mode}:{page-1}"))
    nav.append(InlineKeyboardButton(text=f'{page+1}/{pages}',callback_data='noop'))
    if page<pages-1: nav.append(InlineKeyboardButton(text='➡️',callback_data=f"searchpage:{mode}:{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text=tr(lang,'back'),callback_data='admin:home' if mode=='admin' else 'catalog:home')])
    markup=InlineKeyboardMarkup(inline_keyboard=buttons); text=f"🔎 <b>{escape(query)}</b>\n{tr(lang,'page_count',page=page+1,pages=pages)}"
    if isinstance(target,Message): await target.answer(text,reply_markup=markup)
    else: await safe_edit(target.message,text,markup)

@dp.callback_query(F.data.startswith('searchpage:'))
async def search_page(c:CallbackQuery,state:FSMContext):
    _,mode,page=c.data.split(':'); lang=await db.get_language(c.from_user.id) or 'ru'; d=await state.get_data(); query=d.get('search_query',''); rows=await db.search_perfumes(query)
    await state.update_data(search_query=query,search_mode=mode,browse_kind='search',browse_page=int(page))
    await render_search_results(c,lang,rows,int(page),mode,query); await c.answer()

@dp.callback_query(F.data=='noop')
async def noop(c:CallbackQuery): await c.answer()

@dp.callback_query(F.data=='admin:assign')
async def assign_start(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'; cats=await db.list_categories()
    if not cats: await c.message.answer(tr(lang,'no_categories'))
    else: await c.message.answer(tr(lang,'pick_category'),reply_markup=rows_keyboard(cats,'acat'))
    await c.answer()

@dp.callback_query(F.data.startswith('acat:'))
async def assign_pick_category(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    await state.update_data(category_id=int(c.data.split(':')[1])); lang=await db.get_language(c.from_user.id) or 'ru'
    await c.message.answer(tr(lang,'pick_perfume'),reply_markup=rows_keyboard(await db.list_perfumes(),'assignp')); await c.answer()

@dp.callback_query(F.data.startswith('assignp:'))
async def assign_save(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await c.answer('Admin only',show_alert=True)
    d=await state.get_data(); await db.add_perfume_category(int(c.data.split(':')[1]),d['category_id']); await state.clear()
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.message.answer(tr(lang,'added'),reply_markup=admin_keyboard(lang)); await c.answer()

async def catalog_home_text(target,lang):
    genders=await db.list_genders()
    gender_buttons=[[InlineKeyboardButton(text=f"👤 {g['name']}",callback_data=f"catalog:gender:{g['id']}:0")] for g in genders]
    buttons=gender_buttons+[[InlineKeyboardButton(text=tr(lang,'brands_menu'),callback_data='catalog:directory:brand:0')],
             [InlineKeyboardButton(text=tr(lang,'collections_menu'),callback_data='catalog:directory:category:0')],
             [InlineKeyboardButton(text=tr(lang,'search'),callback_data='catalog:search')]]
    markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(target,Message): await target.answer(tr(lang,'choose'),reply_markup=markup)
    else: await safe_edit(target.message,tr(lang,'choose'),markup)

async def show_catalog(m:Message,lang): await catalog_home_text(m,lang)

async def render_directory(target,lang,kind,page=0):
    rows=await (db.list_brands() if kind=='brand' else db.list_categories()); per=5; pages=max(1,(len(rows)+per-1)//per); page=max(0,min(page,pages-1)); subset=rows[page*per:(page+1)*per]
    buttons=[[InlineKeyboardButton(text=f"{r['name']}",callback_data=f"catalog:{kind}:{r['id']}:0")] for r in subset]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton(text='⬅️',callback_data=f'catalog:directory:{kind}:{page-1}'))
    nav.append(InlineKeyboardButton(text=f'{page+1}/{pages}',callback_data='noop'))
    if page<pages-1: nav.append(InlineKeyboardButton(text='➡️',callback_data=f'catalog:directory:{kind}:{page+1}'))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text=tr(lang,'back'),callback_data='catalog:home')])
    title=tr(lang,'brands_menu' if kind=='brand' else 'collections_menu')
    markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(target,Message): await target.answer(title,reply_markup=markup)
    else: await safe_edit(target.message,title,markup)

async def render_perfume_page(target,lang,kind,item_id,page=0):
    perfumes=await db.list_perfumes(kind,item_id); per=5; pages=max(1,(len(perfumes)+per-1)//per); page=max(0,min(page,pages-1)); subset=perfumes[page*per:(page+1)*per]
    buttons=[[InlineKeyboardButton(text=f"{p['name'][:45]} · {'✅' if p['availability_status']=='stock' else '🕒'}",callback_data=f"perfume:{p['id']}:{kind}:{item_id}:{page}")] for p in subset]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton(text='⬅️',callback_data=f'catalog:page:{kind}:{item_id}:{page-1}'))
    nav.append(InlineKeyboardButton(text=f'{page+1}/{pages}',callback_data='noop'))
    if page<pages-1: nav.append(InlineKeyboardButton(text='➡️',callback_data=f'catalog:page:{kind}:{item_id}:{page+1}'))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text=tr(lang,'back'),callback_data='catalog:back')])
    markup=InlineKeyboardMarkup(inline_keyboard=buttons); title=tr(lang,'choose_perfume') if perfumes else tr(lang,'empty')
    if isinstance(target,Message): await target.answer(title,reply_markup=markup)
    else: await safe_edit(target.message,title,markup)

@dp.callback_query(F.data=='catalog:home')
async def catalog_home(c:CallbackQuery):
    lang=await db.get_language(c.from_user.id) or 'ru'; await catalog_home_text(c,lang); await c.answer()

@dp.callback_query(F.data.startswith('catalog:directory:'))
async def catalog_directory(c:CallbackQuery):
    _,_,kind,page=c.data.split(':'); lang=await db.get_language(c.from_user.id) or 'ru'; await render_directory(c,lang,kind,int(page)); await c.answer()

@dp.callback_query(F.data.startswith('catalog:page:'))
async def catalog_page(c:CallbackQuery):
    _,_,kind,item,page=c.data.split(':'); lang=await db.get_language(c.from_user.id) or 'ru'; await render_perfume_page(c,lang,kind,int(item),int(page)); await c.answer()

@dp.callback_query(F.data.startswith('catalog:gender:') | F.data.startswith('catalog:brand:') | F.data.startswith('catalog:category:'))
async def catalog_list(c:CallbackQuery):
    parts=c.data.split(':'); kind=parts[1]; item=int(parts[2]); page=int(parts[3]) if len(parts)>3 else 0
    lang=await db.get_language(c.from_user.id) or 'ru'; await render_perfume_page(c,lang,kind,item,page); await c.answer()

@dp.callback_query(F.data=='catalog:back')
async def catalog_back(c:CallbackQuery):
    lang=await db.get_language(c.from_user.id) or 'ru'; await catalog_home_text(c,lang); await c.answer()

@dp.callback_query(F.data=='catalog:search')
async def catalog_search_start(c:CallbackQuery,state:FSMContext):
    lang=await db.get_language(c.from_user.id) or 'ru'; await state.update_data(search_mode='client'); await state.set_state(SearchFlow.query)
    await c.message.edit_text(tr(lang,'search_prompt')); await c.answer()

@dp.callback_query(F.data.startswith('perfume:'))
async def perfume_detail(c:CallbackQuery,state:FSMContext):
    parts=c.data.split(':'); pid=int(parts[1]); p=await db.get_perfume(pid)
    if not p or not p['is_active']: return await c.answer('Not found',show_alert=True)
    lang=await db.get_language(c.from_user.id) or 'ru'
    price_text=tr(lang,'price_line',p10=money(p['price_10ml']),p50=money(p['price_50ml']),p100=money(p['price_100ml']))
    detail=f"<b>{escape(p['name'])}</b>\n{escape(p['brand_name'] or '')} · {escape(p['gender_name'] or '')}\n{status_text(lang,p['availability_status'])}\n\n{price_text}"
    if len(parts)>2:
        await state.update_data(browse_kind=parts[2],browse_item=int(parts[3]) if len(parts)>3 and parts[3].isdigit() else 0,browse_page=int(parts[4]) if len(parts)>4 and parts[4].isdigit() else 0)
    else:
        await state.update_data(browse_kind='home',browse_item=0,browse_page=0)
    await state.update_data(perfume_id=pid,perfume_name=p['name'])
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='10 мл',callback_data='volume:10'),InlineKeyboardButton(text='50 мл',callback_data='volume:50'),InlineKeyboardButton(text='100 мл',callback_data='volume:100')]])
    kb.inline_keyboard.append([InlineKeyboardButton(text=tr(lang,'back'),callback_data='catalog:return')])
    await show_card(c,detail+'\n\n'+tr(lang,'volume'),kb,p['image_file_id']); await c.answer()

@dp.callback_query(F.data=='catalog:return')
async def catalog_return(c:CallbackQuery,state:FSMContext):
    lang=await db.get_language(c.from_user.id) or 'ru'; d=await state.get_data(); kind=d.get('browse_kind','home')
    if kind=='home': await catalog_home_text(c,lang)
    elif kind=='search':
        query=d.get('search_query',''); rows=await db.search_perfumes(query); await render_search_results(c,lang,rows,int(d.get('browse_page',0)),'client',query)
    else: await render_perfume_page(c,lang,kind,int(d.get('browse_item',0)),int(d.get('browse_page',0)))
    await c.answer()

@dp.callback_query(F.data.startswith('volume:'))
async def volume(c:CallbackQuery,state:FSMContext):
    vol=c.data.split(':')[1]; d=await state.get_data(); p=await db.get_perfume(d.get('perfume_id'))
    col={'10':'price_10ml','50':'price_50ml','100':'price_100ml'}[vol]; price=p[col] if p else None
    lang=await db.get_language(c.from_user.id) or 'ru'
    if price is None or price<=0: return await c.answer(tr(lang,'not_priced'),show_alert=True)
    await state.update_data(volume=vol,unit_price=price); await state.set_state(OrderFlow.quantity)
    await c.message.answer(tr(lang,'qty'),reply_markup=qty_keyboard(lang)); await c.answer()

@dp.message(OrderFlow.quantity)
async def order_qty(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    if await leave_flow_if_menu(m,state): return
    try: qty=int(m.text)
    except (ValueError,TypeError): qty=0
    if qty<1 or qty>1000:return await m.answer(tr(lang,'invalid_qty'))
    await state.update_data(quantity=qty); await state.set_state(OrderFlow.name); await m.answer(tr(lang,'name'),reply_markup=cancel_keyboard(lang))

@dp.callback_query(OrderFlow.quantity,F.data.startswith('qty:'))
async def order_qty_button(c:CallbackQuery,state:FSMContext):
    """Количество кнопками 1–5 (больше пяти клиент может написать числом)."""
    lang=await db.get_language(c.from_user.id) or 'ru'; value=c.data.split(':')[1]
    if value=='cancel':
        await state.clear()
        try: await c.message.delete()
        except Exception: pass
        await c.message.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang)); return await c.answer()
    try: qty=int(value)
    except ValueError: return await c.answer()
    if not 1<=qty<=1000: return await c.answer()
    await state.update_data(quantity=qty); await state.set_state(OrderFlow.name)
    try: await c.message.edit_text(tr(lang,'qty_chosen',qty=qty))   # убираем кнопки, чтобы их нельзя было нажать повторно
    except TelegramBadRequest: pass
    await c.message.answer(tr(lang,'name'),reply_markup=cancel_keyboard(lang)); await c.answer()

@dp.callback_query(F.data.startswith('qty:'))
async def order_qty_stale(c:CallbackQuery):
    """Нажатие на старые кнопки количества, когда заказ уже не оформляется."""
    lang=await db.get_language(c.from_user.id) or 'ru'; await c.answer(tr(lang,'stale'),show_alert=True)

async def leave_flow_if_menu(m,state):
    """Если клиент посреди заказа нажал кнопку главного меню, выходим из заказа в этот раздел,
    а не записываем подпись кнопки как количество, имя, телефон или адрес."""
    if (m.text or '').strip() in MENU_LABELS:
        await state.clear(); await main_menu_text(m,state); return True
    return False

@dp.message(OrderFlow.name)
async def order_name(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    if await leave_flow_if_menu(m,state): return
    name=(m.text or '').strip()
    if not name: return await m.answer(tr(lang,'name'))
    await state.update_data(customer_name=name); await state.set_state(OrderFlow.phone)
    await m.answer(tr(lang,'phone'),reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=tr(lang,'share_phone'),request_contact=True)],[KeyboardButton(text=tr(lang,'cancel_btn'))]],resize_keyboard=True))

@dp.message(OrderFlow.phone)
async def order_phone(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    if await leave_flow_if_menu(m,state): return
    phone=m.contact.phone_number if m.contact else (m.text or '').strip()
    await state.update_data(phone=phone); await state.set_state(OrderFlow.delivery)
    await m.answer(tr(lang,'delivery'),reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=tr(lang,'share_location'),request_location=True)],[KeyboardButton(text=tr(lang,'cancel_btn'))]],resize_keyboard=True))

@dp.message(OrderFlow.delivery)
async def order_delivery(m:Message,state:FSMContext):
    lang=await db.get_language(m.from_user.id) or 'ru'
    if m.text==tr(lang,'cancel_btn'): await state.clear(); return await m.answer(tr(lang,'cancel'),reply_markup=main_keyboard(lang))
    if await leave_flow_if_menu(m,state): return
    delivery=f"Геолокация: https://maps.google.com/?q={m.location.latitude},{m.location.longitude}" if m.location else (m.text or '').strip()
    d=await state.get_data(); total=d['unit_price']*d['quantity']
    order_id=await db.create_order(telegram_id=m.from_user.id,username=m.from_user.username,language=lang,perfume_id=d['perfume_id'],perfume_name=d['perfume_name'],volume=f"{d['volume']} мл",unit_price=d['unit_price'],total_price=total,quantity=d['quantity'],customer_name=d['customer_name'],phone=d['phone'],delivery=delivery)
    order=await db.get_order(order_id)
    for aid in ADMIN_IDS:
        try:
            sent=await bot.send_message(aid,order_text(order),reply_markup=order_keyboard(order))
            await db.add_order_message(order_id,aid,sent.message_id)
        except Exception: logging.exception('Admin notification failed: %s',aid)
    await state.clear(); await m.answer(tr(lang,'order_done'),reply_markup=main_keyboard(lang))


# Reply-keyboard menu handlers. Without these, tapping the main menu buttons
# produces "Update is not handled" because reply buttons send plain text.
@dp.message(F.text)
async def main_menu_text(m: Message, state: FSMContext):
    lang = await db.get_language(m.from_user.id) or 'ru'
    text = (m.text or '').strip()

    if text == tr(lang, 'catalog'):
        await state.clear()
        await catalog_home_text(m, lang)
    elif text == tr(lang, 'search'):
        await state.clear()
        await state.update_data(search_mode='client')
        await state.set_state(SearchFlow.query)
        await m.answer(tr(lang, 'search_prompt'), reply_markup=cancel_keyboard(lang))
    elif text == tr(lang, 'prices'):
        await m.answer(tr(lang, 'prices_info'), reply_markup=main_keyboard(lang))
    elif text == tr(lang, 'order'):
        await state.clear()
        await m.answer('Сначала выберите аромат в каталоге, затем нажмите нужный объём.', reply_markup=main_keyboard(lang))
        await catalog_home_text(m, lang)
    elif text == tr(lang, 'shops'):
        await m.answer(tr(lang, 'shops_info'), reply_markup=main_keyboard(lang))
    elif text == tr(lang, 'contact'):
        await m.answer('Чтобы связаться с администратором, оставьте заявку через каталог — администратор получит её автоматически.', reply_markup=main_keyboard(lang))


async def main():
    await db.connect(); await seed_catalog()
    try: await dp.start_polling(bot)
    finally: await db.close(); await bot.session.close()

if __name__=='__main__': asyncio.run(main())
