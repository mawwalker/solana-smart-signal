import asyncio
import json
from loguru import logger
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, HTTPException, APIRouter
import websockets
import uvicorn
from utils.gmgn import get_gmgn_token
from config.conf import channel_id, access_token_dict, private_key_dict, wallet_signal_port, wallet_signal_route


class GmgnWebsocketReverse():
    def __init__(self) -> None:
        self.websocket_urls = {}
        self.update_websocket_urls()
        self.router = APIRouter()
        self.router.add_api_websocket_route(f"/{wallet_signal_route}", self.websocket_wallets_signal)
        self.tasks = []
        
    def update_websocket_urls(self):
        global access_token_dict
        for wallet_address, wallet_token in access_token_dict.items():
            if wallet_token is None:
                wallet_token = get_gmgn_token(wallet_address, private_key_dict[wallet_address])
                access_token_dict[wallet_address] = wallet_token
            websocket_url = f"wss://ws.gmgn.ai/stream?tk={wallet_token}"
            self.websocket_urls[wallet_address] = websocket_url
            
    async def websocket_wallets_signal(self, ws_local: WebSocket):
        await ws_local.accept()
        remote_connections = {}
        this_connection_urls = self.websocket_urls
        while True:
            try:
                # 尝试建立一个新的测试连接
                for wallet_address, websocket_url in this_connection_urls.items():
                    try:
                        connect_test = await websockets.connect(websocket_url)
                        logger.info(f"Connection test successed.")
                        await connect_test.close()
                    except Exception as e:
                        logger.warning("Connection test failed, will attempt to reconnect all services.")
                        raise Exception("Test connection failed: reconnecting...")
                # 判断ws_local是否关闭
                if ws_local.client_state == 2:
                    logger.info("Local WebSocket disconnected. Reconnecting...")
                    break
                if len(self.tasks) == 0:
                    for wallet_address, websocket_url in self.websocket_urls.items():
                        try:
                            remote_conn = await websockets.connect(websocket_url)
                            remote_connections[wallet_address] = remote_conn
                        except Exception as e:
                            raise HTTPException(status_code=500, detail=f"Failed to connect to remote WebSocket {websocket_url}: {str(e)}")
                    tasks = []
                    for wallet_address, remote_conn in remote_connections.items():
                        rev_task = asyncio.create_task(reverse(ws_local, remote_conn))
                        tasks.append(rev_task)
                    forward_task = asyncio.create_task(forward(ws_local, remote_connections))
                    tasks.append(forward_task)
                    self.tasks = tasks
                    await asyncio.gather(*tasks)
                # 如果有一个task出现异常，就重新连接
                for task in self.tasks:
                    if task.done() or task.exception():
                        raise Exception("Task done, reconnecting...")
            except Exception as e:
                self.update_websocket_urls()
                self.tasks = []
                continue
            await asyncio.sleep(3)
                
    
    def run_server(self):
        app = FastAPI()
        app.include_router(self.router)
        app_config = uvicorn.Config(app, host="0.0.0.0", port=int(wallet_signal_port))
        server = uvicorn.Server(app_config)
        loop = asyncio.get_event_loop()
        loop.create_task(server.serve())
        loop.run_forever()


async def forward(ws_local: WebSocket, remote_connections):
    try:
        async for message in ws_local.iter_json():
            logger.info(f"Local WebSocket received:{message}")
            message = json.dumps(message)
            for wallet_address, remote_conn in remote_connections.items():
                await remote_conn.send(message)
                logger.info(f"Remote WebSocket sent:{message}")
    except Exception as e:
        logger.info(f"Forwarding error: {e}")

async def reverse(ws_local: WebSocket, ws_b: websockets.WebSocketClientProtocol):
    try:
        async for message in ws_b:
            message = json.loads(message)
            await ws_local.send_json(message)
            logger.info(f"Local WebSocket sent:{message}")
    except Exception as e:
        logger.info(f"Reversing error: {e}")
        
if __name__ == "__main__":
    gmgn_reverse = GmgnWebsocketReverse()
    gmgn_reverse.run_server()
