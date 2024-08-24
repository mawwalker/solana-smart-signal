from loguru import logger
from datetime import datetime
import pytz
from config.conf import (
    min_market_cap,
    max_market_cap,
    filter_in_launch_pad,
    following_wallets_nums,
    filter_dex_socials,
    filter_dex_ads,
    time_zone,
    max_ceate_time,
    min_buy_wallets,
    strategy,
)


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
    mantissa = parts[0].rstrip("0")
    exponent = int(parts[1])

    if exponent < -4:
        # 保留4位有效数字，并格式化前面的0
        significant_digits = mantissa.replace(".", "")[:4]
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
    trade_history = parsed_result["trade_history"]
    token_id = parsed_result["token_address"]
    # {'all_wallets': 7, 'full_wallets': 1, 'hold_wallets': 1, 'close_wallets': 5}
    # 总购买🟦, 全仓符号🟩， 减仓符号🟨, 清仓符号🟥
    total_num_symbol = (
        f"***{trade_history['all_wallets']}*** | "
        + "".join(["🟩" for _ in range(trade_history["full_wallets"])])
        + "".join(["🟨" for _ in range(trade_history["hold_wallets"])])
        + "".join(["🟥" for _ in range(trade_history["close_wallets"])])
    )
    first_trade_time = trade_history["first_trade_time"]

    strategy_type = parsed_result.get("strategy", None)

    token_info = parsed_result["token_info"]
    create_time_str = token_info["create_time"]
    if create_time_str == "未知" or create_time_str == "" or create_time_str is None:
        create_time_str = token_info["open_time"]
    # create_time_str = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone)).strftime('%Y-%m-%d %H:%M:%S')

    # minutes
    delta_time = parsed_result["delta_time"]
    is_new = False
    if delta_time <= 4 * 60:
        is_new = True
    new_str = f"🆕" if is_new else ""

    dexscr_ad = token_info["dexscr_ad"]
    dexscr_update_link = token_info["dexscr_update_link"]
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

    market_cap_str = format_number(token_info["market_cap"])
    token_price_str = format_price(token_info["price"])

    total_following_wallets = sum(following_wallets_nums.values())
    # fomo度计算
    fomo = (
        trade_history["10min_buys"] / trade_history["all_wallets"]
        + min(trade_history["all_wallets"] / 5, 3)
        + trade_history["full_wallets"] / trade_history["all_wallets"]
        + trade_history["hold_wallets"] / trade_history["all_wallets"]
        + -trade_history["close_wallets"] / trade_history["all_wallets"]
    )

    # 根据fomo度，输出热度符🔥，将fomo映射到0,10区间，向上取整
    fomo_range = int(round(fomo))
    fomo_range = max(1, fomo_range)
    if fomo_range > 10:
        fomo_range = 10

    fomo_symbol = "".join(["🔥" for _ in range(fomo_range)])
    net_in_volume_1m_str = format_number(token_info["net_in_volume_1m"])
    net_in_volume_5m_str = format_number(token_info["net_in_volume_5m"])

    message = f"***{new_str}*** **{parsed_result['event_type']}**, **{parsed_result['cost_sol']} SOL**  ***{token_info['symbol']}({token_info['name']})***\n\n"
    message += f"**热度**: {fomo_symbol}\n"
    message += f"**交易时间**: {parsed_result['time']}\n"
    if strategy_type is not None:
        message += f"**策略**: {strategy_type}\n"
    message += f"**CA**: `{token_id}`\n"
    message += f"***市值***: ***${market_cap_str}*** (${token_price_str})\n\n"
    message += dex_str
    message += f"**3min买**: {trade_history['3min_buys']}; **10min买**: ***{trade_history['10min_buys']}***; \n\n"
    message += f"***1m净流入***: ***${net_in_volume_1m_str}***; ***5m净流入***: ***${net_in_volume_5m_str}***; \n\n"
    message += f"**创建时间**: ***{create_time_str}***\n"
    message += f"🟩全仓 | 🟨减仓 | 🟥清仓 \n\n"
    message += f"**买入钱包数**: {total_num_symbol}\n"
    message += (
        f"**持有人**: {token_info['holder_count']}, "
        + f"**TOP10比例**: {token_info['top_10_holder_rate']}\n\n"
    )
    message += f"**钱包地址**: [{parsed_result['wallet_address']}](https://gmgn.ai/sol/address/{parsed_result['wallet_address']})\n"
    message += f"🔗 一键交易: [Trojan](https://t.me/solana_trojanbot?start=r-marcle253818-{token_id}) | [GMGN](https://t.me/GMGN_sol_bot?start={token_id}) | [Pepe](https://t.me/pepeboost_sol12_bot?start=ref_0nh46x_ca_{token_id}) | [Cash](https://t.me/CashCash_trade_bot?start=ref_132dfe48-7_ca_{token_id}) \n"
    message += f"🔗 曲线: [GMGN](https://gmgn.ai/sol/token/{parsed_result['token_address']}) | [Dex](https://dexscreener.com/solana/{token_id}) | [Ave](https://ave.ai/token/{token_id}-solana) \n"
    return message


