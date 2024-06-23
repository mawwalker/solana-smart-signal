import os

from dotenv import load_dotenv

load_dotenv()

# 从环境变量中获取私钥和钱包地址
private_key_base58 = os.getenv('PRIVATE_KEY_BASE58')
wallet_address = os.getenv('WALLET_ADDRESS')

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

time_zone = os.getenv('TIMEZONE')

channel_id = int(os.getenv('CHANNEL_ID'))

DATABASE_FILE = "data/subscriptions.db"

if os.path.dirname(DATABASE_FILE) and not os.path.exists(os.path.dirname(DATABASE_FILE)):
    os.makedirs(os.path.dirname(DATABASE_FILE))
    

# 记录钱包购买记录的表结构
wallet_records_table_schema = '''
CREATE TABLE IF NOT EXISTS wallet_records (
    id INTEGER PRIMARY KEY,
    wallet_address TEXT NOT NULL comment '钱包地址',
    token_address TEXT NOT NULL comment '代币地址',
    trade_state INTEGER NOT NULL comment '交易状态, 0新买，1清仓，2加仓，3减仓',
    cost_sol REAL NOT NULL,
    date_time TEXT NOT NULL
        '''