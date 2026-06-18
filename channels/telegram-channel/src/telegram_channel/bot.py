import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .k8s import K8sClient
from .state import ConversationState

logger = logging.getLogger("telegram-channel")


DEFAULT_BASE_URL = "https://api.telegram.org/bot"


def create_bot(
    token: str,
    namespace: str,
    base_url: str = DEFAULT_BASE_URL,
    k8s: K8sClient | None = None,
    state: ConversationState | None = None,
) -> Application:
    k8s = k8s or K8sClient(namespace=namespace)
    state = state or ConversationState()

    builder = Application.builder().token(token)
    if base_url != DEFAULT_BASE_URL:
        file_url = base_url.replace("/bot", "/file/bot")
        builder = builder.base_url(base_url).base_file_url(file_url)
    app = builder.build()

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        state.clear_session(chat_id)

        try:
            agents = k8s.list_agents()
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            await update.message.reply_text(
                "Failed to connect to Ark cluster. Check service logs."
            )
            return

        if not agents:
            await update.message.reply_text(
                "No agents found in this namespace.\n"
                "Create an Agent resource and try /start again."
            )
            return

        keyboard = []
        for a in agents:
            label = a["name"]
            if a["description"]:
                label += f" - {a['description'][:40]}"
            keyboard.append(
                [InlineKeyboardButton(label, callback_data=f"agent:{a['name']}")]
            )

        await update.message.reply_text(
            "Choose an agent:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def agent_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        agent_name = query.data.split(":", 1)[1]
        chat_id = query.message.chat_id
        user_id = query.from_user.id

        state.set_agent(chat_id, agent_name, user_id)
        logger.info(f"Chat {chat_id} connected to agent {agent_name}")
        await query.edit_message_text(
            f"Connected to {agent_name}. Send a message to start chatting.\n"
            f"Use /switch to change agent.",
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        session = state.get_session(chat_id)

        if not session:
            await cmd_start(update, context)
            return

        await update.effective_chat.send_action("typing")

        try:
            response = await k8s.submit_query(
                agent=session["agent"],
                prompt=update.message.text,
                conversation_id=session["conversation_id"],
                session_id=session["session_id"],
            )
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.message.reply_text(
                        response[i : i + 4096], parse_mode="Markdown",
                    )
            else:
                await update.message.reply_text(response, parse_mode="Markdown")
        except TimeoutError:
            await update.message.reply_text(
                "The agent took too long to respond. Try again or /switch agent."
            )
        except Exception as e:
            logger.error(f"Query error for chat {chat_id}: {e}")
            await update.message.reply_text(f"Error: {e}")

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("agents", cmd_start))
    app.add_handler(CommandHandler("switch", cmd_start))
    app.add_handler(CallbackQueryHandler(agent_selected, pattern=r"^agent:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