def filter_token_strategy_1(parsed_result, now_time):
    """策略1"""
    token_id = parsed_result["token_address"]
    trade_history = parsed_result["trade_history"]
    origin_history = parsed_result["origin_history"]
    token_info = parsed_result["token_info"]
    # kline = parsed_result['kline']
    token_create_time = datetime.strptime(
        token_info["create_time"], "%Y-%m-%d %H:%M:%S"
    ).astimezone(pytz.timezone(time_zone))
    # 如果市值大于150k，钱包数小于2，可以推送。如果市值不满足，则过滤掉钱包数小于2的
    markect_cap = token_info["market_cap"]
    # if trade_history['all_wallets'] < 2:
    #     if markect_cap < 150000:
    #         logger.info(f"token: {token_id} failed to filter min buy wallets, all wallets: {trade_history['all_wallets']}, min_buy_wallets: {min_buy_wallets}")
    #         return False
    #     else:
    #         logger.info(f"token: {token_id} passed regular 1. all wallets: {trade_history['all_wallets']}, market cap: {markect_cap}")
    #         return True
    # else:
    #     logger.info(f"token: {token_id} passed regular 1. all wallets: {trade_history['all_wallets']}, market cap: {markect_cap}")

    # 钱包数大于等于4，且无清仓信号，可以推送
    if trade_history["all_wallets"] >= 4 and trade_history["close_wallets"] < 1:
        logger.info(
            f"token: {token_id} passed regular 2. all wallets: {trade_history['all_wallets']}, close wallets: {trade_history['close_wallets']}"
        )
        return True

    # 市值在20k-1M之间，且如果这次买入比上次买入，价格增加了80%，可以推送
    if markect_cap > 20000 and markect_cap <= 1000000:
        the_last_buy = None
        last_second_buy = None
        for trade in origin_history:
            event = trade["event"]
            if event == "sell":
                continue
            if the_last_buy is None:
                the_last_buy = trade
                continue
            if last_second_buy is None:
                last_second_buy = trade
                continue
            break
        the_last_buy_price = float(the_last_buy["price_usd"])

        last_second_buy_price = float(last_second_buy["price_usd"])

        if the_last_buy_price > 0 and last_second_buy_price > 0:
            price_increase = the_last_buy_price / last_second_buy_price
            if price_increase >= 1.8:
                logger.info(
                    f"token: {token_id} passed regular 3. price increase: {price_increase}"
                )
                return True
            else:
                logger.info(
                    f"token: {token_id} failed to filter price increase. price increase: {price_increase}"
                )
                return False

    else:
        logger.info(
            f"token: {token_id} failed to filter market cap. Market cap: {markect_cap}"
        )
        return False

    return False


