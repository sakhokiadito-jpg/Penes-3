import json
import logging

from telegram import (
    Update,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN,
    OWNER_ID,
    ADMIN_IDS,
    FREE_USERNAMES,
    REPORT_EXPIRE_HOURS,
    STARS_20,
    STARS_50,
    STARS_100,
)

from db import (
    init_db,
    ensure_user,
    get_user,
    charge_search,
    grant_credits,
    set_credits,
    save_payment,
    create_report,
    group_enabled,
    enable_group,
)

from engine import search


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(
    "osint-core"
)


def is_owner(
    user_id: int,
) -> bool:
    return user_id == OWNER_ID


def is_admin(
    user_id: int,
) -> bool:
    return user_id in ADMIN_IDS


def is_free_user(
    username: str | None,
) -> bool:
    if not username:
        return False

    return (
        username.lower().lstrip("@")
        in {
            x.lower()
            for x in FREE_USERNAMES
        }
    )


def prepare_user(
    update: Update,
):
    user = update.effective_user

    ensure_user(
        tg_id=user.id,
        username=user.username,
        is_owner=is_owner(user.id),
        is_admin=is_admin(user.id),
        free_access=is_free_user(
            user.username
        ),
    )

    return user


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = prepare_user(update)

    row = get_user(
        user.id
    )

    credits = (
        row["credits"]
        if row
        else 0
    )

    await update.message.reply_text(
        "🔎 OSINT CORE\n\n"
        "Публичный OSINT-агрегатор.\n\n"
        f"💰 Кредиты: {credits}\n\n"
        "Выберите действие:\n\n"
        "🔍 Просто отправьте запрос сообщением.\n"
        "/buy — купить кредиты\n"
        "/profile — профиль\n"
        "/help — помощь"
    )


async def profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = prepare_user(update)

    row = get_user(
        user.id
    )

    credits = (
        row["credits"]
        if row
        else 0
    )

    unlimited = bool(
        row
        and (
            row["is_owner"]
            or row["is_admin"]
            or row["free_access"]
        )
    )

    access = (
        "♾️ Безлимит"
        if unlimited
        else "Обычный"
    )

    await update.message.reply_text(
        "👤 Профиль\n\n"
        f"ID: {user.id}\n"
        f"Username: @{user.username or 'нет'}\n"
        f"💰 Кредиты: {credits}\n"
        f"🔐 Доступ: {access}"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "ℹ️ OSINT CORE\n\n"
        "Можно отправить:\n"
        "• ФИО\n"
        "• username\n"
        "• email\n"
        "• домен\n"
        "• IP\n"
        "• публичный идентификатор\n\n"
        "Поиск выполняется только "
        "по разрешённым публичным данным."
    )


async def buy(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    prepare_user(update)

    await update.message.reply_text(
        "💳 Пополнение\n\n"
        f"⭐ 20 кредитов — {STARS_20} Stars\n"
        f"⭐ 50 кредитов — {STARS_50} Stars\n"
        f"⭐ 100 кредитов — {STARS_100} Stars\n\n"
        "Для покупки:\n"
        "/buy20\n"
        "/buy50\n"
        "/buy100"
    )


async def send_invoice(
    update: Update,
    credits: int,
    stars: int,
):
    await update.message.reply_invoice(
        title=f"{credits} кредитов",
        description=(
            f"Пополнение баланса OSINT Core "
            f"на {credits} кредитов."
        ),
        payload=f"credits:{credits}",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=f"{credits} кредитов",
                amount=stars,
            )
        ],
    )


