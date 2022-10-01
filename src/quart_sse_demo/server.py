import asyncio
from dataclasses import dataclass

from quart import Quart, abort, jsonify, make_response, render_template, request
from quart.helpers import stream_with_context

from .clients import ChatClient, ConnectedClients

app = Quart(__name__)
app.clients = ConnectedClients()


@dataclass
class ServerSentEvent:
    """Helper class for formatting SSE messages."""

    data: str
    event: str | None = None
    id: int | None = None
    retry: int | None = None

    def encode(self) -> bytes:
        # remove newlines in case data is a rendered template
        self.data = self.data.replace("\n", "")
        message = f"data: {self.data}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\r\n\r\n"
        return message.encode("utf-8")


async def get_event(data: dict) -> ServerSentEvent:
    if data["type"] == "status_update":
        status, username = data["content"], data["sender"]
        html = await render_template(
            "status_partial.jinja", status=status, username=username
        )
        event = ServerSentEvent(html, event="status_update")
    elif data["type"] == "message":
        message, sender = data["content"], data["sender"]
        html = await render_template(
            "message_partial.jinja", message=message, sender=sender
        )
        event = ServerSentEvent(html, event="new_message")
    return event


@app.route("/<username>", methods=["GET"])
async def index(username: str):
    return await render_template(
        "base.html",
        username=username,
        clients=app.clients,
        status="Online",
    )


@app.route("/<username>/status", methods=["PUT"])
async def update_status(username: str):
    data = await request.get_json()
    updated, status_update = await app.clients.update_status(username, data["status"])
    if updated:
        return f'Chatting as {username}, Status: {data["status"]}'
    return jsonify(updated)


@app.route("/<username>/message", methods=["PUT"])
async def message(username: str):
    data = await request.get_json()
    updated, msg = await app.clients.new_message(username, data["message"])
    app.logger.info(updated, msg)
    return jsonify(updated)


@app.route("/sse")
async def sse():

    if "text/event-stream" not in request.accept_mimetypes:
        abort(400)

    username = request.args.get("username", None)
    if not username:
        abort(400)

    app.clients[username] = ChatClient(username)
    app.clients.update_status(username, "Online")
    app.logger.info(f"Add client {username}")

    # decorator needed to call render_template()
    @stream_with_context
    async def send_events():
        while True:
            try:
                # Give control back to event loop if nothing in queue
                data = await app.clients[username].queue.get()
                event = await get_event(data)
                yield event.encode()
            except asyncio.CancelledError:
                app.logger.info("Removing Client")
                del app.clients[username]
                break
            except RuntimeError:
                print("HERE")
                continue

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Transfer-Encoding": "chunked",
    }
    response = await make_response(send_events(), headers)
    # Allow the connection to stay open indefinitely
    response.timeout = None
    return response
