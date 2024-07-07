from loguru import logger
from config.conf import min_market_cap, max_market_cap, filter_in_launch_pad, following_wallets_nums

def format_number(num):  
    """  
    将浮点数格式化为一般数字、千(K)、百万(M)、十亿(B)的形式  
  
    :param num: 浮点数  
    :return: 格式化后的字符串  
    """  
    if num < 1_000:  
        return f"{num:.0f}"  # 不保留小数  
    elif num < 1_000_000:  
        return f"{num / 1_000:.2f}K"  
    elif num < 1_000_000_000:  
        return f"{num / 1_000_000:.2f}M"  
    else:  
        return f"{num / 1_000_000_000:.2f}B"
    
def format_price(price):  
    # 将浮点数转换为字符串，并找到第一个非零数字的位置  
    price_str = "{:.10e}".format(price)  
    parts = price_str.split("e")  
    mantissa = parts[0].rstrip('0')  
    exponent = int(parts[1])  
      
    if exponent < -4:  
        # 保留4位有效数字，并格式化前面的0  
        significant_digits = mantissa.replace('.', '')[:4]  
        leading_zeros = abs(exponent) - 1  
        formatted_price = f"0.0{{{leading_zeros}}}{significant_digits}"  
    else:  
        # 直接格式化为4位有效数字  
        formatted_price = "{:.4g}".format(price)  
  
    return formatted_price

def generate_markdown(parsed_result):
    """  
    生成Markdown格式的消息  
      
    :param parsed_result: 解析后的数据
    :return: Markdown格式的消息  
    """
    trade_history = parsed_result['trade_history']
    token_id = parsed_result['token_address']
    # {'all_wallets': 7, 'full_wallets': 1, 'hold_wallets': 1, 'close_wallets': 5}
    # 总购买🟦, 全仓符号🟩， 减仓符号🟨, 清仓符号🟥
    total_num_symbol = f"***{trade_history['all_wallets']}*** | " + ''.join(["🟩" for _ in range(trade_history['full_wallets'])]) + ''.join(["🟨" for _ in range(trade_history['hold_wallets'])]) + ''.join(["🟥" for _ in range(trade_history['close_wallets'])])
    # total_num_symbol = f"**{trade_history['all_wallets']}**" + ''.join(["🟦" for _ in range(trade_history['all_wallets'])])
    # full_num_symbol = f"**{trade_history['full_wallets']}**" + ''.join(["🟩" for _ in range(trade_history['full_wallets'])])
    # part_num_symbol = f"**{trade_history['hold_wallets']}**" + ''.join(["🟨" for _ in range(trade_history['hold_wallets'])])
    # closed_num_symbol = f"**{trade_history['close_wallets']}**" + ''.join(["🟥" for _ in range(trade_history['close_wallets'])])
    first_trade_time = trade_history['first_trade_time']

    token_info = parsed_result['token_info']
    market_cap_str = format_number(token_info['market_cap'])
    token_price_str = format_price(token_info['price'])
    
    total_following_wallets = sum(following_wallets_nums.values())
    # fomo度计算
    fomo = trade_history['10min_buys'] / trade_history['all_wallets'] + \
        min(trade_history['all_wallets'] / 5, 3) + \
            trade_history['full_wallets'] / trade_history['all_wallets'] + \
                trade_history['hold_wallets'] / trade_history['all_wallets'] + \
                    - trade_history['close_wallets'] / trade_history['all_wallets']

    # 根据fomo度，输出热度符🔥，将fomo映射到0,10区间，向上取整
    fomo_range = int(round(fomo))
    fomo_range = max(1, fomo_range)
    if fomo_range > 10:
        fomo_range = 10
    
    fomo_symbol = ''.join(["🔥" for _ in range(fomo_range)])
    

    message = f"**{parsed_result['event_type']}**, **{parsed_result['cost_sol']} SOL**  ***{token_info['symbol']}({token_info['name']})***\n\n"
    message += f"**热度**: {fomo_symbol}\n"
    message += f"**交易时间**: {parsed_result['time']}\n"
    message += f"**CA**: `{token_id}`\n"
    message += f"***市值***: ***${market_cap_str}*** (${token_price_str})\n\n"
    message += f"**10分钟内买入钱包**: ***{trade_history['10min_buys']}***; **10分钟内清仓钱包**: ***{trade_history['10min_close']}***\n\n"
    message += f"**第一位买入时间**: ***{first_trade_time}***\n"
    message += f"🟩全仓 | 🟨减仓 | 🟥清仓 \n\n"
    message += f"**买入钱包数**: {total_num_symbol}\n"
    # message += f"**全仓数**: {full_num_symbol}\n"
    # message += f"**减仓数**: {part_num_symbol}\n"
    # message += f"**清仓数**: {closed_num_symbol}\n"
    message += f"**持有人**: {token_info['holder_count']}, " + f"**TOP10比例**: {token_info['top_10_holder_rate']}\n\n"
    message += f"**钱包地址**: [{parsed_result['wallet_address']}](https://gmgn.ai/sol/address/{parsed_result['wallet_address']})\n"
    message += f"🔗 一键交易: [Trojan](https://t.me/solana_trojanbot?start=r-marcle253818-{token_id}) | [GMGN](https://t.me/GMGN_sol_bot?start={token_id}) | [Pepe](https://t.me/pepeboost_sol12_bot?start=ref_0nh46x_ca_{token_id}) | [Cash](https://t.me/CashCash_trade_bot?start=ref_132dfe48-7_ca_{token_id}) \n"
    message += f"🔗 曲线: [GMGN](https://gmgn.ai/sol/token/{parsed_result['token_address']}) | [Dex](https://dexscreener.com/solana/{token_id}) | [Ave](https://ave.ai/token/{token_id}-solana) \n"
    return message


def filter_token(parsed_result):
    token_id = parsed_result['token_address']
    trade_history = parsed_result['trade_history']
    token_info = parsed_result['token_info']
    
    
    if trade_history['close_wallets'] == 0 and trade_history['10min_buys'] >= 2 and trade_history['10min_close'] == 0 and trade_history['full_wallets'] >= 3:
        logger.info(f"token: {token_id} passed filter trade fomo. trade stats: {trade_history}")
    else:
        logger.info(f"token: {token_id} failed filter trade fomo. trade stats: {trade_history}")
        return False
    
    if token_info['market_cap'] >= min_market_cap and token_info['market_cap'] <= max_market_cap:
        logger.info(f"token: {token_id} passed filter market cap. Market cap: {token_info['market_cap']}")
    else:
        logger.info(f"token: {token_id} failed filter market cap. Market cap: {token_info['market_cap']}")
        return False
    
    if 'launchpad' in token_info:
        # 如果过滤掉各种内盘，则设置filter_in_launch_pad为1
        launchpad_status = token_info['launchpad_status']
        if launchpad_status == 0 and filter_in_launch_pad:
            logger.info(f"token: {token_id} failed filter launchpad. Launchpad status: {launchpad_status}")
            return False
        elif launchpad_status == 1:
            # 如果已经发射，过滤一下初始sol数, 以pump为参考, 初始sol数大于30
            if token_info['pool_initial_reverse'] < 30:
                logger.info(f"token: {token_id} failed filter launchpad. It's launched, but Pool initial reverse is small: {token_info['pool_initial_reverse']}")
                return False
        else:
            return True
    
    # 如果没有launchpad，那需要过滤一下初始sol数, 以pump为参考, 初始sol数大于30
    elif token_info['pool_initial_reverse'] < 30:
        return False
    
    # ... 添加更多过滤条件
    
    
    logger.info(f"token: {token_id} passed all filters.")
    return True