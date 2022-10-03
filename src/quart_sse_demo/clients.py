import asyncio
from dataclasses import dataclass, field

QUEUE_SIZE = 50


def _get_queue():
    return asyncio.Queue(QUEUE_SIZE)


@dataclass
class ChatClient:
    username: str
    status: str = "Online"
    queue: asyncio.Queue[dict[str, str]] = field(default_factory=_get_queue)


class ConnectedClients:
    _clients: dict[str, ChatClient] = {}

    def __setitem__(self, username: str, client: ChatClient):
        self._clients[username] = client

    def __getitem__(self, username: str) -> ChatClient | None:
        try:
            return self._clients[username]
        except KeyError:
            return None

    def __delitem__(self, username: str):
        try:
            del self._clients[username]
        except KeyError:
            pass

    def __iter__(self):
        for username in self._clients:
            yield self._clients[username]

    async def update_status(self, username: str, status: str) -> tuple[bool, dict]:
        status_update = {"type": "status_update", "sender": username, "content": status}
        try:
            self._clients[username].status = status
        except KeyError:
            print(self._clients)
            return False, status_update

        for client in self._clients:
            if self._clients[client].username == username:
                continue
            await self._clients[client].queue.put(status_update)
        return True, status_update

    async def new_message(self, username: str, message: str) -> tuple[bool, dict]:
        _message = {"type": "message", "sender": username, "content": message}
        try:
            self._clients[username]
        except KeyError:
            return False, _message

        for client in self._clients:
            await self._clients[client].queue.put(_message)
        return True, _message
