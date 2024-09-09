import os

from dotenv import load_dotenv

load_dotenv()

from curl_cffi import requests
session = requests.Session()
cookie = None
user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 从环境变量中获取私钥和钱包地址

PRIVATE_KEY_BASE58_LIST = os.getenv('PRIVATE_KEY_BASE58_LIST').split(',')
WALLET_ADDRESS_LIST = os.getenv('WALLET_ADDRESS_LIST').split(',')

access_token_dict = {}
private_key_dict = {}
following_wallets_nums = {}
sessions = {}

for private_key, wallet_address in zip(PRIVATE_KEY_BASE58_LIST, WALLET_ADDRESS_LIST):
    access_token_dict[wallet_address] = None
    private_key_dict[wallet_address] = private_key
    following_wallets_nums[wallet_address] = 0
    sessions[wallet_address] = requests.Session()


bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

time_zone = os.getenv('TIMEZONE')

channel_id = int(os.getenv('CHANNEL_ID'))

admin_list = os.getenv('ADMIN_LIST').split(',')
admin_list = [int(admin) for admin in admin_list]

if_filter = int(os.getenv('IF_FILTER', 1))
min_buy_wallets = int(os.getenv('MIN_BUY_WALLETS', 0))
max_market_cap = float(os.getenv('MAX_MARKET_CAP', 0))
min_market_cap = float(os.getenv('MIN_MARKET_CAP', 0))
# 过滤创建时间，单位min
max_ceate_time = int(os.getenv('MAX_CEATE_TIME', 0))

filter_dex_socials = int(os.getenv('FILTER_DEX_SOCIALS', 0))
filter_dex_ads = int(os.getenv('FILTER_DEX_ADS', 0))

filter_in_launch_pad = int(os.getenv('FILTER_IN_LAUNCH_PAD', 0))

# 是否重复推送
repeat_push = int(os.getenv('REPEAT_PUSH', 1))

# 发送交易，-1表示不发送，1表示模拟发送，0表示真实发送
trade_monitor = int(os.getenv('TRADE_TYPE', -1))

strategy = int(os.getenv('STRATEGY', -1))


dbot_token = os.getenv('DBOT_TOKEN')
dbot_wallet_id = os.getenv('DBOT_WALLET_ID', None)

wallet_signal_server = os.getenv('WALLET_SIGNAL_SERVER', 'localhost')
wallet_signal_port = int(os.getenv('WALLET_SIGNAL_PORT', 8000))
wallet_signal_route = os.getenv('WALLET_SIGNAL_ROUTE', '/wallet_signal')

DATABASE_FILE = "data/data.db"

if os.path.dirname(DATABASE_FILE) and not os.path.exists(os.path.dirname(DATABASE_FILE)):
    os.makedirs(os.path.dirname(DATABASE_FILE))


