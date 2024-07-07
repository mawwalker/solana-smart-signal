import requests
import json
from loguru import logger
from config.conf import dbot_token


def get_wallet_id(dbot_token, chain="solana"):
    url = f"https://api-bot-v1.dbotx.com/account/wallets?type={chain}"
    header = {
        "Content-Type": "application/json",
        "X-API-KEY": dbot_token
    }
    
    wallet_info = requests.get(url, headers=header)
    wallet_info = wallet_info.json()
    logger.info(f"Get wallet info: {wallet_info}")
    
    err = wallet_info.get("err", True)
    if err:
        logger.error(f"Get wallet info error: {wallet_info}")
        return []
    wallet_list = wallet_info.get("res", [])
    wallet_ids = []
    for wallet in wallet_list:
        wallet_ids.append(wallet.get("id"))
    
    
    return wallet_ids

def dbot_swap(wallet_id, token_address, dbot_token, amountOrPercent, swap_type='buy', chain="solana", retries=2):
    url = f"https://api-bot-v1.dbotx.com/automation/swap_order"
    header = {
        "Content-Type": "application/json",
        "X-API-KEY": dbot_token
    }
    
    
    data = { 
        "chain": chain, 
        "pair": token_address, 
        "walletId": wallet_id, 
        "type": swap_type, 
        "amountOrPercent": amountOrPercent,
        "priorityFee": "", 
        # "gasFeeDelta": 5, # for EVM
        # "maxFeePerGas": 100, # for EVM
        "jitoEnabled": True, 
        "jitoTip": 0.001, 
        "maxSlippage": 0.5, 
        "concurrentNodes": 2, 
        "retries": retries
    }
    
    result = requests.post(url, headers=header, json=data)
    
    result = result.json()
    
    logger.info(f"Swap result: {result}")
    
    err = result.get("err", True)
    if err:
        logger.error(f"Swap error: {result}")
        return False
    return True


def dbot_simulate_swap(wallet_id, token_address, dbot_token, amountOrPercent=0.2, swap_type='buy', chain="solana"):
    url = f"https://api-bot-v1.dbotx.com/simulator/sim_swap_order"
    header = {
        "Content-Type": "application/json",
        "X-API-KEY": dbot_token
    }
    
    
    data = { 
        "chain": chain, 
        "pair": token_address, 
        "walletId": wallet_id, 
        "type": swap_type, 
        "amountOrPercent": amountOrPercent,
        "priorityFee": "", 
        # "gasFeeDelta": 5, # for EVM
        # "maxFeePerGas": 100, # for EVM
        "slippage": 0.5
    }
    
    result = requests.post(url, headers=header, json=data)
    
    result = result.json()
    
    logger.info(f"Simulate swap result: {result}")
    
    err = result.get("err", True)
    if err:
        logger.error(f"Simulate swap error: {result}")
        return False
    return True