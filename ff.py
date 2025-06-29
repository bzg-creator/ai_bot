import logging
from typing import Dict
import stripe
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import io
import speech_recognition as sr
from pydub import AudioSegment
import requests


from dotenv import load_dotenv
import os


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")

# Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Subscription plans
PLANS = {
    "basic": {
        "name": "Basic Plan",
        "description": "1000 API calls/month",
        "price": 500,
        "api_key": "sk_test_basic_1234567890",
    },
    "standard": {
        "name": "Standard Plan",
        "description": "5000 API calls/month",
        "price": 2000,
        "api_key": "sk_test_standard_1234567890",
    },
    "premium": {
        "name": "Premium Plan",
        "description": "Unlimited API calls",
        "price": 5000,
        "api_key": "sk_test_premium_1234567890",
    },
}


user_subscriptions: Dict[int, dict] = {}


class SubscriptionState(StatesGroup):
    choosing_plan = State()
    processing_payment = State()



bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_main_menu_keyboard():

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Главная", callback_data="main_menu"),
    )
    builder.row(
        InlineKeyboardButton(text="Моя подписка", callback_data="my_subscription"),
    )
    builder.row(
        InlineKeyboardButton(text="Подробная информация", callback_data="detailed_info"),
    )
    builder.row(
        InlineKeyboardButton(text="Оформить тариф", callback_data="subscribe"),
    )
    return builder.as_markup()


def get_plans_keyboard():

    builder = InlineKeyboardBuilder()
    for plan_id, plan in PLANS.items():
        builder.add(InlineKeyboardButton(
            text=f"{plan['name']} - ${plan['price'] / 100:.2f}",
            callback_data=f"plan_{plan_id}"
        ))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_plan_details_keyboard(plan_id: str):

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="💳 Оплатить сейчас",
        callback_data=f"purchase_{plan_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 Вернуться к планам",
        callback_data="view_plans"
    ))
    builder.adjust(1)
    return builder.as_markup()


async def create_stripe_payment_link(plan_id: str, user_id: int) -> str:
    plan = PLANS[plan_id]
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': plan['name'],
                        'description': plan['description'],
                    },
                    'unit_amount': plan['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://t.me/stratton_openAI_bot?start=success_{plan_id}_{user_id}',
            cancel_url=f'https://t.me/stratton_openAI_bot?start=cancel',
            metadata={
                'plan_id': plan_id,
                'telegram_user_id': user_id
            }
        )
        return session.url
    except Exception as e:
        logger.error(f"Error creating Stripe session: {e}")
        return None


async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    subscription = user_subscriptions.get(user_id)
    if not subscription or subscription["status"] != "active":
        await message.answer(
            "❌ Для использования голосового помощника требуется активная подписка.",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    voice = await bot.download(message.voice.file_id)
    audio_data = io.BytesIO(voice.getvalue())
    try:
        audio = AudioSegment.from_ogg(audio_data)
        wav_data = io.BytesIO()
        audio.export(wav_data, format="wav")
        wav_data.seek(0)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_data) as source:
            audio_text = recognizer.listen(source)
            text = recognizer.recognize_google(audio_text, language="ru-RU")
        await message.answer(f"Вы сказали: {text}\nПравильно вас понял?")
        gemini_response = ask_gemini(text)
        await message.answer(f"Ответ: {gemini_response}")
    except sr.UnknownValueError:
        await message.answer("Не удалось распознать речь. Пожалуйста, повторите.")
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await message.answer("Произошла ошибка при обработке голосового сообщения.")


def ask_gemini(prompt: str) -> str:

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text",
                                                                                                       "Извините, не удалось получить ответ.")
    else:
        logger.error(f"Gemini API error: {response.status_code}, {response.text}")
        return "Произошла ошибка при получении ответа от ИИ."



