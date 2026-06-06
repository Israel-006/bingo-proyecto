import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import PartidaBingo

class BingoConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.id_partida = self.scope['url_route']['kwargs']['id_partida']
        self.id_bingo = await self.obtener_id_bingo(self.id_partida)

        if not self.id_bingo:
            await self.close()
            return

        self.group_partida = f'bingo_partida_{self.id_partida}'
        self.group_tienda = f'bingo_tienda_{self.id_bingo}'
        self.group_chat = f'bingo_chat_{self.id_bingo}'

        await self.channel_layer.group_add(self.group_partida, self.channel_name)
        await self.channel_layer.group_add(self.group_tienda, self.channel_name)
        await self.channel_layer.group_add(self.group_chat, self.channel_name)

        await self.accept()

        # MAGIA: Presencia Automática al Conectar
        cedula = self.scope["user"].username if self.scope["user"].is_authenticated else "Invitado"
        if cedula != "Invitado":
            self.alias_seguro = await self.registrar_conexion(cedula, self.id_partida)
            if self.alias_seguro:
                await self.channel_layer.group_send(
                    self.group_partida,
                    {
                        'type': 'evento_presencia',
                        'accion': 'entrar',
                        'alias': self.alias_seguro
                    }
                )
        else:
            self.alias_seguro = "Invitado"

    async def disconnect(self, close_code):
        if hasattr(self, 'group_partida'):
            # MAGIA: Presencia Automática al Desconectar
            if hasattr(self, 'alias_seguro') and self.alias_seguro and self.alias_seguro != "Invitado":
                cedula = self.scope["user"].username
                await self.registrar_desconexion(cedula, self.id_partida)
                
                await self.channel_layer.group_send(
                    self.group_partida,
                    {
                        'type': 'evento_presencia',
                        'accion': 'salir',
                        'alias': self.alias_seguro
                    }
                )

            await self.channel_layer.group_discard(self.group_partida, self.channel_name)
            await self.channel_layer.group_discard(self.group_tienda, self.channel_name)
            await self.channel_layer.group_discard(self.group_chat, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo_evento = data.get('tipo')

        if tipo_evento == 'chat':
            cedula = self.scope["user"].username if self.scope["user"].is_authenticated else "Invitado"
            if cedula != "Invitado":
                alias_seguro = await self.obtener_alias_jugador(cedula)
            else:
                alias_seguro = "Invitado"
            
            await self.guardar_historial_chat(self.id_bingo, alias_seguro, data['mensaje'])
            await self.channel_layer.group_send(
                self.group_chat,
                {'type': 'evento_chat', 'mensaje': data['mensaje'], 'usuario': alias_seguro}
            )
            
        # ==========================================
        # NUEVO: MEGÁFONO DEL ADMINISTRADOR
        # ==========================================
        elif tipo_evento == 'admin_broadcast':
            # Medida de Seguridad: Solo el personal Staff puede disparar esta alerta
            if self.scope["user"].is_staff:
                await self.channel_layer.group_send(
                    self.group_partida,
                    {
                        'type': 'evento_partida',
                        'datos': {
                            'evento': 'alerta_admin',
                            'mensaje': data['mensaje']
                        }
                    }
                )
        
        # ==========================================
        # NUEVO: RECLAMO DE BINGO (FASE 2)
        # ==========================================
        elif tipo_evento == 'reclamo_bingo':
            cedula = self.scope["user"].username
            alias_jugador = await self.obtener_alias_jugador(cedula)
            codigo_carton = data.get('codigo_carton', 'DESCONOCIDO')

            await self.channel_layer.group_send(
                self.group_partida,
                {
                    'type': 'evento_partida',
                    'datos': {
                        'evento': 'alerta_reclamo',
                        'alias': alias_jugador,
                        'codigo': codigo_carton
                    }
                }
            )

    async def evento_chat(self, event):
        await self.send(text_data=json.dumps({'canal': 'chat', 'usuario': event['usuario'], 'mensaje': event['mensaje']}))

    async def evento_partida(self, event):
        await self.send(text_data=json.dumps({'canal': 'partida', 'datos': event['datos']}))

    async def evento_tienda(self, event):
        await self.send(text_data=json.dumps({'canal': 'tienda', 'datos': event['datos']}))

    # CANAL EXCLUSIVO PARA PRESENCIA
    async def evento_presencia(self, event):
        await self.send(text_data=json.dumps({'canal': 'presencia', 'accion': event['accion'], 'alias': event['alias']}))

    @database_sync_to_async
    def obtener_id_bingo(self, id_partida):
        try: return PartidaBingo.objects.get(idpartidabingo=id_partida).idbingo_id
        except PartidaBingo.DoesNotExist: return None
        
    @database_sync_to_async
    def obtener_alias_jugador(self, username):
        from .models import Jugador
        try: return Jugador.objects.get(cedulaidentidadjugador=username).aliasjugador
        except: return username 

    # ==========================================
    # NUEVOS MOTORES DE BASE DE DATOS (PRESENCIA)
    # ==========================================
    @database_sync_to_async
    def registrar_conexion(self, cedula, id_partida):
        from .models import Jugador, SesionJuego, PlataformaJuego, PartidaBingo
        from django.utils import timezone
        import uuid
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            partida = PartidaBingo.objects.get(idpartidabingo=id_partida)
            plataforma, _ = PlataformaJuego.objects.get_or_create(
                nombreplataforma='Web Oficial', defaults={'urlplataforma': '/', 'estadoplataforma': True}
            )
            # Limpiamos las sesiones anteriores que se hayan quedado colgadas
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(estadosesion='Finalizada', fechafinsesion=timezone.now())
            # Registramos la nueva entrada
            SesionJuego.objects.create(
                idplataforma=plataforma, idjugador=jugador, idpartida=partida,
                fechainiciosesion=timezone.now(), ipconexion='WebSocket', dispositivoconexion='Conexión En Vivo',
                estadosesion='Activa', navegadorweb='Socket de Juego', tokenconexion=str(uuid.uuid4())
            )
            return jugador.aliasjugador
        except Exception:
            return None

    @database_sync_to_async
    def registrar_desconexion(self, cedula, id_partida):
        from .models import Jugador, SesionJuego
        from django.utils import timezone
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            SesionJuego.objects.filter(idjugador=jugador, idpartida_id=id_partida, estadosesion='Activa').update(
                estadosesion='Finalizada', fechafinsesion=timezone.now(), motivocierre='Salió de la Sala'
            )
        except Exception:
            pass

    @database_sync_to_async
    def guardar_historial_chat(self, id_bingo, alias, texto):
        from .models import Bingo, MensajeChat
        try:
            bingo = Bingo.objects.get(idbingo=id_bingo)
            # 1. Guardamos el mensaje nuevo
            MensajeChat.objects.create(idbingo=bingo, usuario=alias, mensaje=texto)
            
            # 2. LIMPIEZA AUTOMÁTICA: Si hay más de 50, borramos los más viejos
            if MensajeChat.objects.filter(idbingo=bingo).count() > 50:
                ids_a_guardar = MensajeChat.objects.filter(idbingo=bingo).order_by('-fechahora')[:50].values_list('idmensaje', flat=True)
                MensajeChat.objects.filter(idbingo=bingo).exclude(idmensaje__in=list(ids_a_guardar)).delete()
        except Exception:
            pass

# =========================================================
# NUEVO: CONSUMIDOR EXCLUSIVO PARA LA TIENDA DE CARTONES
# =========================================================
class TiendaConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        # 1. Atrapamos el ID del Bingo (Evento Matriz) desde la URL
        self.id_bingo = self.scope['url_route']['kwargs']['id_bingo']
        self.group_tienda = f'bingo_tienda_{self.id_bingo}'

        # 2. Inscribimos el navegador del comprador al grupo de la tienda
        await self.channel_layer.group_add(self.group_tienda, self.channel_name)
        
        # 3. Le abrimos la puerta al WebSocket (Aquí desaparece tu error 404)
        await self.accept()

    async def disconnect(self, close_code):
        # Cuando el comprador cierra la tienda, lo sacamos del grupo
        await self.channel_layer.group_discard(self.group_tienda, self.channel_name)

    # El megáfono: Recibe el grito desde views.py y se lo pasa al JavaScript
    async def evento_tienda(self, event):
        # Extraemos 'datos' y lo enviamos al JS (para que haga la animación de desaparecer)
        await self.send(text_data=json.dumps(event['datos']))

