import os  
import requests
import datetime
from loguru import logger
import base58
from urllib.parse import quote
from solana.rpc.api import Keypair
import nacl.signing  
import nacl.encoding
import pytz
from datetime import datetime, timedelta
from utils.util import filter_token
from config.conf import *
  
# 步骤1：获取登录nonce  
def get_login_nonce(wallet_address):  
    try:  
        response = requests.get(f'https://gmgn.ai/defi/auth/v1/login_nonce?address={wallet_address}')  
        response.raise_for_status()  
        nonce = response.json()['data']['nonce']  
        return nonce  
    except requests.RequestException as error:  
        print('获取登录nonce失败:', error)  
        raise  
  
# 步骤2：生成签名消息  
def generate_message(nonce, wallet_address):  
    message = (  
        f"gmgn.ai wants you to sign in with your Solana account:\n{wallet_address}\n\n"  
        f"wallet_sign_statement\nURI: https://gmgn.ai\nVersion: 1\nChain ID: 900\n"  
        f"Nonce: {nonce}\nIssued At: {datetime.now().isoformat()}Z\n"  
        f"Expiration Time: {(datetime.now() + timedelta(days=30)).isoformat()}Z"  
    )  
    return message  
  
# 步骤3：签名消息  
def sign_message(message, secret_key):  
    message_bytes = message.encode('utf-8')  
    signing_key = nacl.signing.SigningKey(secret_key[:32], encoder=nacl.encoding.RawEncoder)  
    signed_message = signing_key.sign(message_bytes)  
    signature = signed_message.signature  
    return base58.b58encode(signature).decode('utf-8')  
  
# 步骤4：发送签名  
def login(message, signature):  
    payload = {  
        'message': message,  
        'signature': signature,  
    }  
    print('发送登录请求:', payload)  
    try:  
        response = requests.post('https://gmgn.ai/defi/auth/v1/login', json=payload)  
        response.raise_for_status()  
        result = response.json()
        print('登录成功')  
        return result
    except requests.RequestException as error:  
        print('登录失败:', error)
        return {'code': -1, 'message': '登录失败'}

def get_gmgn_token(wallet_address, private_key):
    logger.info(f"Get GMGN token for wallet: {wallet_address}")
    access_token = None
    nonce = get_login_nonce(wallet_address)
    message = generate_message(nonce, wallet_address)
    signature = sign_message(message, base58.b58decode(private_key))
    login_result = login(message, signature)
    if login_result['code'] == 0:
        access_token = login_result['data']['access_token']
    if access_token is None:
        logger.info(f"Failed to get GMGN token for wallet: {wallet_address}")
    else:
        logger.info(f"Successfully get GMGN token for wallet: {wallet_address}")
        global access_token_dict
        access_token_dict[wallet_address] = access_token
    return access_token
    
def get_gas_price(chain='sol'):
    try:
        response = requests.get(f'https://gmgn.ai/defi/quotation/v1/chains/{chain}/gas_price')
        response.raise_for_status()
        result = response.json()
        if result['code'] != 0:
            logger.info('获取Gas价格失败:', result)
            return None
        else:
            data = result['data']
            return data
    except requests.RequestException as error:
        logger.info('获取Gas价格失败:', error)
        return None

def get_token_info(token_address):
    url = f"https://gmgn.ai/defi/quotation/v1/tokens/sol/{token_address}"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    token_info = response.json()
    logger.info(f"gmgn original token info: {token_info}")
    result = {}
    result['total_supply'] = int(token_info['data']['token']['total_supply'])
    try:
        creation_timestamp = token_info['data']['token']['creation_timestamp']
        open_timestamp = token_info['data']['token']['open_timestamp']
        result['creation_timestamp'] = int(creation_timestamp) if creation_timestamp is not None else int(open_timestamp)
    except Exception as e:
        result['creation_timestamp'] = 0
    result['holder_count'] = token_info['data']['token']['holder_count']
    try:
        top_10_holder_rate = float(token_info['data']['token']['top_10_holder_rate']) * 100
    except Exception as e:
        top_10_holder_rate = 0.0
    result['top_10_holder_rate'] = f"{top_10_holder_rate:.2f}%"
    try: 
        result['pool_initial_reverse'] = float(token_info['data']['token']['pool_info']['initial_quote_reserve'])
    except:
        result['pool_initial_reverse'] = 0
        
    if 'launchpad' in token_info['data']['token']:
        result['launchpad'] = token_info['data']['token']['launchpad']
        result['launchpad_status'] = int(token_info['data']['token']['launchpad_status'])
        
    result['dexscr_ad'] = token_info['data']['token'].get('dexscr_ad', 0)
    result['dexscr_update_link'] = token_info['data']['token'].get('dexscr_update_link', 0)
    result['cto_flag'] = token_info['data']['token'].get('cto_flag', 0)
    return result

