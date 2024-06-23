# solana-wallet-tracker
A Telegram Bot for solana smart money buy/sell signals

## Pre-requisites
1. Tested on Python 3.11 or higher
2. Docker (optional)
3. Telegram Bot Token (Get it from BotFather)

## Usage

### Source Code
1. Clone the repository
2. Install the dependencies
```bash
pip install -r requirements.txt
```
3. Copy the .env_example file to .env, and fill in the required fields
4. Run the bot
```bash
python app.py
```

### Docker

1. Build the image
```bash
docker build -t matrixarcher/solana-smart-signal .
```
2. Run the container
```bash
docker run -d --name matrixarcher/solana-smart-signal solana-smart-signal
```
