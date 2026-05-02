import asyncio
import json
import sys

# Workaround for Python Windows Proactor Event Loop bug
if sys.platform.startswith("win"):
    from asyncio.proactor_events import _ProactorBasePipeTransport
    from functools import wraps
    def silence_event_loop_closed(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != 'Event loop is closed':
                    raise
        return wrapper
    _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from tools.registry import tool
import config
from agents.chat_agent import ChatAgent

class TelegramBridge:
    def __init__(self, agent: ChatAgent):
        import importlib
        importlib.reload(config)
        self.agent = agent
        self.authorized_chat_id = int(config.TELEGRAM_CHAT_ID) if config.TELEGRAM_CHAT_ID else None
        self.pending_permissions = {} # store future to wait for button click

    async def check_auth(self, update: Update):
        if self.authorized_chat_id and update.effective_chat.id != self.authorized_chat_id:
            await update.message.reply_text("⛔ Unauthorized access.")
            return False
        return True

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        
        user_input = update.message.text
        if not user_input: return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        status_msg = await update.message.reply_text("🧬 Agent thinking...")
        full_response = ""
        
        try:
            gen = self.agent.run(user_input)
            
            def safe_step(g, val=None, is_send=False):
                try:
                    return g.send(val) if is_send else next(g)
                except StopIteration:
                    return StopIteration

            chunk = await asyncio.to_thread(safe_step, gen)
            
            while chunk is not StopIteration:
                if isinstance(chunk, str):
                    if chunk.startswith("__ASK_PERMISSION__"):
                        parts = chunk.split(":", 2)
                        tool_name = parts[1]
                        tool_params = parts[2]
                        if len(tool_params) > 60:
                            tool_params = tool_params[:60] + "...}"
                        
                        # Create buttons
                        keyboard = [
                            [
                                InlineKeyboardButton("✅ Approve", callback_data=f"perm:yes:{tool_name}"),
                                InlineKeyboardButton("❌ Deny", callback_data=f"perm:no:{tool_name}")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        perm_msg = await update.message.reply_text(
                            f"🛡️ **Permission Required**\nTool: `{tool_name}`\nParams: `{tool_params}`",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        
                        # Wait for the button click
                        loop = asyncio.get_running_loop()
                        future = loop.create_future()
                        self.pending_permissions[perm_msg.message_id] = future
                        
                        approved = await future
                        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=perm_msg.message_id)
                        
                        chunk = await asyncio.to_thread(safe_step, gen, approved, True)
                        
                    elif chunk.startswith("__UI_STATUS__"):
                        status_text = chunk.replace("__UI_STATUS__:", "").strip()
                        try:
                            await context.bot.edit_message_text(
                                chat_id=update.effective_chat.id,
                                message_id=status_msg.message_id,
                                text=f"⚡ {status_text}"
                            )
                        except: pass
                        chunk = await asyncio.to_thread(safe_step, gen)
                    elif not chunk.startswith("__"):
                        full_response += chunk
                        chunk = await asyncio.to_thread(safe_step, gen)
                    else:
                        chunk = await asyncio.to_thread(safe_step, gen)
                else:
                    chunk = await asyncio.to_thread(safe_step, gen)
                    
            if full_response:
                if len(full_response) > 4000:
                    for i in range(0, len(full_response), 4000):
                        await update.message.reply_text(full_response[i:i+4000])
                else:
                    await update.message.reply_text(full_response)
            else:
                await update.message.reply_text("✅ Task complete.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        msg_id = query.message.message_id
        if msg_id in self.pending_permissions:
            action = query.data.split(":")[1]
            future = self.pending_permissions.pop(msg_id)
            future.set_result(action == "yes")

    # Command Handlers
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        help_text = (
            "🤖 **Agent Control Active**\n\n"
            "Commands:\n"
            "/mode <online/offline> - Switch between online and offline mode\n"
            "/list\\_models - List all available Models\n"
            "/model <name> - Switch LLM model\n"
            "/status - Check current configuration\n"
            "/clear - Reset conversation history\n"
            "/help - Show this guide\n\n"
            "Just send a message to start a task!"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        if not context.args:
            models = self.agent.get_available_models()
            await update.message.reply_text(f"Available models: {', '.join(models)}\nUsage: `/model <name>`", parse_mode="Markdown")
            return
        
        new_model = context.args[0]
        self.agent.set_model(new_model)
        await update.message.reply_text(f"✅ Model switched to `{new_model}`", parse_mode="Markdown")

    async def cmd_mode(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        if not context.args:
            await update.message.reply_text("Usage: `/mode <online/offline>`", parse_mode="Markdown")
            return
        new_mode = context.args[0]
        if new_mode not in ["online","offline"]:
            await update.message.reply_text("Invalid mode. Use 'online' or 'offline'.", parse_mode="Markdown")
            return
        self.agent.set_mode(new_mode)
        await update.message.reply_text(f"✅ Mode switched to `{new_mode}`", parse_mode="Markdown")

    async def cmd_list_models(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        local_models = self.agent.get_available_models()
        msg = f"*Local Models:*\n- " + "\n- ".join(local_models)
        
        if self.agent.mode != "offline" and self.agent.online_models:
            # Escape underscores for markdown parser
            safe_online = [m.replace("_", "\\_") for m in self.agent.online_models]
            msg += f"\n\n*Online Models:*\n- " + "\n- ".join(safe_online)
            
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        status = (
            f"📊 **Agent Status**\n"
            f"- Model: `{self.agent.model}`\n"
            f"- Mode: `{self.agent.mode}`\n"
            f"- Tools: `Enabled`"
        )
        await update.message.reply_text(status, parse_mode="Markdown")

    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        self.agent.messages = [{"role": "system", "content": self.agent.base_system_prompt + self.agent.tools_prompt}]
        await update.message.reply_text("🧹 Conversation history cleared.")

async def start_bot_chat(agent: ChatAgent):
    import importlib
    importlib.reload(config)
    token = config.TELEGRAM_BOT_TOKEN
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN missing.")
        return

    bridge = TelegramBridge(agent)
    app = ApplicationBuilder().token(token).connect_timeout(30.0).read_timeout(30.0).build()
    
    # Commands
    app.add_handler(CommandHandler("start", bridge.cmd_start))
    app.add_handler(CommandHandler("help", bridge.cmd_start))
    app.add_handler(CommandHandler("model", bridge.cmd_model))
    app.add_handler(CommandHandler("list_models", bridge.cmd_list_models))
    app.add_handler(CommandHandler("mode", bridge.cmd_mode))
    app.add_handler(CommandHandler("status", bridge.cmd_status))
    app.add_handler(CommandHandler("clear", bridge.cmd_clear))
    
    # Callbacks (for permission buttons)
    app.add_handler(CallbackQueryHandler(bridge.handle_callback))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bridge.handle_message))
    
    print("🚀 Telegram Bot is now active with full command support.")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()
        # Allow extra time for transport sockets to cleanly close
        await asyncio.sleep(0.1)