def parse_token_info(data, gass_price=None):
    logger.info("Enter parse_token_info")
    event_type = data['event_type']
    wallet_address = data['wallet_address']
    token_address = data['token']['address'] if 'token' in data else data['token_address']
    times_stamp = data['timestamp']
    local_time = datetime.fromtimestamp(times_stamp, pytz.timezone(time_zone))
    
    token_symbol = data['token']['symbol']
    token_name = data['token']['name']
    token_price = data['price_usd']
    price_change = f"{(data['price_change'] * 100):.2f}%"
    cost_usd = data['cost_usd']
    
    # 是否开仓或平仓，1为是，0为否
    is_open_or_close = int(data['is_open_or_close'])
    # 仓位状态： 新买，清仓，加仓，减仓。
    if is_open_or_close == 1:
        if event_type == "buy":
            event_type = "🟢建仓"
        elif event_type == "sell":
            event_type = "🔴清仓"
            logger.info(f"清仓信号，不推送，交易信息为：{data}")
            return None
    else:
        if event_type == "buy":
            event_type = "🟢加仓"
        elif event_type == "sell":
            event_type = "🔴减仓"
            # 如果是减仓，不需要再获取交易历史，也不需要推送消息
            logger.info(f"减仓信号，不推送，交易信息为：{data}")
            return None
    if gass_price is None:
        gass_price = get_gas_price()
    
    
    trade_history = []
    
    for self_wallet_address in private_key_dict.keys():
        access_token = access_token_dict.get(self_wallet_address, None)
        if access_token is None:
            access_token = get_gmgn_token(self_wallet_address, private_key_dict[self_wallet_address])
            access_token_dict[self_wallet_address] = access_token
        logger.info(f"Get trade history for wallet: {self_wallet_address}")
        trade_history_ = get_trade_history(token_address, access_token, self_wallet_address)
        logger.info(f"Length of trade history: {len(trade_history_)}")
        if len(trade_history_) == 0:
            continue
        trade_history.extend(trade_history_)
    
    # trade_history = get_trade_history(token_address, access_token)
    parsed_trade_history = parse_history(trade_history, now_time=local_time)
    # {'all_wallets': 7, 'full_wallets': 1, 'hold_wallets': 1, 'close_wallets': 5}
    
    cost_sol = float(cost_usd) / float(gass_price['eth_usd_price'])
    
    token_info = get_token_info(token_address)
    logger.info(f"Token info get complete, token_info: {token_info}")
    token_info['address'] = token_address
    token_info['symbol'] = token_symbol
    token_info['name'] = token_name
    token_info['price'] = float(token_price)
    
    # 避免交易监听与交易历史api时间差，导致的市值不准确，这里重新计算市值
    token_info['market_cap'] = float(token_price) * token_info['total_supply']
    token_info['price_change'] = price_change
    if token_info['creation_timestamp'] == 0:
        token_info['create_time'] = '未知'
    create_time = datetime.fromtimestamp(token_info['creation_timestamp'], pytz.timezone(time_zone))
    create_time_str = create_time.strftime('%Y-%m-%d %H:%M:%S')
    token_info['create_time'] = create_time_str
    
    delta_time = (local_time - create_time).total_seconds() / 60


    trade_info = {
        'event_type': event_type,
        'wallet_address': wallet_address,
        'token_address': token_address,
        'token_info': token_info,
        'time': local_time.strftime('%Y-%m-%d %H:%M:%S'),
        'delta_time': delta_time,
        'trade_history': parsed_trade_history,
        'cost_sol': f"{cost_sol:.3f}",
        'is_open_or_close': is_open_or_close
    }
    logger.info(f"Total trade info: {trade_info}")
    logger.info("Entering filter_token")
    filter_result = True
    if if_filter:
        filter_result = filter_token(trade_info, local_time)
    
    
    if filter_result:
        logger.info(f"Complete all filter, all passed.")
        return trade_info
    else:
        logger.info(f"Faied to pass filter.")
        return None


# def token_filter(token_trade_info, now_time):
#     event_type = token_trade_info['event_type']
#     token_info = token_trade_info['token_info']
#     trade_history = token_trade_info['trade_history']
#     market_cap = token_info['market_cap']
#     token_create_time = datetime.strptime(token_info['create_time'], '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone(time_zone))
    
#     # 过滤市值范围
#     if market_cap < min_market_cap:
#         logger.info(f"Market cap out of range: {market_cap}")
#         return False
    
