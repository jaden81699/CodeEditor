"""
ASGI config for CodeEditor project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

# myproject/asgi.py
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from CodeEditor import consumers  # adjust the import according to your app name

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CodeEditor.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter([
        path("ws/java/", consumers.JavaLanguageServerConsumer.as_asgi()),
    ]),
})