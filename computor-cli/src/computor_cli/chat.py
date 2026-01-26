"""
WebSocket chat CLI for testing real-time messaging.

Usage:
    computor chat -c submission_group:uuid
    computor chat --channel course:uuid --listen-only
"""

import asyncio
import json
import click
from typing import List, Optional

from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig


class ChatClient:
    """Interactive WebSocket chat client."""

    def __init__(self, api_url: str, access_token: str, channel: str):
        self.api_url = api_url.rstrip('/')
        self.access_token = access_token
        self.channel = channel  # Single active channel
        self.running = True
        self.ws = None
        self._composing = False  # Track if user is composing a message

    @property
    def ws_url(self) -> str:
        url = self.api_url
        # Remove /api suffix if present (WebSocket is at root, not under /api)
        if url.endswith("/api"):
            url = url[:-4]
        elif url.endswith("/api/"):
            url = url[:-5]
        url = url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{url}/ws?token={self.access_token}"

    async def connect(self):
        """Connect to WebSocket and subscribe to channel."""
        try:
            import websockets
        except ImportError:
            click.echo("Error: websockets package required. Install with: pip install websockets")
            return False

        click.echo(f"[debug] Connecting to: {self.ws_url.split('?')[0]}?token=***")

        try:
            self.ws = await websockets.connect(self.ws_url)
            click.echo(f"[connected] WebSocket connected")

            # Subscribe to channel
            await self.ws.send(json.dumps({
                "type": "channel:subscribe",
                "channels": [self.channel]
            }))
            click.echo(f"[subscribe] Subscribing to: {self.channel}")

            return True
        except Exception as e:
            click.echo(f"[error] Connection failed: {e}")
            return False

    async def listen(self):
        """Listen for incoming WebSocket messages."""
        try:
            while self.running and self.ws:
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    data = json.loads(message)
                    self._handle_message(data)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    if self.running:
                        click.echo(f"[error] WebSocket error: {e}")
                    break
        except Exception as e:
            if self.running:
                click.echo(f"[error] Listen error: {e}")

    async def ping_loop(self):
        """Send keep-alive pings every 25 seconds."""
        while self.running and self.ws:
            try:
                await asyncio.sleep(25)
                if self.ws:
                    await self.ws.send(json.dumps({"type": "system:ping"}))
            except Exception:
                break

    def _handle_message(self, data: dict):
        """Handle and display incoming messages."""
        msg_type = data.get("type", "")

        if msg_type == "system:connected":
            click.echo(f"[system] Connected as user: {data.get('user_id')}")

        elif msg_type == "channel:subscribed":
            channels = data.get("channels", [])
            click.echo(f"[subscribed] {', '.join(channels)}")

        elif msg_type == "channel:error":
            click.echo(f"[error] Channel {data.get('channel')}: {data.get('reason')}")

        elif msg_type == "message:new":
            self._display_new_message(data)

        elif msg_type == "message:update":
            click.echo(f"[updated] Message {data.get('message_id')}")

        elif msg_type == "message:delete":
            click.echo(f"[deleted] Message {data.get('message_id')}")

        elif msg_type == "typing:update":
            user = data.get("user_name") or data.get("user_id", "Someone")
            if data.get("is_typing"):
                click.echo(f"[typing] {user} is typing...")

        elif msg_type == "read:update":
            click.echo(f"[read] User {data.get('user_id')} read message {data.get('message_id')}")

        elif msg_type == "system:pong":
            pass  # Silent pong

        elif msg_type == "system:error":
            click.echo(f"[error] {data.get('code')}: {data.get('message')}")

        else:
            click.echo(f"[{msg_type}] {json.dumps(data)}")

    def _display_new_message(self, data: dict):
        """Display a new message nicely."""
        msg_data = data.get("data", {})

        message_id = msg_data.get("id", "")
        author = msg_data.get("author", {})
        author_name = None
        if author:
            given = author.get("given_name", "")
            family = author.get("family_name", "")
            author_name = f"{given} {family}".strip() or author.get("id", "Unknown")

        title = msg_data.get("title", "")
        content = msg_data.get("content", "")

        click.echo("")
        click.echo(f"┌─ NEW MESSAGE [{message_id[:8]}...]")
        click.echo(f"│ From: {author_name}")
        if title:
            click.echo(f"│ Title: {title}")
        click.echo(f"│ {content}")
        click.echo(f"│ (Use /read {message_id} to mark as read)")
        click.echo("└─")

    async def send_message(self, title: str, content: str) -> bool:
        """Send a message via REST API."""
        import httpx

        # Parse channel to get target field
        parts = self.channel.split(":", 1)
        if len(parts) != 2:
            click.echo(f"[error] Invalid channel format: {self.channel}")
            return False

        scope, target_id = parts
        target_field = f"{scope}_id"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json={
                        target_field: target_id,
                        "title": title,
                        "content": content
                    },
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                if response.status_code in (200, 201):
                    click.echo(f"[sent] Message sent")
                    return True
                else:
                    click.echo(f"[error] Send failed: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                click.echo(f"[error] Send error: {e}")
                return False

    async def _send_typing(self, is_typing: bool):
        """Send typing indicator."""
        if self.ws:
            await self.ws.send(json.dumps({
                "type": "typing:start" if is_typing else "typing:stop",
                "channel": self.channel
            }))

    async def input_loop(self):
        """Interactive input for sending messages."""
        loop = asyncio.get_event_loop()

        click.echo("")
        click.echo("─" * 50)
        click.echo(f"Chat ready. Channel: {self.channel}")
        click.echo("Commands:")
        click.echo("  /send                     - compose (with typing indicator)")
        click.echo("  /send <title> | <content> - quick send")
        click.echo("  /read <message_id>        - mark message as read")
        click.echo("  /quit")
        click.echo("─" * 50)
        click.echo("")

        while self.running:
            try:
                line = await loop.run_in_executor(None, lambda: input("> "))
                line = line.strip()

                if not line:
                    continue

                if line == "/quit" or line == "/q":
                    self.running = False
                    break

                elif line == "/send":
                    await self._handle_send()

                elif line.startswith("/send "):
                    await self._handle_quick_send(line[6:])

                elif line.startswith("/read "):
                    await self._handle_read_mark(line[6:].strip())

                else:
                    click.echo("Unknown command. Use /send, /read, or /quit")

            except EOFError:
                self.running = False
                break
            except KeyboardInterrupt:
                self.running = False
                break

    async def _handle_send(self):
        """Handle /send command - interactive compose with typing indicator."""
        loop = asyncio.get_event_loop()
        self._composing = True

        # Start background typing indicator refresh
        typing_task = asyncio.create_task(self._typing_refresh_loop())

        try:
            # Get title
            title = await loop.run_in_executor(None, lambda: input("Title: "))
            if not title.strip():
                click.echo("[cancelled]")
                self._composing = False
                typing_task.cancel()
                await self._send_typing(False)
                return

            # Get content
            click.echo("Content (Enter twice to send):")
            lines = []
            while True:
                line = await loop.run_in_executor(None, lambda: input())
                if line == "":
                    if lines:  # Empty line after content = send
                        break
                    else:  # Empty line with no content = cancel
                        click.echo("[cancelled]")
                        self._composing = False
                        typing_task.cancel()
                        await self._send_typing(False)
                        return
                lines.append(line)

            content = "\n".join(lines)

            # Stop typing
            self._composing = False
            typing_task.cancel()
            await self._send_typing(False)

            # Send the message
            if content.strip():
                await self.send_message(title.strip(), content.strip())
            else:
                click.echo("[cancelled] No content")

        except KeyboardInterrupt:
            click.echo("\n[cancelled]")
            self._composing = False
            typing_task.cancel()
            await self._send_typing(False)

    async def _typing_refresh_loop(self):
        """Send typing indicator every second while composing."""
        try:
            while self._composing:
                await self._send_typing(True)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def _handle_quick_send(self, args: str):
        """Handle /send <title> | <content> - quick send without typing indicator."""
        if "|" not in args:
            click.echo("Usage: /send <title> | <content>")
            return

        title, content = args.split("|", 1)
        title = title.strip()
        content = content.strip()

        if not title or not content:
            click.echo("Usage: /send <title> | <content>")
            return

        await self.send_message(title, content)

    async def _handle_read_mark(self, message_id: str):
        """Handle /read <message_id> - mark a message as read via WebSocket."""
        if not message_id:
            click.echo("Usage: /read <message_id>")
            return

        if not self.ws:
            click.echo("[error] Not connected")
            return

        # Send read:mark event via WebSocket
        await self.ws.send(json.dumps({
            "type": "read:mark",
            "channel": self.channel,
            "message_id": message_id
        }))
        click.echo(f"[read:mark] Sent for message: {message_id}")

    async def run(self, listen_only: bool = False):
        """Main run loop."""
        if not await self.connect():
            return

        tasks = [
            asyncio.create_task(self.listen()),
            asyncio.create_task(self.ping_loop()),
        ]

        if not listen_only:
            tasks.append(asyncio.create_task(self.input_loop()))

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if self.ws:
                await self.ws.close()
            click.echo("\n[disconnected] Chat closed")


async def _run_chat(auth: CLIAuthConfig, channel: str, listen_only: bool):
    """Async entry point for chat."""
    # Get authenticated client to obtain access token
    client = await get_computor_client(auth)

    # Extract access token from client's auth provider
    access_token = await client._auth_provider.get_access_token()

    if not access_token:
        click.echo("Error: Could not obtain access token. Try logging in again.")
        return

    chat = ChatClient(auth.api_url, access_token, channel)
    await chat.run(listen_only=listen_only)


@click.command()
@click.option(
    "--channel", "-c",
    required=True,
    help="Channel to connect to (e.g., submission_group:uuid)"
)
@click.option(
    "--listen-only", "-l",
    is_flag=True,
    default=False,
    help="Only listen for messages, don't show input prompt."
)
@authenticate
def chat(channel: str, listen_only: bool, auth: CLIAuthConfig):
    """
    Interactive WebSocket chat for testing real-time messaging.

    Examples:

        computor chat -c submission_group:abc123

        computor chat -c submission_group:abc --listen-only
    """
    if not channel:
        click.echo("Channel required. Use -c/--channel to specify.")
        click.echo("Example: computor chat -c submission_group:your-uuid")
        return

    try:
        asyncio.run(_run_chat(auth, channel, listen_only))
    except KeyboardInterrupt:
        click.echo("\nInterrupted")
