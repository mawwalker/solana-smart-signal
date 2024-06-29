import os

from dotenv import load_dotenv

load_dotenv()

# 从环境变量中获取私钥和钱包地址
private_key_base58 = os.getenv('PRIVATE_KEY_BASE58')
wallet_address = os.getenv('WALLET_ADDRESS')

PRIVATE_KEY_BASE58_LIST = os.getenv('PRIVATE_KEY_BASE58_LIST').split(',')
WALLET_ADDRESS_LIST = os.getenv('WALLET_ADDRESS_LIST').split(',')

access_token_dict = {}
private_key_dict = {}

for private_key, wallet_address in zip(PRIVATE_KEY_BASE58_LIST, WALLET_ADDRESS_LIST):
    access_token_dict[wallet_address] = None
    private_key_dict[wallet_address] = private_key
    

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

time_zone = os.getenv('TIMEZONE')

channel_id = int(os.getenv('CHANNEL_ID'))

admin_list = os.getenv('ADMIN_LIST').split(',')


max_market_cap = float(os.getenv('MAX_MARKET_CAP', 200000))

min_market_cap = float(os.getenv('MIN_MARKET_CAP', 0))

filter_in_launch_pad = int(os.getenv('FILTER_IN_LAUNCH_PAD', 0))


DATABASE_FILE = "data/subscriptions.db"

if os.path.dirname(DATABASE_FILE) and not os.path.exists(os.path.dirname(DATABASE_FILE)):
    os.makedirs(os.path.dirname(DATABASE_FILE))


