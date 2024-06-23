from telegram import Update, Bot
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, Updater
import asyncio
import threading
from loguru import logger
from sub import connect_and_subscribe
from config.conf import bot_token


def run_asyncio_coroutine(coroutine, loop):  
    asyncio.set_event_loop(loop)  
    loop.run_until_complete(coroutine)  

def main():
    # 创建事件循环  
    loop = asyncio.new_event_loop()  
    asyncio.set_event_loop(loop)

    application = Application.builder().token(bot_token).build()
    
    loop.run_until_complete(connect_and_subscribe(application.bot))
    
    # 在子线程中运行 bot 的事件循环  
    threading.Thread(target=run_asyncio_coroutine, args=(application.run_polling(), loop)).start()   
    
if __name__ == '__main__':
    main()