def judge_price_increase(parsed_result, threshold=0.75):
    """判断当前信号是否比上一个信号价格增加了一定比例"""
    trade_history = parsed_result["trade_history"]
    origin_history = parsed_result["origin_history"]
    the_last_buy = None
    last_second_buy = None
    # 如果钱包数不足2，返回False
    if trade_history["all_wallets"] < 2:
        return False, None, None, None
    for trade in origin_history:
        event = trade["event"]
        if event == "sell":
            continue
        if the_last_buy is None:
            the_last_buy = trade
            continue
        if last_second_buy is None:
            last_second_buy = trade
            continue
        break
    the_last_buy_price = float(the_last_buy["price_usd"])

    last_second_buy_price = float(last_second_buy["price_usd"])

    if the_last_buy_price > 0 and last_second_buy_price > 0:
        price_increase = the_last_buy_price / last_second_buy_price
        if price_increase >= threshold + 1:
            return True, price_increase, the_last_buy_price, last_second_buy_price
    return False, None, None, None


def quatify_mc_and_net_change(
    parsed_result,
    mc_range=(0, 1e9),
    net_in_1min_range=(0, 1e9),
    net_in_5min_range=(0, 1e9),
    net_in_diff_range=(0, 1e9),
):
    """量化市值和净流入的变化
    其中， mc_range, net_in_1min_range, net_in_5min_range, net_in_diff_range分别是市值，1min净流入，5min净流入，5min-1min净流入的范围
        例如: 300k以下慢拉性净流入1min净流入300-1k，5min大于3k小于5k
        quatify_mc_and_net_change(parsed_result, mc_range=(0, 300000),
                                        net_in_1min_range=(300, 1000), net_in_5min_range=(3000, 5000))
    """
    token_info = parsed_result["token_info"]
    markect_cap = token_info["market_cap"]
    net_in_volume_1m = token_info["net_in_volume_1m"]
    net_in_volume_5m = token_info["net_in_volume_5m"]
    net_in_diff = net_in_volume_5m - net_in_volume_1m
    return (
        markect_cap >= mc_range[0]
        and markect_cap < mc_range[1]
        and net_in_volume_1m >= net_in_1min_range[0]
        and net_in_volume_1m < net_in_1min_range[1]
        and net_in_volume_5m >= net_in_5min_range[0]
        and net_in_volume_5m < net_in_5min_range[1]
        and net_in_diff >= net_in_diff_range[0]
        and net_in_diff < net_in_diff_range[1]
    )


def buy_and_close_judge(parsed_result, wallets_num=4):
    """判断连续买入，不清仓，连续买入次数大于等于4"""
    trade_history = parsed_result["trade_history"]
    if (
        trade_history["all_wallets"] >= wallets_num
        and trade_history["close_wallets"] < 1
    ):
        return True
    return False


def token_safe_judge(parsed_result):
    """判断币种安全性"""
    token_info = parsed_result["token_info"]
    if (
        int(token_info["renounced_mint"])
        and int(token_info["renounced_freeze_account"])
        and float(token_info["burn_ratio"]) > 0
        and str(token_info["burn_status"]) == "burn"
    ):
        return True
    return False


