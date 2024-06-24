import requests  
import json  
import asyncio
import uuid  
import websockets
from loguru import logger
from datetime import datetime, timedelta  
from utils.gmgn import get_gmgn_token, get_gas_price, parse_token_info
from utils.util import generate_markdown
from config.conf import channel_id
  
token_expiry_duration = timedelta(days=28)  
token = None  
token_acquired_time = None

# 获取当前的sol价格
gass_price = get_gas_price()
  
async def subscribe(ws):  
    session_id = str(uuid.uuid4())  
    payload = {  
        "action": "subscribe",  
        "channel": "following_wallet_activity",  
        "id": session_id,  
        "data": {  
            "chain": "sol"  
        }  
    }  
    await ws.send(json.dumps(payload))  
    logger.info(f"Subscribed with session ID: {session_id}")  
  
async def send_heartbeat(ws):  
    ping_payload = {  
        "action": "ping"  
    }  
    while True:  
        try:  
            await ws.send(json.dumps(ping_payload))  
            logger.info("Sent heartbeat")
        except websockets.ConnectionClosed:  
            logger.info("Connection closed, stopping heartbeat")  
            break  
        await asyncio.sleep(30)
        
async def update_gas_price():
    global gass_price
    while True:
        gass_price = get_gas_price()
        await asyncio.sleep(20)
        

async def send_message_with_retry(bot, channel_id, message, retries=3, timeout=1):  
    attempt = 0  
    while attempt < retries:  
        try:  
            await bot.send_message(chat_id=channel_id, text=message, parse_mode="Markdown", disable_web_page_preview=True)  
            logger.info(f"Sent message: {message}")  
            return  # 成功发送消息后退出循环  
        except Exception as e:  
            logger.warning(f"Attempt {attempt + 1} failed with error: {e}")  
            attempt += 1  
            if attempt < retries:  
                logger.info(f"Retrying in {timeout} seconds...")  
                await asyncio.sleep(timeout)  # 等待一段时间后重试  
    logger.error(f"Failed to send message after {retries} attempts")

async def send_message(bot, parsed_result, channel_id=channel_id):
    try:  
        message = generate_markdown(parsed_result)  
        logger.info(f"Formatted message: {message}")  
        await send_message_with_retry(bot, channel_id, message)  
    except Exception as e:
        logger.error(f"Unexpected error: {e}")  

async def listen(ws, bot=None):
    async for message in ws:
        message = json.loads(message)
        if 'type' in message and message['type'] == 'pong':  
            logger.info("Received ping")  
            continue
        else:
            logger.info(f"Received message: {message}")
            if 'data' not in message or len(message['data']) == 0:
                continue
            follow_data = message['data'][0]
            token_address = follow_data['token']['address']
            # 过滤掉稳定币的token
            if "So11111111" in token_address:
                continue
            global gass_price
            parsed_result = parse_token_info(follow_data, gass_price=gass_price, access_token=token)
            if parsed_result is None:
                # 解析失败，或者减仓信号，不推送
                continue
            logger.info(f"parsed_result: {parsed_result}")
            if bot is not None:
                # try:
                #     message = generate_markdown(parsed_result)
                #     logger.info(f"Formated message: {message}")
                #     await bot.send_message(chat_id=channel_id, text=message, parse_mode="Markdown", disable_web_page_preview=True)
                # except Exception as e:
                #     logger.info(f"Error: {e}")
                #     await bot.send_message(chat_id=channel_id, text="error", parse_mode="Markdown", disable_web_page_preview=True)
                # logger.info(f"Sent message: {message}")
                await send_message(bot, parsed_result, channel_id=channel_id)
                
                
async def fetch_valid_token():
    global token, token_acquired_time  
    if token is None or datetime.now() - token_acquired_time >= token_expiry_duration:  
        token = get_gmgn_token()
        token_acquired_time = datetime.now()  
    return token  
  
async def connet_and_subscribe_task(bot=None):
    task = asyncio.create_task(connect_and_subscribe(bot))
    logger.info("Task created.")


async def connect_and_subscribe(bot=None):
    await bot.send_message(chat_id=channel_id, text="机器人启动成功！")
    while True:  
        try:  
            token = await fetch_valid_token()
            websocket_url = f"wss://ws.gmgn.ai/stream?tk={token}"  
            async with websockets.connect(websocket_url) as ws:  
                await subscribe(ws)  
  
                # Create tasks for heartbeat and listening  
                heartbeat_task = asyncio.create_task(send_heartbeat(ws))  
                listen_task = asyncio.create_task(listen(ws, bot=bot))  
  
                # Wait for either task to complete  
                done, pending = await asyncio.wait(  
                    [heartbeat_task, listen_task],  
                    return_when=asyncio.FIRST_COMPLETED  
                )  
  
                # Cancel all pending tasks  
                for task in pending:  
                    task.cancel()  
        except (websockets.ConnectionClosed, ConnectionRefusedError) as e:  
            logger.info(f"Connection lost: {e}. Reconnecting in 5 seconds...")  
            await asyncio.sleep(5)  
  
if __name__ == "__main__":  
    asyncio.run(connect_and_subscribe())  
