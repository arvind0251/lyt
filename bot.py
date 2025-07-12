"""
MultiGame Telegram Bot (Aiogram 3.4)
-----------------------------------
Games:
 1. 🎯 Throw Dot          (dice)
 2. 🎲 Classic Dice       (dice)
 3. ⚽ Football Goal      (dice)
 4. 🏀 Basketball Shot    (dice)      ← NEW
 5. 🎳 Bowling Strike     (dice)      ← NEW
 6. 🎰 Slot Machine       (dice)      ← NEW
 7. 🪙 Coin Flip          (text random)
 8. ✂️ Rock‑Paper‑Scissors (inline)
 9. 🔢 Guess the Number   (inline)
10. ❓ Quick Trivia        (text)

Set env var BOT_TOKEN before running.
"""

import asyncio
import logging
import os
import random
from enum import Enum, auto

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

API_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
if API_TOKEN.startswith("YOUR_"):
    raise RuntimeError("👉  BOT_TOKEN environment variable डाल दीजिये!")

# ───────── basic setup ─────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(API_TOKEN, parse_mode="HTML")
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ───────── per‑user session ─────────
class ActiveGame(Enum):
    NONE   = auto()
    GUESS  = auto()
    RPS    = auto()
    TRIVIA = auto()

class Session:
    def __init__(self):
        self.game           = ActiveGame.NONE
        self.target_number  = None      # Guess‑the‑number
        self.trivia_answer  = None      # Trivia

_sessions: dict[int, Session] = {}
def get_session(uid: int) -> Session:
    return _sessions.setdefault(uid, Session())

# ───────── trivia Q/A ─────────
TRIVIA_BANK = [
    ("What is the chemical symbol for water?", "h2o"),
    ("Who wrote the epic Ramayana?", "valmiki"),
    ("Fastest land animal? (one word)", "cheetah"),
    ("Capital city of Japan?", "tokyo"),
]

# ───────── keyboards ─────────
def main_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🎯 Throw Dot",  callback_data="dot"),
            InlineKeyboardButton("🎲 Roll Dice",  callback_data="dice"),
        ],
        [
            InlineKeyboardButton("⚽ Football",    callback_data="foot"),
            InlineKeyboardButton("🏀 Basketball",  callback_data="bask"),  # NEW
        ],
        [
            InlineKeyboardButton("🎳 Bowling",     callback_data="bowl"),  # NEW
            InlineKeyboardButton("🎰 Slot",        callback_data="slot"),  # NEW
        ],
        [
            InlineKeyboardButton("🪙 Coin Flip",   callback_data="coin"),
            InlineKeyboardButton("✂️ R / P / S",  callback_data="game_rps"),
        ],
        [
            InlineKeyboardButton("🔢 Guess Number", callback_data="game_guess"),
            InlineKeyboardButton("❓ Trivia",       callback_data="game_trivia"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def guess_kb() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1, 11)]
    grid = [buttons[:5], buttons[5:], [InlineKeyboardButton("❌ Exit", callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=grid)

def rps_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("🪨 Rock",     callback_data="rps_rock"),
            InlineKeyboardButton("📄 Paper",    callback_data="rps_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors"),
        ],
        [InlineKeyboardButton("❌ Exit", callback_data="cancel")],
    ])

# ───────── handlers ─────────
@router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "<b>Welcome to MultiGame Bot!</b>\nगेम चुनें 👇",
        reply_markup=main_menu_kb(),
    )

@router.message(Command("menu"))
async def menu_cmd(msg: Message):
    await start_cmd(msg)

# ----- instant dice games -----
@router.callback_query(F.data.in_({"dot","dice","foot","bask","bowl","slot"}))
async def instant_dice(cb: CallbackQuery):
    emoji = {
        "dot":"🎯", "dice":"🎲", "foot":"⚽",
        "bask":"🏀", "bowl":"🎳", "slot":"🎰",
    }[cb.data]
    await cb.message.answer_dice(emoji)
    await cb.answer()

