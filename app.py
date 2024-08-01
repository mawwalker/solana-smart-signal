import os
from config.conf import time_zone
os.environ['TZ'] = time_zone

from telegram import Update, Bot
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, Updater
import asyncio
import threading
from loguru import logger
from fastapi import FastAPI
import uvicorn
from sub import connect_and_subscribe, connect_and_subscribe_task
from utils.gmgn import follow_wallet, unfollow_wallet, get_following_wallets
from sub import fetch_valid_token
from databases.database import create_tables
from config.conf import bot_token, private_key_dict, access_token_dict, admin_list

ALLOWED_USER_IDS = admin_list


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"User {update.effective_user.id} started the bot.")
    if update.effective_user.id in ALLOWED_USER_IDS:  
        await update.message.reply_text('Welcome to the Wallet Subscription Bot! Use /add, /list, /rm commands.')  
    else:
        await update.message.reply_text('You are not allowed to use this command.')

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    logger.info(f"User {update.effective_user.id} entering add_wallet.")
    if update.effective_user.id in ALLOWED_USER_IDS:  
        args = context.args  
        if len(args) == 1:  
            wallet_address = args[0]
            
            
            not_full_wallet = None
            for self_wallet_address in access_token_dict.keys():
                access_token = access_token_dict.get(self_wallet_address, None)
                if access_token is None:
                    access_token = await fetch_valid_token(wallet_address=self_wallet_address)
                folling_wallets = get_following_wallets(token=access_token, self_wallet_address=self_wallet_address)
                if wallet_address in folling_wallets:
                    await update.message.reply_text("Wallet already added. You don't need to add it again.")
                    return
                following_num = len(folling_wallets)
                if following_num < 100 and not_full_wallet is None:
                    not_full_wallet = self_wallet_address

            access_token = access_token_dict.get(not_full_wallet, None)
            result = follow_wallet(wallet_address=wallet_address, self_wallet_address=not_full_wallet, token=access_token)
            await update.message.reply_text(f"Wallet subscribed successfully to wallet address: {not_full_wallet}" if result else "Failed to add wallet.")
        else:  
            await update.message.reply_text('Usage: /add <wallet_address>')  
    else:
        await update.message.reply_text('You are not allowed to use this command.')

async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"User {update.effective_user.id} entering delete_wallet.")
    if update.effective_user.id in ALLOWED_USER_IDS:  
        args = context.args  
        if len(args) == 1:  
            wallet_address = args[0]
            
            
            followed_by_wallet = None
            for self_wallet_address in access_token_dict.keys():
                access_token = access_token_dict.get(self_wallet_address, None)
                if access_token is None:
                    access_token = await fetch_valid_token(wallet_address=self_wallet_address)
                folling_wallets = get_following_wallets(token=access_token, self_wallet_address=self_wallet_address)
                if wallet_address in folling_wallets:
                    followed_by_wallet = self_wallet_address
                    break
            if followed_by_wallet is None:
                await update.message.reply_text("Wallet not found.")
                return
            access_token = access_token_dict.get(followed_by_wallet, None)
            
            result = unfollow_wallet(wallet_address=wallet_address, self_wallet_address=followed_by_wallet, token=access_token)
            await update.message.reply_text(f"Wallet removed successfully from wallet address: {followed_by_wallet}" if result else "Failed to remove wallet.")
        else:  
            await update.message.reply_text('Usage: /rm <wallet_address>')  
    else:
        await update.message.reply_text('You are not allowed to use this command.')
        
async def get_wallet_nums(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    logger.info(f"User {update.effective_user.id} entering get_wallet_nums.")
    if update.effective_user.id in ALLOWED_USER_IDS:  
        args = context.args  
        for wallet_address in access_token_dict.keys():
            access_token = access_token_dict.get(wallet_address, None)
            if access_token is None:
                access_token = await fetch_valid_token(wallet_address=wallet_address)
            folling_wallets = get_following_wallets(token=access_token, self_wallet_address=wallet_address)
            following_num = len(folling_wallets)
            logger.info(f"Wallet {wallet_address} has {following_num} following wallets.")
            await update.message.reply_text(f"Wallet {wallet_address} has {following_num} following wallets.")
    else:
        await update.message.reply_text('You are not allowed to use this command.')


async def main():
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_wallet))
    application.add_handler(CommandHandler("rm", delete_wallet))
    application.add_handler(CommandHandler("list", get_wallet_nums))

    # Set bot commands
    result = await application.bot.set_my_commands([
        BotCommand("/start", "Start the bot."),
        BotCommand("/add", "/add <wallet_address> to add a wallet."),
        BotCommand("/rm", "/rm <wallet_address> to remove a wallet."),
        BotCommand("/list", "List all wallets and their following wallets.")
    ])
    logger.info(f"Set commands result: {result}")

    # Create tables in the database
    database_result = await create_tables()
    logger.info(f"Create tables result: {database_result}")

    # Initialize and start the application
    async with application:
        await application.start()
        await application.updater.start_polling()

        # Start the connect_and_subscribe_task concurrently
        connect_and_subscribe = asyncio.create_task(connect_and_subscribe_task(application.bot))
        
        # Keep the event loop running until you want to shut down
        try:
            await asyncio.Future()  # Run forever
        finally:
            await application.updater.stop()
            await application.stop()
            connect_and_subscribe.cancel()  # Cancel the connect and subscribe task
            await application.shutdown()

   
if __name__ == '__main__':
    asyncio.run(main())
