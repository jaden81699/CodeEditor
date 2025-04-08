# myapp/consumers.py
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer


class JavaLanguageServerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection.
        await self.accept()

        # Spawn the Java language server process.
        # Adjust the command and arguments as needed for your setup.
        self.process = await asyncio.create_subprocess_exec(
            'java', '-jar', '/Users/jaden/Documents/Spring 2025/CS 595/jdt-language-server-1.45.0-202501221836.tar.gz',
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Start a background task to read from the language server’s stdout.
        self.stdout_task = asyncio.create_task(self.forward_stdout())

    async def disconnect(self, close_code):
        # Cancel the reading task and terminate the language server.
        if hasattr(self, 'stdout_task'):
            self.stdout_task.cancel()
        if hasattr(self, 'process'):
            self.process.terminate()
            await self.process.wait()

    async def receive(self, text_data):
        # Forward any incoming message from the client to the language server's stdin.
        if self.process and self.process.stdin:
            self.process.stdin.write(text_data.encode())
            await self.process.stdin.drain()

    async def forward_stdout(self):
        # Continuously read from the language server's stdout and send data to the client.
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                # Send the language server response back over the WebSocket.
                await self.send(line.decode())
        except asyncio.CancelledError:
            # Task was cancelled on disconnect.
            pass
