from loguru import logger
from datetime import datetime
import pytz
from config.conf import min_market_cap, max_market_cap, filter_in_launch_pad, following_wallets_nums, filter_dex_socials, filter_dex_ads, time_zone, max_ceate_time, min_buy_wallets, strategy

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
    total_num_symbol = f"***{trade_history['all_wallets']}*** | " + \
        ''.join(["🟩" for _ in range(trade_history['full_wallets'])]) + \
            ''.join(["🟨" for _ in range(trade_history['hold_wallets'])]) + \
                ''.join(["🟥" for _ in range(trade_history['close_wallets'])])
    first_trade_time = trade_history['first_trade_time']

    token_info = parsed_result['token_info']
    create_time = token_info['create_time']
    create_time_str = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone)).strftime('%Y-%m-%d %H:%M:%S')
    
    # minutes
    delta_time = parsed_result['delta_time']
    is_new = False
    if delta_time <= 4 * 60:
        is_new = True
    new_str = f"🆕" if is_new else ""
    
    dexscr_ad = token_info['dexscr_ad']
    dexscr_update_link = token_info['dexscr_update_link']
    dex_str = ""
    if dexscr_ad:
        dex_str += f"***Dex广告👍*** | "
    else:
        dex_str += f"***Dex广告❌*** | "
    if dexscr_update_link:
        dex_str += f"***Dex社交媒体👍*** | "
    else:
        dex_str += f"***Dex社交媒体❌*** | "
    if dex_str != "":
        dex_str = dex_str[:-2] + "\n\n"
    
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
    net_in_volume_1m_str = format_number(token_info['net_in_volume_1m'])
    net_in_volume_5m_str = format_number(token_info['net_in_volume_5m'])
    

    message = f"***{new_str}*** **{parsed_result['event_type']}**, **{parsed_result['cost_sol']} SOL**  ***{token_info['symbol']}({token_info['name']})***\n\n"
    message += f"**热度**: {fomo_symbol}\n"
    message += f"**交易时间**: {parsed_result['time']}\n"
    message += f"**CA**: `{token_id}`\n"
    message += f"***市值***: ***${market_cap_str}*** (${token_price_str})\n\n"
    message += dex_str
    message += f"**3min买**: {trade_history['3min_buys']}; **10min买**: ***{trade_history['10min_buys']}***; \n\n"
    message += f"***1m净流入***: ***${net_in_volume_1m_str}***; ***5m净流入***: ***${net_in_volume_5m_str}***; \n\n"
    message += f"**创建时间**: ***{create_time_str}***\n"
    message += f"🟩全仓 | 🟨减仓 | 🟥清仓 \n\n"
    message += f"**买入钱包数**: {total_num_symbol}\n"
    message += f"**持有人**: {token_info['holder_count']}, " + f"**TOP10比例**: {token_info['top_10_holder_rate']}\n\n"
    message += f"**钱包地址**: [{parsed_result['wallet_address']}](https://gmgn.ai/sol/address/{parsed_result['wallet_address']})\n"
    message += f"🔗 一键交易: [Trojan](https://t.me/solana_trojanbot?start=r-marcle253818-{token_id}) | [GMGN](https://t.me/GMGN_sol_bot?start={token_id}) | [Pepe](https://t.me/pepeboost_sol12_bot?start=ref_0nh46x_ca_{token_id}) | [Cash](https://t.me/CashCash_trade_bot?start=ref_132dfe48-7_ca_{token_id}) \n"
    message += f"🔗 曲线: [GMGN](https://gmgn.ai/sol/token/{parsed_result['token_address']}) | [Dex](https://dexscreener.com/solana/{token_id}) | [Ave](https://ave.ai/token/{token_id}-solana) \n"
    return message


