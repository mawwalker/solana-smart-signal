import asyncio
import json
import uuid
import datetime
from loguru import logger
import traceback
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosedError
from config.conf import access_token_dict, private_key_dict
from utils.gmgn import get_gmgn_token
import config.conf as configuration
from config.conf import (
    user_agent,
    access_token_dict,
    private_key_dict,
    wallet_signal_port,
)


class GmgnWebsocketReverse:
    def __init__(self):
        self.websocket_urls = {}
        self.update_websocket_urls()
        self.remote_connections = {}
        self.local_connections = {}

    def update_websocket_urls(self):
        """更新所有的 websocket URLs"""
        logger.info("Updating websocket URLs...")
        for wallet_address, wallet_token in access_token_dict.items():
            wallet_token = get_gmgn_token(wallet_address, private_key_dict[wallet_address])
            access_token_dict[wallet_address] = wallet_token
            websocket_url = f"wss://ws.gmgn.ai/stream?tk={wallet_token}"
            self.websocket_urls[wallet_address] = websocket_url
        self.update_time = datetime.datetime.now()
        
    async def _schedule_cancel_all_tasks(self):
        """定时取消所有任务，用于更新url"""
        logger.info("Start to schedule cancel all tasks")
        while True:
            await asyncio.sleep(60 * 60)
            try:
                for connection_id, connection in self.local_connections.items():
                    tasks = connection["tasks"]
                    for task in tasks["reverse"]:
                        task.cancel()
                    tasks["forward"].cancel()
                    logger.info(f"Cancelled all tasks for connection {connection_id}")
                
                # 清空self.local_connections
                self.local_connections.clear()
            except Exception as e:
                traceback.print_exc()

    async def handle_local_connection(self, local_ws):
        """处理本地 WebSocket 连接，接收并转发消息"""
        logger.info("Local WebSocket connected.")
        connection_id = str(uuid.uuid4())
        while True:
            try:
                now_time = datetime.datetime.now()
                if (now_time - self.update_time).seconds > 60 * 5:
                    logger.info("Websocket URLs need to be updated, updating now...")
                    self.update_websocket_urls()
                this_connection_urls = self.websocket_urls.copy()
                # 建立远程 WebSocket 连接
                await self.create_remote_connections(this_connection_urls)
                # 启动正向和反向任务
                connection_tasks = {
                    "forward": asyncio.create_task(self.forward(local_ws)),
                    "reverse": [asyncio.create_task(self.reverse(local_ws, wallet_address, remote_ws)) 
                                for wallet_address, remote_ws in self.remote_connections.items()]
                }
                self.local_connections[connection_id] = {
                    "local_ws": local_ws,
                    "remote_connections": self.remote_connections,
                    "tasks": connection_tasks
                }
                # 等待所有任务结束
                # await asyncio.gather(connection_tasks["forward"], *connection_tasks['reverse'])
                tasks = connection_tasks["reverse"] + [connection_tasks["forward"]]
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    logger.info(f"Cancel task {task}")
                    task.cancel()
                if connection_id in self.local_connections:
                    self.local_connections.pop(connection_id)
                
                logger.info(f"All tasks finished for connection {connection_id}")
            except Exception as e:
                traceback.print_exc()
                await asyncio.sleep(2)

    async def create_remote_connections(self, this_connection_urls):
        """为每个钱包地址创建远程WebSocket连接"""
        logger.info(f"Creating remote connections for {this_connection_urls.keys()}")
        for wallet_address, websocket_url in this_connection_urls.items():
            try:
                configuration.sessions[wallet_address].get(
                    "https://gmgn.ai/defi/quotation/v1/chains/sol/gas_price",
                    impersonate="chrome120",
                )
                cookie = configuration.sessions[wallet_address].cookies.get_dict()
                additional_headers = {}
                additional_headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in cookie.items()])
                remote_conn = await ws_connect(websocket_url, origin="https://gmgn.ai", additional_headers=additional_headers, user_agent_header=user_agent)
                self.remote_connections[wallet_address] = remote_conn
                subscribe(remote_conn)
                logger.info(f"Connected to remote WebSocket ({wallet_address})")
            except Exception as e:
                logger.error(f"Failed to connect to {websocket_url}: {str(e)}")

    async def forward(self, local_ws):
        """处理本地到远程 WebSocket 的消息转发"""
        logger.info("Forward WebSocket task started")
        try:
            async for message in local_ws:
                logger.info(f"Local WebSocket received: {message}")
                # import pdb; pdb.set_trace()
                message_json = json.dumps(message) if isinstance(message, dict) else message
                for wallet_address, remote_conn in self.remote_connections.items():
                    await remote_conn.send(message_json)
                    logger.info(f"Forwarded message to remote WebSocket ({wallet_address}): {message_json}")
        except ConnectionClosedError as e:
            logger.error(f"Local WebSocket connection closed: {str(e)}")

    async def reverse(self, local_ws, wallet_address, remote_conn):
        """处理远程到本地 WebSocket 的消息转发"""
        logger.info(f"Reverse WebSocket task started for {wallet_address}")
        try:
            async for message in remote_conn:
                logger.info(f"Remote WebSocket ({wallet_address}) received: {message}")
                message_json = json.loads(message)
                await local_ws.send(json.dumps(message_json))
                logger.info(f"Sent message to local WebSocket: {message_json}")
        except ConnectionClosedError as e:
            logger.error(f"Remote WebSocket ({wallet_address}) connection closed: {str(e)}")


async def websocket_server(reverse_proxy: GmgnWebsocketReverse):
    """启动 WebSocket 服务器"""
    async def handler(websocket):
        await reverse_proxy.handle_local_connection(websocket)

    # 创建定时任务_schedule_cancel_all_tasks
    asyncio.create_task(reverse_proxy._schedule_cancel_all_tasks())

    logger.info(f"Starting WebSocket server on ws://localhost:{wallet_signal_port}")
    async with serve(handler, "0.0.0.0", int(wallet_signal_port)):
        await asyncio.Future()  # 保持服务器运行


def subscribe(remote_conn):
    """订阅 WebSocket 频道"""
    session_id = str(uuid.uuid4())
    payload = {
        "action": "subscribe",
        "channel": "following_wallet_activity",
        "id": session_id,
        "data": {"chain": "sol"},
    }
    asyncio.create_task(remote_conn.send(json.dumps(payload)))
    logger.info(f"Subscribed with session ID: {session_id}")


if __name__ == "__main__":
    reverse_proxy = GmgnWebsocketReverse()
    asyncio.run(websocket_server(reverse_proxy))
