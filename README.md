# ai_bot
This is a Telegram bot built using the Aiogram 3.x framework , designed to provide users with access to AI-powered services through a subscription-based model.

# Stratton AI Telegram Bot


 A Telegram bot that offers AI-powered services through subscription plans using Stripe for payments and Gemini API for AI responses.


## 📌 Features


- **Subscription Plans**: Choose from Basic, Standard, or Premium plans.

- **Stripe Integration**: Secure payment processing via Stripe Checkout.
- 
- **Voice Message Support**: Converts voice messages to text using Google Web Speech API.
- 
- **AI Responses**: Uses Google Gemini API to generate intelligent answers.
- 
- **User-Friendly Interface**: Inline buttons for easy navigation and interaction.
  

---

## 🔧 Requirements


Make sure you have the following installed before running the bot:


### Python Packages

Install dependencies using pip:


```bash
pip install aiogram stripe speechrecognition pydub requests python-dotenv
```

> Optional (for better voice recognition):
```bash
pip install google-cloud-speech  # For Google Cloud Speech-to-Text
```

### System Requirements
- **FFmpeg**: Required by `pydub` for audio conversion (OGG to WAV).
    - Windows: Add FFmpeg to your PATH.
    - Linux/macOS: Install via package manager (`apt install ffmpeg`, `brew install ffmpeg`)

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/stratton-ai-bot.git
cd stratton-ai-bot
```

### 2. Create `.env` File

Create a `.env` file in the root folder with the following content:

```
BOT_TOKEN=your_telegram_bot_token_here
STRIPE_API_KEY=your_stripe_secret_key_here
GEMINI_API_KEY=your_google_gemini_api_key_here
```

Replace the values with your actual tokens and keys.

> If you're using Google Cloud Speech-to-Text:
```
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

## 📁 Project Structure
.
├── main.py              # Main bot logic
├── .env                 # Environment variables (API keys, tokens)
├── README.md            # This file
└── requirements.txt     # List of required Python packages

---

##  Credits

- Built using [Aiogram](https://docs.aiogram.dev/) — modern Telegram Bot framework for Python.
- Powered by [Google Gemini API](https://ai.google/devsite/gemini-api/docs/get-started) for AI responses.
- Payments powered by [Stripe](https://stripe.com/docs/payments/checkout).