def filter_token_strategy_1(parsed_result, now_time):
    '''策略1
    '''
    token_id = parsed_result['token_address']
    trade_history = parsed_result['trade_history']
    origin_history = parsed_result['origin_history']
    token_info = parsed_result['token_info']
    # kline = parsed_result['kline']
    token_create_time = datetime.strptime(token_info['create_time'], '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone))
    # 如果市值大于150k，钱包数小于2，可以推送。如果市值不满足，则过滤掉钱包数小于2的
    markect_cap = token_info['market_cap']
    if trade_history['all_wallets'] < 2:
        if markect_cap < 150000:
            logger.info(f"token: {token_id} failed to filter min buy wallets, all wallets: {trade_history['all_wallets']}, min_buy_wallets: {min_buy_wallets}")
            return False
        else:
            logger.info(f"token: {token_id} passed regular 1. all wallets: {trade_history['all_wallets']}, market cap: {markect_cap}")
            return True
    else:
        logger.info(f"token: {token_id} passed regular 1. all wallets: {trade_history['all_wallets']}, market cap: {markect_cap}")
        
    # 钱包数大于等于4，且无清仓信号，可以推送
    if trade_history['all_wallets'] >= 4 and trade_history['close_wallets'] < 1:
        logger.info(f"token: {token_id} passed regular 2. all wallets: {trade_history['all_wallets']}, close wallets: {trade_history['close_wallets']}")
        return True
    
    # 市值在64k-1M之间，且如果这次买入比上次买入，价格增加了80%，可以推送
    if markect_cap >= 50000 and markect_cap <= 1000000:
        the_last_buy = None
        last_second_buy = None
        for trade in origin_history:
            event = trade['event']
            if event == 'sell':
                continue
            if the_last_buy is None:
                the_last_buy = trade
                continue
            if last_second_buy is None:
                last_second_buy = trade
                continue
            break
        the_last_buy_price = float(the_last_buy['price_usd'])
        
        last_second_buy_price = float(last_second_buy['price_usd'])
        
        if the_last_buy_price > 0 and last_second_buy_price > 0:
            price_increase = the_last_buy_price / last_second_buy_price
            if price_increase >= 1.8:
                logger.info(f"token: {token_id} passed regular 3. price increase: {price_increase}")
                return True
            else:
                logger.info(f"token: {token_id} failed to filter price increase. price increase: {price_increase}")
                return False
        
    else:
        logger.info(f"token: {token_id} failed to filter market cap. Market cap: {markect_cap}")
        return False
    
    return False


def filter_token(parsed_result, now_time):
    ''' 简单过滤规则
    '''
    
    if strategy == 1:
        return filter_token_strategy_1(parsed_result, now_time)
    
    token_id = parsed_result['token_address']
    trade_history = parsed_result['trade_history']
    token_info = parsed_result['token_info']
    token_create_time = datetime.strptime(token_info['create_time'], '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone))
    
    if trade_history['all_wallets'] >= min_buy_wallets:
        logger.info(f"token: {token_id} passwd filter min buy wallets")
    else:
        logger.info(f"token: {token_id} failed to filter min buy wallets, all wallets: {trade_history['all_wallets']}, min_buy_wallets: {min_buy_wallets}")
        return False
    
    if token_info['market_cap'] >= min_market_cap:
        logger.info(f"token: {token_id} passed filter min market cap. Market cap: {token_info['market_cap']}")
    else:
        logger.info(f"token: {token_id} failed filter min market cap. Market cap: {token_info['market_cap']}")
        return False

    if max_market_cap > 0 and token_info['market_cap'] > max_market_cap:
        logger.info(f"token: {token_id} passed filter max market cap. Market cap: {token_info['market_cap']}")
        return False
    
    # 过滤创建时间，旧盘不推送
    if max_ceate_time > 0 and (now_time - token_create_time).total_seconds() / 60 > max_ceate_time:
        logger.info(f"Token too old: {token_create_time}")
        return False
    
    if filter_dex_socials:
        if token_info['dexscr_update_link']:
            logger.info(f"token: {token_id} passed filter dex socials. Dex socials: {token_info['dexscr_update_link']}")
        else:
            logger.info(f"token: {token_id} failed filter dex socials. Dex socials: {token_info['dexscr_update_link']}")
            return False
    
    if filter_dex_ads:
        if token_info['dexscr_ad']:
            logger.info(f"token: {token_id} passed filter dex ads. Dex ads: {token_info['dexscr_ad']}")
        else:
            logger.info(f"token: {token_id} failed filter dex ads. Dex ads: {token_info['dexscr_ad']}")
            return False
    
    
    # ... 添加更多过滤条件
    
    
    logger.info(f"token: {token_id} passed all filters.")
    return True
