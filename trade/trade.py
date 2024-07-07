import asyncio
from loguru import logger
import datetime
from trade.dbot import get_wallet_id, dbot_simulate_swap, dbot_swap
from databases.database import insert_send_trade, get_send_trade
from config.conf import dbot_token, dbot_wallet_id, trade_monitor

async def send_trade_with_retry(bot, channel_id, parsed_result, retries=3, timeout=1):
    token_address = parsed_result['token_address']
    token_price = parsed_result['token_info']['price']
    
    # +120% change
    token_price_1_2 = token_price * 2.2
    
    attempt = 0
    history_trade = await get_send_trade(token_address, trade_monitor, trade_type=0)
    # 是否买入过
    if len(history_trade) > 0:
        return
    amountOrPercent = 0.2
    
    global dbot_wallet_id
    try:
        if dbot_wallet_id is None or dbot_wallet_id == "":
            dbot_wallet_id = get_wallet_id(dbot_token)[0]
    except Exception as e:
        logger.error(f"Failed to get wallet id: {e}")
        return
    while attempt < retries:
        try:
            if trade_monitor == 0:
                result = dbot_swap(dbot_wallet_id, token_address, dbot_token, amountOrPercent)
                message = f"成功发送交易, Token ca: {token_address}. 交易金额: {amountOrPercent}."
            else:
                result = dbot_simulate_swap(dbot_wallet_id, token_address, dbot_token, amountOrPercent)
                message = f"成功发送模拟交易, Token ca: {token_address}. 交易金额: {amountOrPercent}."
            if result:
                await insert_send_trade(token_address, 0, trade_monitor, 0, datetime.datetime.now())
                await bot.send_message(chat_id=channel_id, text=message, parse_mode="Markdown", disable_web_page_preview=True)
                break
        except Exception as e:
            logger.error(f"Failed to send trade: {e}")
        attempt += 1
        await asyncio.sleep(timeout)
    