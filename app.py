from telegram import Update, Bot
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, Updater
import asyncio
import threading
from loguru import logger
from sub import connect_and_subscribe, connet_and_subscribe_task
from utils.gmgn import follow_wallet, unfollow_wallet
from sub import token, fetch_valid_token
from config.conf import bot_token

ALLOWED_USER_IDS = [6573081218]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    logger.info(f"User {update.effective_user.id} started the bot.")
    if update.effective_user.id in ALLOWED_USER_IDS:  
        await update.message.reply_text('Welcome to the Wallet Subscription Bot! Use /add, /list, /rm commands.')  
    else:
        await update.message.reply_text('You are not allowed to use this command.')

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    logger.info(f"User {update.effective_user.id} entering add_wallet.")
    global token
    if update.effective_user.id in ALLOWED_USER_IDS:  
        args = context.args  
        if len(args) == 1:  
            wallet_address = args[0]
            if token is None:
                token = await fetch_valid_token()
            result = follow_wallet(wallet_address=wallet_address, token=token)
            await update.message.reply_text("Wallet added successfully." if result else "Failed to add wallet.")
        else:  
            await update.message.reply_text('Usage: /add <wallet_address>')  
    else:
        await update.message.reply_text('You are not allowed to use this command.')

async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"User {update.effective_user.id} entering delete_wallet.")
    global token
    if update.effective_user.id in ALLOWED_USER_IDS:  
        args = context.args  
        if len(args) == 1:  
            wallet_address = args[0]
            if token is None:
                token = await fetch_valid_token()
            result = unfollow_wallet(wallet_address=wallet_address, token=token)
            await update.message.reply_text("Wallet removed successfully." if result else "Failed to remove wallet.")
        else:  
            await update.message.reply_text('Usage: /rm <wallet_address>')  
    else:
        await update.message.reply_text('You are not allowed to use this command.')

def run_asyncio_coroutine(coroutine, loop):  
    asyncio.set_event_loop(loop)  
    loop.run_until_complete(coroutine)  

def main():
    # 创建事件循环  
    loop = asyncio.new_event_loop()  
    asyncio.set_event_loop(loop)

    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_wallet))
    application.add_handler(CommandHandler("rm", delete_wallet))
    
    commands = [BotCommand("/start", "Start the bot."), 
                BotCommand("/add", "/add <wallet_address> to add a wallet."), 
                BotCommand("/rm", "/rm <wallet_address> to remove a wallet.")]
    
    result = loop.run_until_complete(application.bot.set_my_commands(commands))
    logger.info(f"Set commands result: {result}")
    
    loop.run_until_complete(connet_and_subscribe_task(application.bot))
    
    logger.info(f"Starting bot commands...")
    # # 在子线程中运行 bot 的事件循环  
    threading.Thread(target=run_asyncio_coroutine, args=(application.run_polling(), loop)).start()   
    
if __name__ == '__main__':
    main()