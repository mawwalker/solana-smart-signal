import aiosqlite
import os
import pandas as pd
from loguru import logger
from config.conf import DATABASE_FILE


async def create_tables():
    logger.info("Creating tables...")
    async with aiosqlite.connect(DATABASE_FILE) as db:  
        await db.execute('''  
            CREATE TABLE IF NOT EXISTS token_notify (  
                id INTEGER PRIMARY KEY,  
                token_id TEXT NOT NULL,
                notify_time DATETIME NOT NULL
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS send_trade (
                id INTEGER PRIMARY KEY,
                token_id TEXT NOT NULL,
                trade_amount REAL NOT NULL,
                is_monitor INTEGER NOT NULL, -- comment '0: no, 1: yes',
                trade_type INTEGER NOT NULL, -- comment '0: buy, 1: sell',
                trade_time DATETIME NOT NULL
            )
        ''')
        
        await db.commit()

async def insert_token_notify(token_id, notify_time):  
    async with aiosqlite.connect(DATABASE_FILE) as db:  
        await db.execute('''  
            INSERT INTO token_notify (token_id, notify_time) VALUES (?, ?)  
        ''', (token_id, notify_time))  
        await db.commit()

async def get_token_notify(token_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:  
        async with db.execute('''  
            SELECT * FROM token_notify WHERE token_id = ?  
        ''', (token_id,)) as cursor:  
            return await cursor.fetchall()
        
        
async def insert_send_trade(token_id, trade_amount, is_monitor, trade_type, trade_time):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            INSERT INTO send_trade (token_id, trade_amount, is_monitor, trade_type, trade_time) VALUES (?, ?, ?, ?, ?)
        ''', (token_id, trade_amount, is_monitor, trade_type, trade_time))
        await db.commit()

async def get_send_trade(token_id, is_monitor=0, trade_type=0):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        sql = f'''
        SELECT * FROM send_trade WHERE token_id = '{token_id}' AND is_monitor = '{is_monitor}' AND trade_type = '{trade_type}'
        '''
        async with db.execute(sql) as cursor:
            trade_history = await cursor.fetchall()
            return trade_history