async def buy20(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    prepare_user(update)
    await send_invoice(
        update,
        20,
        STARS_20,
    )


async def buy50(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    prepare_user(update)
    await send_invoice(
        update,
        50,
        STARS_50,
    )


async def buy100(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    prepare_user(update)
    await send_invoice(
        update,
        100,
        STARS_100,
    )


async def precheckout(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.pre_checkout_query

    await query.answer(
        ok=True
    )


async def successful_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = prepare_user(update)

    payment = (
        update.message.successful_payment
    )

    payload = payment.invoice_payload

    if not payload.startswith(
        "credits:"
    ):
        return

    credits = int(
        payload.split(
            ":",
            1
        )[1]
    )

    grant_credits(
        user.id,
        credits,
    )

    save_payment(
        tg_id=user.id,
        payload=payload,
        stars=payment.total_amount,
        charge_id=(
            payment.telegram_payment_charge_id
        ),
    )

    await update.message.reply_text(
        "✅ Оплата получена.\n\n"
        f"💰 Начислено: {credits} кредитов."
    )


async def do_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = prepare_user(update)

    query = (
        update.message.text
        or ""
    ).strip()

    if not query:
        return

    chat = update.effective_chat

    in_group = (
        chat.type in {
            "group",
            "supergroup",
        }
        and group_enabled(
            chat.id
        )
    )

    if not charge_search(
        user.id,
        group_chat=in_group,
    ):
        await update.message.reply_text(
            "❌ Недостаточно кредитов.\n\n"
            "Используй /buy для пополнения."
        )
        return

    await update.message.reply_text(
        "🔎 Выполняю поиск..."
    )

    try:
        result = await search(
            query
        )

        token = create_report(
            tg_id=user.id,
            payload=json.dumps(
                result,
                ensure_ascii=False,
            ),
            ttl_seconds=(
                REPORT_EXPIRE_HOURS
                * 3600
            ),
        )

        local_count = len(
            result["local_results"]
        )

        await update.message.reply_text(
            "✅ Поиск завершён.\n\n"
            f"🔎 Запрос: {query}\n"
            f"📂 Совпадений: {local_count}\n"
            f"🆔 Report: {token}\n\n"
            "Результаты основаны только "
            "на публичных/разрешённых данных."
        )

    except Exception:
        logger.exception(
            "Search error"
        )

        await update.message.reply_text(
            "❌ При выполнении поиска "
            "произошла ошибка."
        )


async def group_enable(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_chat.type not in {
        "group",
        "supergroup",
    }:
        await update.message.reply_text(
            "Команда предназначена для группы."
        )
        return

    member = await update.effective_chat.get_member(
        update.effective_user.id
    )

    if member.status not in {
        "administrator",
        "creator",
    }:
        await update.message.reply_text(
            "❌ Команду может выполнить "
            "только администратор группы."
        )
        return

    enable_group(
        update.effective_chat.id
    )

    await update.message.reply_text(
        "👥 Групповой режим OSINT Core включён.\n\n"
        "Участники группы получают "
        "безлимитный доступ к поисковым функциям."
    )


async def owner_only(
    update: Update,
) -> bool:
    return (
        update.effective_user.id
        == OWNER_ID
    )


async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await owner_only(update):
        await update.message.reply_text(
            "❌ Доступ запрещён."
        )
        return

    await update.message.reply_text(
        "👑 OWNER PANEL\n\n"
        "Только владелец:\n\n"
        "💰 Доходы\n"
        "⭐ Stars\n"
        "💳 Платежи\n"
        "👥 Пользователи\n"
        "📂 Базы\n"
        "🌐 Источники\n"
        "👥 Группы\n"
        "⚙️ Настройки"
    )


async def cmd_grant(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await owner_only(update):
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "/grant <telegram_id> <credits>"
        )
        return

    user_id = int(
        context.args[0]
    )

    amount = int(
        context.args[1]
    )

    grant_credits(
        user_id,
        amount,
    )

    await update.message.reply_text(
        "✅ Кредиты начислены."
    )


async def cmd_setcredits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not await owner_only(update):
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "/setcredits <telegram_id> <credits>"
        )
        return

    user_id = int(
        context.args[0]
    )

    amount = int(
        context.args[1]
    )

    set_credits(
        user_id,
        amount,
    )

    await update.message.reply_text(
        "✅ Баланс установлен."
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing"
        )

    init_db()

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "profile",
            profile,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "buy",
            buy,
        )
    )

    application.add_handler(
        CommandHandler(
            "buy20",
            buy20,
        )
    )

    application.add_handler(
        CommandHandler(
            "buy50",
            buy50,
        )
    )

    application.add_handler(
        CommandHandler(
            "buy100",
            buy100,
        )
    )

    application.add_handler(
        CommandHandler(
            "group",
            group_enable,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin,
        )
    )

    application.add_handler(
        CommandHandler(
            "grant",
            cmd_grant,
        )
    )

    application.add_handler(
        CommandHandler(
            "setcredits",
            cmd_setcredits,
        )
    )

    application.add_handler(
        PreCheckoutQueryHandler(
            precheckout
        )
    )

    application.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            successful_payment,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            do_search,
        )
    )

    logger.info(
        "OSINT Core started"
    )

    application.run_polling()


if __name__ == "__main__":
    main()
