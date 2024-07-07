import requests  
import json  
import asyncio
import uuid  
import websockets
from loguru import logger
from datetime import datetime, timedelta
from utils.gmgn import get_gmgn_token, get_gas_price, parse_token_info, get_following_wallets
from utils.util import generate_markdown, filter_token
from trade.dbot import get_wallet_id, dbot_simulate_swap, dbot_swap
from trade.trade import send_trade_with_retry
from databases.database import insert_token_notify, get_token_notify
from config.conf import channel_id, access_token_dict, private_key_dict, repeat_push, trade_monitor, following_wallets_nums
  
token_expiry_duration = timedelta(hours=2)  
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
  
async def send_heartbeat(ws, wallet_address=None, access_token=None):
    ping_payload = {  
        "action": "ping"  
    }
    global following_wallets_nums
    while True:  
        try:  
            await ws.send(json.dumps(ping_payload))  
            logger.info("Sent heartbeat")
            if access_token is not None:
                # 只是为了保证token不过期
                following_wallets = get_following_wallets(token=access_token)
                following_wallets_nums[wallet_address] = len(following_wallets)
                logger.info(f"Sent heartbeat, following wallets nums: {len(following_wallets)}")
                # logger.info(f"Following wallets: {following_wallets}")
        except websockets.ConnectionClosed:  
            logger.info("Connection closed, stopping heartbeat")  
            break  
        await asyncio.sleep(30)
        
async def update_gas_price():
    global gass_price
    while True:
        gass_price = get_gas_price()
        logger.info(f"Update gas price: {gass_price}")
        await asyncio.sleep(20)
        

async def send_message_with_retry(bot, channel_id, message, token_address, retries=3, timeout=1):  
    attempt = 0
    if not repeat_push:
        history_push = await get_token_notify(token_address)
        if len(history_push) > 0:
            logger.info(f"Token {token_address} has been pushed, skip")
            return
    while attempt < retries:  
        try:
            await bot.send_message(chat_id=channel_id, text=message, parse_mode="Markdown", disable_web_page_preview=True)
            logger.info(f"Sent message: {message}")
            if not repeat_push:
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                await insert_token_notify(token_address, now_time)
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
        token_address = parsed_result['token_address']
        logger.info(f"Formatted message: {message}")  
        
        if trade_monitor != -1:
            await send_trade_with_retry(bot, channel_id, token_address)
        await send_message_with_retry(bot, channel_id, message, token_address)  
    except Exception as e:
        logger.error(f"Unexpected error: {e}")  

async def listen(ws, bot=None):
    async for message in ws:
        try:
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
                if "So11111111" in token_address or token_address == 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v':
                    continue
                global gass_price
                parsed_result = parse_token_info(follow_data, gass_price=gass_price)
                if parsed_result is None:
                    # 解析失败，或者减仓信号，不推送
                    continue
                logger.info(f"parsed_result: {parsed_result}")
                if bot is not None:
                    await send_message(bot, parsed_result, channel_id=channel_id)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
                
                
async def fetch_valid_token(wallet_address):
    global token_acquired_time
    wallet_token = access_token_dict.get(wallet_address, None)
    private_key = private_key_dict.get(wallet_address, None)
    if wallet_token is None or datetime.now() - token_acquired_time >= token_expiry_duration:  
        wallet_token = get_gmgn_token(wallet_address=wallet_address, private_key=private_key)
        token_acquired_time = datetime.now()
        access_token_dict[wallet_address] = wallet_token
    return wallet_token
  
async def connet_and_subscribe_task(bot=None):
    await bot.send_message(chat_id=channel_id, text="机器人启动成功！")
    gas_price_task = asyncio.create_task(update_gas_price())
    for wallet_address in access_token_dict.keys():
        task = asyncio.create_task(connect_and_subscribe(wallet_address, bot))
        logger.info(f"Task created for wallet: {wallet_address}")


async def connect_and_subscribe(wallet_address, bot=None):
    while True:  
        try:  
            wallet_token = await fetch_valid_token(wallet_address)
            websocket_url = f"wss://ws.gmgn.ai/stream?tk={wallet_token}"  
            async with websockets.connect(websocket_url) as ws:  
                await subscribe(ws)  
  
                # Create tasks for heartbeat and listening  
                heartbeat_task = asyncio.create_task(send_heartbeat(ws, wallet_address, wallet_token))  
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
