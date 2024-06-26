import os

from dotenv import load_dotenv

load_dotenv()

# 从环境变量中获取私钥和钱包地址
private_key_base58 = os.getenv('PRIVATE_KEY_BASE58')
wallet_address = os.getenv('WALLET_ADDRESS')

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

time_zone = os.getenv('TIMEZONE')

channel_id = int(os.getenv('CHANNEL_ID'))


max_market_cap = float(os.getenv('MAX_MARKET_CAP', 200000))

min_market_cap = float(os.getenv('MIN_MARKET_CAP', 0))

filter_in_launch_pad = int(os.getenv('FILTER_IN_LAUNCH_PAD', 0))


DATABASE_FILE = "data/subscriptions.db"

if os.path.dirname(DATABASE_FILE) and not os.path.exists(os.path.dirname(DATABASE_FILE)):
    os.makedirs(os.path.dirname(DATABASE_FILE))


