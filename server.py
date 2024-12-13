import tornado.web
import tornado.websocket
import tornado.ioloop
import redis.asyncio as redis

# Список подключенных клиентов
connected_clients = []

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True  # Разрешаем подключения с любого источника

    async def open(self):
        print("New client connected")
        connected_clients.append(self)
        self.redis = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Подписываемся на канал сообщений Redis
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("chat_room")

        # Запускаем обработку сообщений из Redis
        tornado.ioloop.IOLoop.current().spawn_callback(self.listen_to_redis)

    async def listen_to_redis(self):
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                print(f"Received message from Redis: {message['data']}")
                # Отправляем сообщение всем подключенным клиентам
                for client in connected_clients:
                    await client.write_message(message["data"])

    async def on_message(self, message):
        print(f"Received message from client: {message}")
        # Публикуем сообщение в Redis
        await self.redis.publish("chat_room", message)

    async def on_close(self):
        print("Client disconnected")
        connected_clients.remove(self)
        # Отписываемся от канала сообщений Redis
        await self.pubsub.unsubscribe("chat_room")
        await self.pubsub.close()

def make_app():
    return tornado.web.Application([
        (r"/ws", WebSocketHandler),  # Изменено на /ws
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("WebSocket server started on ws://localhost:8888/ws")
    tornado.ioloop.IOLoop.current().start()