#     if max_market_cap >0 and market_cap > max_market_cap:
#         logger.info(f"Market cap out of range: {market_cap}")
#         return False
    
#     # 过滤创建时间，旧盘不推送
#     if max_ceate_time > 0 and (now_time - token_create_time).total_seconds() / 60 > max_ceate_time:
#         logger.info(f"Token too old: {token_create_time}")
#         return False
    
#     if trade_history['all_wallets'] < min_buy_wallets:
#         logger.info(f"Buy wallets less than {min_buy_wallets}, not push message")
#         return False
    
#     return True


def follow_wallet(wallet_address, self_wallet_address, token, network='sol', retry=3):
    access_token = access_token_dict.get(self_wallet_address, None)
    if token != access_token:
        token = access_token
    url = f"https://gmgn.ai/defi/quotation/v1/follow/sol/follow_wallet"
    payload = {"address": wallet_address,
               "network": network}
    header = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, headers=header, json=payload)
    result = response.json()
    logger.info(f"Follow wallet result: {result}")
    # {"code":0,"msg":"success","data":{}}
    if 'code' in result and result['code'] == 0:
        return True
    else:
        logger.info(f"Failed to follow wallet: {result}, retry: {retry}")
        private_key_ = private_key_dict.get(self_wallet_address, None)
        access_token = get_gmgn_token(self_wallet_address, private_key=private_key_)
        if retry > 0:
            return follow_wallet(wallet_address, self_wallet_address, access_token, network=network, retry=retry-1)
        else:
            return False
    
def unfollow_wallet(wallet_address, self_wallet_address, token, network='sol', retry=3):
    access_token = access_token_dict.get(self_wallet_address, None)
    if token != access_token:
        token = access_token
    url = f"https://gmgn.ai/defi/quotation/v1/follow/sol/unfollow_wallet"
    payload = {"address": wallet_address,
               "network": network}
    header = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, headers=header, json=payload)
    result = response.json()
    logger.info(f"Unfollow wallet result: {result}")
    # {"code":0,"msg":"success","data":{}}
    if 'code' in result and result['code'] == 0:
        return True
    else:
        logger.info(f"Failed to unfollow wallet: {result}, retry: {retry}")
        private_key_ = private_key_dict.get(self_wallet_address, None)
        access_token = get_gmgn_token(self_wallet_address, private_key=private_key_)
        if retry > 0:
            return unfollow_wallet(wallet_address, self_wallet_address, access_token, network=network, retry=retry-1)
        else:
            return False
    
def get_following_wallets(token, self_wallet_address, network='sol', retry=3):
    access_token = access_token_dict.get(self_wallet_address, None)
    if token != access_token:
        token = access_token
    url = f"https://gmgn.ai/defi/quotation/v1/follow/{network}/following_wallets?network={network}"
    header = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=header)
    result = response.json()
    # logger.info(f"Following wallets: {result}")
    address_list = []
    if 'code' in result and result['code'] == 0:
        for wallet in result['data']['followings']:
            wallet_address = wallet['address']
            address_list.append(wallet_address)
        return address_list
    else:
        logger.info(f"Failed to get following wallets: {result}")
        private_key_ = private_key_dict.get(self_wallet_address, None)
        access_token = get_gmgn_token(self_wallet_address, private_key=private_key_)
        if retry > 0:
            return get_following_wallets(access_token, self_wallet_address, network=network, retry=retry-1)
        else:
            return address_list
    
    
    
def tag_wallet_state(token_address, access_token, network='sol'):
    url = f"https://gmgn.ai/defi/quotation/v1/tokens/tag_wallet_count/{network}/{token_address}"
    header = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=header)
    result = response.json()
    #     {
    #     "code": 0,
    #     "msg": "success",
    #     "data": {
    #         "chain": "sol",
    #         "token_address": "3B5wuUrMEi5yATD7on46hKfej3pfmd7t1RKgrsN3pump",
    #         "smart_wallets": 4,
    #         "fresh_wallets": 0,
    #         "renowned_wallets": 1,
    #         "creator_wallets": 1,
    #         "sniper_wallets": 1,
    #         "rat_trader_wallets": 1,
    #         "following_wallets": 27,
    #         "whale_wallets": 1060,
    #         "top_wallets": 0
    #     }
    # }   
    if 'code' in result and result['code'] == 0:
        return result['data']
    
def get_pnl_wallets(token, network='sol'):
    url = f"https://gmgn.ai/defi/quotation/v1/rank/{network}/wallets/7d?orderby=realized_profit_7d&direction=desc"
    header = {
        "Content-Type": "application",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=header)
    result = response.json()
    logger.info(f"PNL wallets: {result}")
    return result

    