# ----- coin flip -----
@router.callback_query(F.data=="coin")
async def coin_flip(cb: CallbackQuery):
    toss = random.choice(["🪙 <b>Heads</b>", "🪙 <b>Tails</b>"])
    await cb.message.answer(f"Flipping…\n{toss}")
    await cb.answer()

# ----- guess number -----
@router.callback_query(F.data=="game_guess")
async def start_guess(cb: CallbackQuery):
    s = get_session(cb.from_user.id)
    s.game, s.target_number = ActiveGame.GUESS, random.randint(1, 10)
    await cb.message.answer("I'm thinking of a number 1‑10. Guess!", reply_markup=guess_kb())
    await cb.answer()

@router.callback_query(lambda c: c.data.startswith("guess_"))
async def handle_guess(cb: CallbackQuery):
    s = get_session(cb.from_user.id)
    if s.game != ActiveGame.GUESS:
        await cb.answer("Not playing Guess Number.", show_alert=True); return
    g = int(cb.data.split("_")[1])
    if g == s.target_number:
        await cb.message.answer(f"🎉 Correct! It was {g}.", reply_markup=main_menu_kb())
        s.game = ActiveGame.NONE
    elif g < s.target_number:
        await cb.answer("⬆️ Higher!", show_alert=False)
    else:
        await cb.answer("⬇️ Lower!", show_alert=False)

# ----- rock‑paper‑scissors -----
@router.callback_query(F.data=="game_rps")
async def start_rps(cb: CallbackQuery):
    get_session(cb.from_user.id).game = ActiveGame.RPS
    await cb.message.answer("Choose one:", reply_markup=rps_kb())
    await cb.answer()

@router.callback_query(lambda c: c.data.startswith("rps_"))
async def play_rps(cb: CallbackQuery):
    s = get_session(cb.from_user.id)
    if s.game != ActiveGame.RPS:
        await cb.answer("Not playing RPS.", show_alert=True); return
    player = cb.data.split("_")[1]
    bot = random.choice(["rock","paper","scissors"])
    wins = {"rock":"scissors","paper":"rock","scissors":"paper"}
    result = "🤝 Draw." if player == bot else ("🏆 You win!" if wins[player]==bot else "💔 I win!")
    await cb.message.answer(f"You: <b>{player.title()}</b>\nMe: <b>{bot.title()}</b>\n{result}", reply_markup=rps_kb())
    await cb.answer()

# ----- trivia -----
@router.callback_query(F.data=="game_trivia")
async def start_trivia(cb: CallbackQuery):
    q, ans = random.choice(TRIVIA_BANK)
    s = get_session(cb.from_user.id)
    s.game, s.trivia_answer = ActiveGame.TRIVIA, ans.lower()
    await cb.message.answer(f"❓ <b>Trivia</b>\n{q}\n\n(Type your answer)")
    await cb.answer()

# ----- cancel button -----
@router.callback_query(F.data=="cancel")
async def cancel(cb: CallbackQuery):
    get_session(cb.from_user.id).__init__()      # reset session
    await cb.message.answer("Exited. Select another game 👇", reply_markup=main_menu_kb())
    await cb.answer("Cancelled")

# ----- text messages (for trivia) -----
@router.message()
async def on_text(msg: Message):
    s = get_session(msg.from_user.id)
    if s.game == ActiveGame.TRIVIA and s.trivia_answer:
        if msg.text.lower().strip() == s.trivia_answer:
            await msg.reply("✅ Correct! 🎉", reply_markup=main_menu_kb())
        else:
            await msg.reply(f"❌ Nope — it was {s.trivia_answer.title()}.", reply_markup=main_menu_kb())
        s.__init__()   # reset session

# ───────── main ─────────
async def main():
    logging.info("Starting MultiGame Bot…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
