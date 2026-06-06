from django.urls import re_path
from bingo import consumers 

websocket_urlpatterns = [
    # Captura el ID de la partida directamente desde la URL del WebSocket
    re_path(r'ws/juego/(?P<id_partida>\w+)/$', consumers.BingoConsumer.as_asgi()),
    #El canal de la Tienda (Nivel Bingo Matriz)
    re_path(r'ws/tienda/(?P<id_bingo>\w+)/$', consumers.TiendaConsumer.as_asgi()),
]