@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    if len(message.text.split()) > 1:
        args = message.text.split()[1]
        if args.startswith('success_'):
            _, plan_id, user_id = args.split('_')
            user_id = int(user_id)
            if user_id == message.from_user.id:
                plan = PLANS[plan_id]
                user_subscriptions[user_id] = {
                    "plan": plan_id,
                    "api_key": plan['api_key'],
                    "status": "active",
                }
                await message.answer(
                    f"🎉 <b>Оплата прошла успешно!</b>\n"
                    f"Вы подписались на <b>{plan['name']}</b>.\n"
                    f"Ваш AI API ключ:\n<code>{plan['api_key']}</code>",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML",
                )
                return
        elif args == 'cancel':
            await message.answer(
                "Оплата была отменена.",
                reply_markup=get_main_menu_keyboard(),
            )
            return


    await message.answer(
        "👋 <b>Добро пожаловать в Stratton AI!</b>\n"
        "Я ваш персональный помощник для работы с искусственным интеллектом. 🤖✨\n"
        "Чтобы начать, выберите один из доступных планов подписки или узнайте больше о наших услугах.\n"
        "Выберите действие ниже:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 <b>Добро пожаловать в Stratton AI!</b>\n"
        "Я ваш персональный помощник для работы с искусственным интеллектом. 🤖✨\n"
        "Чтобы начать, выберите один из доступных планов подписки или узнайте больше о наших услугах.\n"
        "Выберите действие ниже:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "my_subscription")
async def my_subscription(callback: types.CallbackQuery):

    user_id = callback.from_user.id
    subscription = user_subscriptions.get(user_id)
    if subscription:
        plan_id = subscription["plan"]
        plan = PLANS[plan_id]
        text = (
            f"👤 <b>Ваша подписка:</b>\n"
            f"📋 План: <b>{plan['name']}</b>\n"
            f"🔑 API Key: <code>{subscription['api_key']}</code>\n"
            f"🔄 Статус: <b>{subscription['status'].capitalize()}</b>"
        )
    else:
        text = (
            "❌ <b>У вас нет активной подписки.</b>\n"
            "Выберите план, чтобы получить доступ к нашим услугам."
        )
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "detailed_info")
async def detailed_info(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📚 <b>Подробная информация</b>\n"
        "🏪 Компания <a href='https://stratton.kz/'>Stratton.kz</a>\n"
        "Мы автоматизируем бизнес-процессы посредством роботизации, внедрения чат-ботов и функциональных сайтов.\n"
        "ℹ️ Подробнее о компании <a href='https://stratton.taplink.ws/p/o-kompanii/'>тут</a>.\n\n"
        "📞 <b>Контакты</b>\n"
        "Для связи с нами пишите ✍️\n"
        "@bzg00\n\n"
        "🤖 <b>AI справочник</b>\n"
        "<b>Доступные AI модели:</b>\n"
        "1️⃣ <b>GPT-4 Turbo</b>\n"
        "- Самый продвинутый AI для сложных задач.\n"
        "- Генерация текста, анализ данных, ответы на вопросы.\n"
        "- Доступен в планах: Стандартный и Премиум.\n"
        "2️⃣ <b>Claude 3</b>\n"
        "- Идеально подходит для анализа больших объемов данных.\n"
        "- Ответы на сложные запросы и структурирование информации.\n"
        "- Доступен в планах: Стандартный и Премиум.\n"
        "3️⃣ <b>Stable Diffusion</b>\n"
        "- Генерация изображений на основе текстовых описаний.\n"
        "- Создание уникального визуального контента.\n"
        "- Доступен в плане: Премиум.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@dp.callback_query(F.data == "subscribe")
async def subscribe(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🚀 <b>Выберите план для подписки:</b>",
        reply_markup=get_plans_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("plan_"))
async def plan_details(callback: types.CallbackQuery):
    plan_id = callback.data.split("_")[1]
    plan = PLANS[plan_id]
    await callback.message.edit_text(
        f"💡 <b>{plan['name']}</b>\n"
        f"{plan['description']}\n"
        f"💵 Цена: <b>${plan['price'] / 100:.2f}</b> в месяц\n"
        "Нажмите 'Оплатить сейчас' для доступа:",
        reply_markup=get_plan_details_keyboard(plan_id),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("purchase_"))
async def start_payment(callback: types.CallbackQuery, state: FSMContext):
    plan_id = callback.data.split("_")[1]
    plan = PLANS[plan_id]
    user_id = callback.from_user.id
    payment_url = await create_stripe_payment_link(plan_id, user_id)
    if not payment_url:
        await callback.answer("Ошибка при создании оплаты. Пожалуйста, попробуйте позже.", show_alert=True)
        return
    await callback.message.edit_text(
        f"💳 <b>Оплата {plan['name']}</b>\n"
        f"Сумма: <b>${plan['price'] / 100:.2f}</b>\n"
        "Нажмите для оплаты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить через Stripe", url=payment_url)],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"plan_{plan_id}")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "view_plans")
async def view_plans_callback(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "🚀 <b>Выберите план для подписки:</b>",
        reply_markup=get_plans_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    subscription = user_subscriptions.get(user_id)

    if not subscription or subscription["status"] != "active":
        await message.answer("❌ Для использования голосового помощника требуется активная подписка.")
        return

    voice = await bot.download(message.voice.file_id)
    audio_data = io.BytesIO(voice.getvalue())

    try:
        sound = AudioSegment.from_file(audio_data, format="ogg")
        wav_data = io.BytesIO()
        sound.export(wav_data, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_data) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="ru-RU")

        gemini_response = ask_gemini(text)
        await message.answer(f"🤖 Ответ ИИ: {gemini_response}")
    except Exception as e:
        await message.answer("⚠️ Ошибка при обработке голоса.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
