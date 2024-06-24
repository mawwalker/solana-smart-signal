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
    total_num_symbol = f"**{trade_history['all_wallets']}**" + ''.join(["🟦" for _ in range(trade_history['all_wallets'])])
    full_num_symbol = f"**{trade_history['full_wallets']}**" + ''.join(["🟩" for _ in range(trade_history['full_wallets'])])
    part_num_symbol = f"**{trade_history['hold_wallets']}**" + ''.join(["🟨" for _ in range(trade_history['hold_wallets'])])
    closed_num_symbol = f"**{trade_history['close_wallets']}**" + ''.join(["🟥" for _ in range(trade_history['close_wallets'])])
    first_trade_time = trade_history['first_trade_time']

    message = f"**{parsed_result['event_type']}**, **{parsed_result['cost_sol']} SOL**  ***{parsed_result['token_info']['symbol']}({parsed_result['token_info']['name']})***\n\n"
    message += f"**交易时间**: {parsed_result['time']}\n"
    message += f"**CA**: `{token_id}`\n"
    message += f"***市值***: ***${parsed_result['token_info']['market_cap']}*** (${parsed_result['token_info']['price']})\n\n"
    message += f"**10分钟内买入钱包**: ***{trade_history['10min_buys']}***; **10分钟内清仓钱包**: ***{trade_history['10min_close']}***\n\n"
    message += f"**第一位买入时间**: ***{first_trade_time}***\n"
    message += f"**买入钱包数**: {total_num_symbol}\n"
    message += f"**全仓数**: {full_num_symbol}\n"
    message += f"**减仓数**: {part_num_symbol}\n"
    message += f"**清仓数**: {closed_num_symbol}\n"
    message += f"**持有人**: {parsed_result['token_info']['holder_count']}, " + f"**TOP10比例**: {parsed_result['token_info']['top_10_holder_rate']}\n\n"
    message += f"**钱包地址**: [{parsed_result['wallet_address']}](https://gmgn.ai/sol/address/{parsed_result['wallet_address']})\n"
    message += f"🔗 一键交易: [Trojan](https://t.me/solana_trojanbot?start=r-marcle253818-{token_id}) | [GMGN](https://t.me/GMGN_sol_bot?start={token_id}) | [Pepe](https://t.me/pepeboost_sol12_bot?start=ref_0nh46x_ca_{token_id}) | [Cash](https://t.me/CashCash_trade_bot?start=ref_132dfe48-7_ca_{token_id}) \n"
    message += f"🔗 曲线: [GMGN](https://gmgn.ai/sol/token/{parsed_result['token_address']}) \n"
    return message