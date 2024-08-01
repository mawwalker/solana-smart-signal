import asyncio
import json
from loguru import logger
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, HTTPException, APIRouter
import websockets
import uuid
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
        # update_websocket_task = asyncio.create_task(self._update_websocket_urls())
        # self.tasks.append(update_websocket_task)
        
    def update_websocket_urls(self):
        # 更新所有的websocket urls
        logger.info("Updating websocket urls...")
        global access_token_dict
        for wallet_address, wallet_token in access_token_dict.items():
            wallet_token = get_gmgn_token(wallet_address, private_key_dict[wallet_address])
            access_token_dict[wallet_address] = wallet_token
            websocket_url = f"wss://ws.gmgn.ai/stream?tk={wallet_token}"
            self.websocket_urls[wallet_address] = websocket_url
        # logger.info(f"Websocket urls updated: {self.websocket_urls}")
    async def _update_websocket_urls(self):
        '''定时更新websocket urls
        '''
        while True:
            await asyncio.sleep(60 * 30)
            try:
                self.update_websocket_urls()
            except Exception as e:
                logger.error(f"Failed to update websocket urls: {str(e)}")
            
    async def websocket_wallets_signal(self, ws_local: WebSocket):
        await ws_local.accept()
        this_connection_urls = self.websocket_urls.copy()
        tasks = []
        new_tasks = []
        
        async def create_tasks(this_connection_urls):
            nonlocal new_tasks
            new_tasks = []
            remote_connections = {}
            for wallet_address, websocket_url in this_connection_urls.items():
                remote_conn = await websockets.connect(websocket_url)
                await subscribe(remote_conn)
                remote_connections[wallet_address] = remote_conn
                rev_task = asyncio.create_task(reverse(ws_local, remote_conn))
                new_tasks.append(rev_task)
            forward_task = asyncio.create_task(forward(ws_local, remote_connections))
            new_tasks.append(forward_task)
        
        while True:
            try:
                # logger.info(f"Websocket urls: {this_connection_urls}, self.websocket_urls: {self.websocket_urls}")
                if this_connection_urls != self.websocket_urls:
                    logger.info(f"Websocket urls updated, reconnecting...")
                    this_connection_urls = self.websocket_urls.copy()
                    for task in tasks:
                        task.cancel()
                        del task
                    await create_tasks(this_connection_urls)
                    # await asyncio.gather(*new_tasks)
                    logger.info(f"New Tasks length: {len(new_tasks)}")
                    tasks = new_tasks

                if len(new_tasks) == 0:
                    for task in tasks:
                        task.cancel()
                        del task
                    await create_tasks(this_connection_urls)
                    # await asyncio.gather(*new_tasks)
                    logger.info(f"New Tasks length: {len(new_tasks)}")
                    tasks = new_tasks
                # 如果有一个task出现异常，就重新连接
                for task in self.tasks:
                    if task.done() or task.exception():
                        self.update_websocket_urls()
            except Exception as e:
                import pdb; pdb.set_trace()
                self.update_websocket_urls()
                continue
            await asyncio.sleep(3)
                
    
    def run_server(self):
        app = FastAPI()
        app.include_router(self.router)
        app_config = uvicorn.Config(app, host="0.0.0.0", port=int(wallet_signal_port))
        server = uvicorn.Server(app_config)
        loop = asyncio.get_event_loop()
        loop.create_task(self._update_websocket_urls())
        loop.create_task(server.serve())
        loop.run_forever()


async def subscribe(ws):  
    session_id = str(uuid.uuid4())  
    payload = {  
        "action": "subscribe",  
        "channel": "following_wallet_activity",  
        "id": session_id,  
        "data": {  
            "chain": "sol"  
        }  
    }  
    await ws.send(json.dumps(payload))  
    logger.info(f"Subscribed with session ID: {session_id}") 


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