def get_trade_history(token_address, token, self_wallet_address, network='sol', filter_event: str=None, cursor=None, retry=3):
    access_token = access_token_dict.get(self_wallet_address, None)
    if token != access_token:
        token = access_token
    filter_event_ = f"&event={filter_event}" if filter_event is not None else ""
    cursor_ = f"&cursor={quote(cursor)}" if cursor is not None else ""
    url = f"https://gmgn.ai/defi/quotation/v1/trades/{network}/{token_address}?limit=100{cursor_}{filter_event_}&maker=&following=true"
    header = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=header)
    result = response.json()
    if 'code' in result and result['code'] == 0:
        history = result['data']['history']
        # logger.info(f"Length of trade history: {len(history)}")
        if 'next' in result['data']:
            next_cursor = result['data']['next']
            if next_cursor is not None and next_cursor != '':
                next_history = get_trade_history(token_address, token, self_wallet_address, network=network, filter_event=filter_event, cursor=next_cursor)
                history.extend(next_history)
        return history
    else:
        logger.info(f"Failed to get trade history: {result}")
        private_key_ = private_key_dict.get(self_wallet_address, None)
        access_token = get_gmgn_token(self_wallet_address, private_key=private_key_)
        if retry > 0:
            return get_trade_history(token_address, access_token, self_wallet_address, network=network, filter_event=filter_event, cursor=cursor, retry=retry-1)
        else:
            return []
    
def parse_history(history, now_time=None):
    '''解析交易历史，获取每个钱包当前持仓比例，计算总购买钱包数、当前仍持仓钱包数，清仓钱包数；
        并计算10min内购买钱包数、10min内清仓钱包数
    '''
    result = {'all_wallets': 0, 'full_wallets': 0, 
              'hold_wallets': 0, 'close_wallets': 0,
              '10min_buys': 0, '10min_close': 0, 'total_trades': len(history),
              '3min_buys': 0, '3min_close': 0, 
              'total_buy': 0, 'total_sell': 0}
    first_trade_time = now_time
    wallet_info = {}
    recorded_10min_wallets = []
    recorded_10min_buy_wallets = []
    recorded_10min_sell_wallets = []
    recorded_3min_wallets = []
    recorded_3min_buy_wallets = []
    recorded_3min_sell_wallets = []
    for trade in history:
        trade_time_stamp = trade['timestamp']
        trade_local_time = datetime.fromtimestamp(trade_time_stamp, pytz.timezone(time_zone))
        
        # 避免api时间差，过滤掉now_time之后的交易
        if trade_local_time > now_time:
            continue

        wallet_address = trade['maker']
        event = trade['event']
        if event == 'buy':
            result['total_buy'] += 1
        elif event == 'sell':
            result['total_sell'] += 1
        
        is_open_or_close = trade['is_open_or_close']
        if is_open_or_close is None or is_open_or_close == '':
            is_open_or_close = 0
        is_open_or_close = int(is_open_or_close)
        logger.info(f"wallet_address: {wallet_address}, Event: {event}, is_open_or_close: {is_open_or_close}")
        balance = float(trade['balance']) if (trade['balance'] is not None) and (trade['balance'] != '') else 0
        bought_amount = float(trade['history_bought_amount'])
        sold_amount = float(trade['history_sold_amount'])
        
        if trade_local_time < first_trade_time:
            first_trade_time = trade_local_time
        
        trade_time_delta = (now_time - trade_local_time).total_seconds() / 60
        
        if trade_time_delta <= 10.0 and trade_time_delta > 3.0:
            if wallet_address not in recorded_10min_wallets:
                recorded_10min_wallets.append(wallet_address)
                if event == 'buy':
                    result['10min_buys'] += 1
                elif event == 'sell' and is_open_or_close == 1:
                    result['10min_close'] += 1
        if trade_time_delta <= 3.0:
            if wallet_address not in recorded_3min_wallets:
                recorded_3min_wallets.append(wallet_address)
                if event == 'buy':
                    result['3min_buys'] += 1
                elif event == 'sell' and is_open_or_close == 1:
                    result['3min_close'] += 1
        
        if wallet_address not in wallet_info:
            wallet_info[wallet_address] = {'balance': balance, 'bought_amount': bought_amount, 'sold_amount': sold_amount}
            if balance >= bought_amount:
                result['full_wallets'] += 1
            elif balance <= 1e-10:
                result['close_wallets'] += 1
            else:
                result['hold_wallets'] += 1
            result['all_wallets'] += 1
        else:
            continue
    result['first_trade_time'] = first_trade_time.strftime('%Y-%m-%d %H:%M:%S')
    return result
if __name__ == '__main__':
    token = get_gmgn_token()
