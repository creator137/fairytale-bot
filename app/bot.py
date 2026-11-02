import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp
from .core import s
bot=Bot(s.bot_token); dp=Dispatcher()
@dp.message(CommandStart())
async def start(m: Message):
    await bot.set_chat_menu_button(chat_id=m.chat.id, menu_button=MenuButtonWebApp(text='Моя сказка',web_app=WebAppInfo(url=s.public_url)))
    await m.answer('Сказка с тобой ✨\nДемонстрация: 10 страниц с шаблонным текстом и иллюстрациями. Бесплатно, без ИИ-генерации. Фото хранится приватно; заказ можно удалить.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Создать сказку',web_app=WebAppInfo(url=s.public_url))]]))
@dp.message(Command('terms','support','paysupport'))
async def support(m: Message): await m.answer('Это демонстрационная версия. Оплата отключена. Фото не отправляется ИИ. Удалить данные можно в «Моих сказках».')
async def main():
    if not s.public_url: raise RuntimeError('Set PUBLIC_URL')
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text='Моя сказка',web_app=WebAppInfo(url=s.public_url)))
    await dp.start_polling(bot)
if __name__=='__main__': asyncio.run(main())
