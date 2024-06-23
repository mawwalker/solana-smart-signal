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
from utils.util import format_number, format_price
from config.conf import private_key_base58, wallet_address, time_zone
  
# 将Base58格式的私钥转换为字节数组  
secret_key = base58.b58decode(private_key_base58)
  
# 验证私钥长度是否正确（64字节）  
if len(secret_key) != 64:  
    raise ValueError("私钥长度不正确，应该为64字节。")  
  
# 创建Keypair对象  
keypair = Keypair.from_base58_string(private_key_base58)  
public_key = Keypair.pubkey(keypair)  
  
if str(public_key) != wallet_address:  
    raise ValueError(f"私钥和钱包地址不匹配。公钥: {public_key}, 钱包地址: {wallet_address}")  
else:  
    print('私钥和钱包地址匹配')  
  
# 步骤1：获取登录nonce  
def get_login_nonce():  
    try:  
        response = requests.get(f'https://gmgn.ai/defi/auth/v1/login_nonce?address={wallet_address}')  
        response.raise_for_status()  
        nonce = response.json()['data']['nonce']  
        return nonce  
    except requests.RequestException as error:  
        print('获取登录nonce失败:', error)  
        raise  
  
# 步骤2：生成签名消息  
def generate_message(nonce):  
    message = (  
        f"gmgn.ai wants you to sign in with your Solana account:\n{wallet_address}\n\n"  
        f"wallet_sign_statement\nURI: https://gmgn.ai\nVersion: 1\nChain ID: 900\n"  
        f"Nonce: {nonce}\nIssued At: {datetime.now().isoformat()}Z\n"  
        f"Expiration Time: {(datetime.now() + timedelta(days=30)).isoformat()}Z"  
    )  
    return message  
  
# 步骤3：签名消息  
def sign_message(message):  
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

def get_gmgn_token():
    nonce = get_login_nonce()
    message = generate_message(nonce)
    signature = sign_message(message)
    result = login(message, signature)
    if result['code'] == 0:
        logger.info('登录成功')
        access_token = result['data']['access_token']
        return access_token
    else:
        return None
    
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
    result['market_cap'] = format_number(float(token_info['data']['token']['market_cap']))
    result['holder_count'] = token_info['data']['token']['holder_count']
    result['top_10_holder_rate'] = f"{(token_info['data']['token']['top_10_holder_rate'] * 100):.2f}%"
    return result

def parse_token_info(data, gass_price=None, access_token=None):
    event_type = data['event_type']
    wallet_address = data['wallet_address']
    token_address = data['token']['address']
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
            event_type = "🟢BUY·新买"
        elif event_type == "sell":
            event_type = "🔴Sell·清仓"
    else:
        if event_type == "buy":
            event_type = "🟢BUY·加仓"
        elif event_type == "sell":
            event_type = "🔴Sell·减仓"
            # 如果是减仓，不需要再获取交易历史，也不需要推送消息
            logger.info(f"减仓信号，不推送，交易信息为：{data}")
            return None
    if gass_price is None:
        gass_price = get_gas_price()
    
    # import pdb; pdb.set_trace()
    now_time = datetime.now(tz=pytz.timezone(time_zone))
    trade_history = get_trade_history(token_address, access_token)
    parsed_trade_history = parse_history(trade_history, now_time=now_time)
    # {'all_wallets': 7, 'full_wallets': 1, 'hold_wallets': 1, 'close_wallets': 5}
    
    cost_sol = float(cost_usd) / float(gass_price['eth_usd_price'])
    
    token_info = get_token_info(token_address)
    token_info['address'] = token_address
    token_info['symbol'] = token_symbol
    token_info['name'] = token_name
    token_info['price'] = format_price(float(token_price))
    token_info['price_change'] = price_change
    
    trade_info = {
        'event_type': event_type,
        'wallet_address': wallet_address,
        'token_address': token_address,
        'token_info': token_info,
        'time': local_time,
        'trade_history': parsed_trade_history,
        'cost_sol': f"{cost_sol:.3f}",
        'is_open_or_close': is_open_or_close
    }
    
    return trade_info

def follow_wallet(wallet_address, token, network='sol'):
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
        return False
    
def unfollow_wallet(wallet_address, token, network='sol'):
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
        return False
    
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
    
def get_trade_history(token_address, token, network='sol', filter_event: str=None, cursor=None):
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
            next_history = get_trade_history(token_address, token, network=network, filter_event=filter_event, cursor=next_cursor)
            history.extend(next_history)
        return history
    else:
        return []
    
def parse_history(history, now_time=None):
    '''解析交易历史，获取每个钱包当前持仓比例，计算总购买钱包数、当前仍持仓钱包数，清仓钱包数；
        并计算10min内购买钱包数、10min内清仓钱包数
    '''
    result = {'all_wallets': 0, 'full_wallets': 0, 
              'hold_wallets': 0, 'close_wallets': 0,
              '10min_buys': 0, '10min_close': 0}
    wallet_info = {}
    recorded_10min_wallets = []
    for trade in history:
        wallet_address = trade['maker']
        event = trade['event']
        is_open_or_close = trade['is_open_or_close']
        if is_open_or_close is None or is_open_or_close == '':
            is_open_or_close = 0
        is_open_or_close = int(is_open_or_close)
        logger.info(f"wallet_address: {wallet_address}, Event: {event}, is_open_or_close: {is_open_or_close}")
        balance = float(trade['balance']) if (trade['balance'] is not None) and (trade['balance'] != '') else 0
        bought_amount = float(trade['history_bought_amount'])
        sold_amount = float(trade['history_sold_amount'])
        trade_time_stamp = trade['timestamp']
        trade_local_time = datetime.fromtimestamp(trade_time_stamp, pytz.timezone(time_zone))
        trade_time_delta = (now_time - trade_local_time).total_seconds() / 60
        
        if trade_time_delta <= 10.0:
            if wallet_address not in recorded_10min_wallets:
                recorded_10min_wallets.append(wallet_address)
                if event == 'buy':
                    result['10min_buys'] += 1
                elif event == 'sell' and is_open_or_close == 1:
                    result['10min_close'] += 1
        
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
    return result
if __name__ == '__main__':
    token = get_gmgn_token()