def filter_token_strategy_2(parsed_result, now_time):
    """策略2"""
    token_id = parsed_result["token_address"]
    trade_history = parsed_result["trade_history"]
    origin_history = parsed_result["origin_history"]
    token_info = parsed_result["token_info"]
    # kline = parsed_result['kline']
    # token_create_time = datetime.strptime(token_info['create_time'], '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone))
    # token_open_time = datetime.strptime(
    #     token_info["open_time"], "%Y-%m-%d %H:%M:%S"
    # ).astimezone(pytz.timezone(time_zone))
    launchpad = None
    launchpad_status = 1  # launchpad_status: 0:内盘，1:外盘
    # 钱包数大于等于2，这次信号比上次信号，价格增加了75%
    if_price_increase, price_increase, the_last_buy_price, last_second_buy_price = (
        judge_price_increase(parsed_result)
    )

    # 1. 价格上涨满足条件
    if if_price_increase:
        # 1.1 300k以下慢拉性净流入1min净流入300-1k，5min大于3k小于5k
        if quatify_mc_and_net_change(
            parsed_result,
            mc_range=(0, 300000),
            net_in_1min_range=(300, 1000),
            net_in_5min_range=(3000, 5000),
        ):
            logger.info(
                f"token: {token_id} passed regular 1.1 Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "1.1"}
        # 1.2 100k以下快拉性净流入1min大于3k，5min大于9k,并且5min减去1min的差值大于3.5k
        if quatify_mc_and_net_change(
            parsed_result,
            mc_range=(0, 100000),
            net_in_1min_range=(3000, 1e9),
            net_in_5min_range=(9000, 1e9),
            net_in_diff_range=(3500, 1e9),
        ):
            logger.info(
                f"token: {token_id} passed regular 1.2 Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "1.2"}
        # 1.3 100k以上300k以下，1min净流入2k-6.5k，5min净流入大于6.5k小于15k，或者5min减去1min的差值大于8.5k
        if quatify_mc_and_net_change(
            parsed_result,
            mc_range=(100000, 300000),
            net_in_1min_range=(2000, 6500),
            net_in_5min_range=(6500, 15000),
            net_in_diff_range=(0, 1e9),
        ) or quatify_mc_and_net_change(
            parsed_result,
            mc_range=(100000, 300000),
            net_in_1min_range=(0, 1e9),
            net_in_5min_range=(0, 1e9),
            net_in_diff_range=(8500, 1e9),
        ):
            logger.info(
                f"token: {token_id} passed regular 1.3 Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "1.3"}
    logger.info(f"Failed to pass regular 1.")

    # 2. 钱包数大于等于4，且无清仓信号，也过一遍上面的三个量化策略
    if buy_and_close_judge(parsed_result):
        # 2.1 300k以下慢拉性净流入1min净流入300-1k，5min大于3k小于5k
        if quatify_mc_and_net_change(
            parsed_result,
            mc_range=(0, 300000),
            net_in_1min_range=(300, 1000),
            net_in_5min_range=(3000, 5000),
        ):
            logger.info(
                f"token: {token_id} passed regular 2.1 Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "2.1"}
        # 2.2 100k以下快拉性净流入1min大于3k，5min大于9k,并且5min减去1min的差值大于3.5k
        if quatify_mc_and_net_change(
            parsed_result,
            mc_range=(0, 100000),
            net_in_1min_range=(3000, 1e9),
            net_in_5min_range=(9000, 1e9),
            net_in_diff_range=(3500, 1e9),
        ):
            logger.info(
                f"token: {token_id} passed regular 2.2 Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "2.2"}
        # 2.3 100k以上300k以下，1min净流入2k-6.5k，5min净流入大于6.5k小于15k，或者5min减去1min的差值大于8.5k
        if quatify_mc_and_net_change(
            parsed_result,
            mc_range=(100000, 300000),
            net_in_1min_range=(2000, 6500),
            net_in_5min_range=(6500, 15000),
            net_in_diff_range=(0, 1e9),
        ) or quatify_mc_and_net_change(
            parsed_result,
            mc_range=(100000, 300000),
            net_in_1min_range=(0, 1e9),
            net_in_5min_range=(0, 1e9),
            net_in_diff_range=(8500, 1e9),
        ):
            logger.info(
                f"token: {token_id} passed regular 2.3 Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "2.3"}
    logger.info(f"Failed to pass regular 2.")

    # 3. 当前是第一个信号，且市值大于300k，满足5min-1min净流入大于10k
    if (
        trade_history["all_wallets"] == 1
        and token_info["market_cap"] >= 300000
        and token_info["net_in_volume_5m"] - token_info["net_in_volume_1m"] > 10000
    ):
        logger.info(
            f"token: {token_id} passed regular 3. Market cap: {token_info['market_cap']}"
        )
        return {"pass": True, "strategy": "3"}
    logger.info(f"Failed to pass regular 3.")

    # 4. 100k以下快拉性净流入1min大于3k，5min大于9k,并且5min减去1min的差值大于3.5k.
    if quatify_mc_and_net_change(
        parsed_result,
        mc_range=(0, 100000),
        net_in_1min_range=(3000, 1e9),
        net_in_5min_range=(9000, 1e9),
        net_in_diff_range=(3500, 1e9),
    ):
        logger.info(
            f"token: {token_id} passed regular 4. Market cap: {token_info['market_cap']}"
        )
        return {"pass": True, "strategy": "4"}
    logger.info(f"Failed to pass regular 4.")

    # 5. 如果当前是第二个信号，第一个信号超过100k，且当前信号相比上一个信号，价格增加了75%以上
    if trade_history["all_wallets"] == 2:
        # 计算第一个信号的市值
        if the_last_buy_price is not None and last_second_buy_price is not None:
            last_second_buy_mc = last_second_buy_price * (
                token_info["market_cap"] / token_info["price"]
            )
            if last_second_buy_mc > 100000 and price_increase >= 1.75:
                logger.info(
                    f"token: {token_id} passed regular 5. Market cap: {token_info['market_cap']}"
                )
                return {"pass": True, "strategy": "5"}
    logger.info(f"Failed to pass regular 5.")

    # 6.信号超过500k，加安全性检测,限制市值在500k-2M
    if (
        token_info["market_cap"] >= 500000
        and token_info["market_cap"] <= 2000000
        and token_safe_judge(parsed_result)
        and trade_history["all_wallets"] <= 2
    ):
        # 1. 慢拉性1min<0 5min>7.5k或者0<1min<1k 5min>7.5k
        # 2. 快拉性2k<1min 5min>5k 但是如果5min-1min>13.5k不行
        # 3. 热度盘5min>100k
        result_6_1 = quatify_mc_and_net_change(
            parsed_result,
            mc_range=(500000, 2000000),
            net_in_1min_range=(0, 1000),
            net_in_5min_range=(7500, 1e9),
        )
        result_6_2 = quatify_mc_and_net_change(
            parsed_result,
            mc_range=(500000, 2000000),
            net_in_1min_range=(2000, 1e9),
            net_in_5min_range=(5000, 1e9),
            net_in_diff_range=(0, 13500),
        )
        result_6_3 = token_info["net_in_volume_5m"] > 100000
        if result_6_1 or result_6_2 or result_6_3:
            logger.info(
                f"token: {token_id} passed regular 6. Market cap: {token_info['market_cap']}"
            )
            return {"pass": True, "strategy": "6"}
    logger.info(f"Failed to pass regular 6.")

    return {"pass": False, "strategy": "None"}


def filter_token_strategy_3(parsed_result, now_time):
    """大市值策略"""
    token_id = parsed_result["token_address"]
    trade_history = parsed_result["trade_history"]
    origin_history = parsed_result["origin_history"]
    token_info = parsed_result["token_info"]
    # kline = parsed_result['kline']
    token_create_time = datetime.strptime(
        token_info["create_time"], "%Y-%m-%d %H:%M:%S"
    ).astimezone(pytz.timezone(time_zone))

    markect_cap = token_info["market_cap"]

    # result['renounced_mint'] = token_info['data']['token'].get('renounced_mint', 0)
    # result['renounced_freeze_account'] = token_info['data']['token'].get('renounced_freeze_account', 0)
    # result['burn_ratio'] = token_info['data']['token'].get('burn_ratio', 0)
    # result['burn_status'] = token_info['data']['token'].get('burn_status', 0)

    # 当前是第一个信号，且市值大于500k，且币种安全性全通过，5min-1min净流入大于3.5k  token_info['net_in_volume_5m'] - token_info['net_in_volume_1m'] > 3500 and \
    if (
        trade_history["all_wallets"] == 1
        and markect_cap >= 500000
        and int(token_info["renounced_mint"])
        and int(token_info["renounced_freeze_account"])
        and float(token_info["burn_ratio"]) > 0
        and str(token_info["burn_status"]) == "burn"
    ):
        logger.info(f"token: {token_id} passed regular 1. Market cap: {markect_cap}")
        return True
    else:
        logger.info(
            f"token: {token_id} failed to filter strategy 3, part 1. Market cap: {markect_cap}"
        )

    # 或者当前信号是第二个信号，且市值大于500k，相比上一个信号，价格增加了80%以上，安全性全通过, 5min-1min净流入大于3.5k   # token_info['net_in_volume_5m'] - token_info['net_in_volume_1m'] > 3500 and \
    if (
        trade_history["all_wallets"] == 2
        and markect_cap >= 500000
        and int(token_info["renounced_mint"])
        and int(token_info["renounced_freeze_account"])
        and float(token_info["burn_ratio"]) > 0
        and str(token_info["burn_status"]) == "burn"
    ):
        the_last_buy = None
        last_second_buy = None
        for trade in origin_history:
            event = trade["event"]
            if event == "sell":
                continue
            if the_last_buy is None:
                the_last_buy = trade
                continue
            if last_second_buy is None:
                last_second_buy = trade
                continue
            break
        the_last_buy_price = float(the_last_buy["price_usd"])

        last_second_buy_price = float(last_second_buy["price_usd"])

        if the_last_buy_price > 0 and last_second_buy_price > 0:
            price_increase = the_last_buy_price / last_second_buy_price
            if price_increase >= 1.8:
                logger.info(
                    f"token: {token_id} passed regular 2. price increase: {price_increase}"
                )
                return True
            else:
                logger.info(
                    f"token: {token_id} failed to filter price increase. price increase: {price_increase}"
                )
                return False
    else:
        logger.info(
            f"token: {token_id} failed to filter strategy 3, part 2. Market cap: {markect_cap}"
        )

    return False


def filter_token(parsed_result, now_time):
    """简单过滤规则"""

    if strategy == 1:
        return filter_token_strategy_1(parsed_result, now_time)

    elif strategy == 2:
        return filter_token_strategy_2(parsed_result, now_time)
    elif strategy == 3:
        return filter_token_strategy_3(parsed_result, now_time)

    token_id = parsed_result["token_address"]
    trade_history = parsed_result["trade_history"]
    token_info = parsed_result["token_info"]
    # token_create_time = datetime.strptime(token_info['create_time'], '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone))

    if trade_history["all_wallets"] >= min_buy_wallets:
        logger.info(f"token: {token_id} passwd filter min buy wallets")
    else:
        logger.info(
            f"token: {token_id} failed to filter min buy wallets, all wallets: {trade_history['all_wallets']}, min_buy_wallets: {min_buy_wallets}"
        )
        return False

    if token_info["market_cap"] >= min_market_cap:
        logger.info(
            f"token: {token_id} passed filter min market cap. Market cap: {token_info['market_cap']}"
        )
    else:
        logger.info(
            f"token: {token_id} failed filter min market cap. Market cap: {token_info['market_cap']}"
        )
        return False

    if max_market_cap > 0 and token_info["market_cap"] > max_market_cap:
        logger.info(
            f"token: {token_id} passed filter max market cap. Market cap: {token_info['market_cap']}"
        )
        return False

    # 过滤创建时间，旧盘不推送
    # if max_ceate_time > 0 and (now_time - token_create_time).total_seconds() / 60 > max_ceate_time:
    #     logger.info(f"Token too old: {token_create_time}")
    #     return False

    if filter_dex_socials:
        if token_info["dexscr_update_link"]:
            logger.info(
                f"token: {token_id} passed filter dex socials. Dex socials: {token_info['dexscr_update_link']}"
            )
        else:
            logger.info(
                f"token: {token_id} failed filter dex socials. Dex socials: {token_info['dexscr_update_link']}"
            )
            return False

    if filter_dex_ads:
        if token_info["dexscr_ad"]:
            logger.info(
                f"token: {token_id} passed filter dex ads. Dex ads: {token_info['dexscr_ad']}"
            )
        else:
            logger.info(
                f"token: {token_id} failed filter dex ads. Dex ads: {token_info['dexscr_ad']}"
            )
            return False

    # ... 添加更多过滤条件

    logger.info(f"token: {token_id} passed all filters.")
    return True
