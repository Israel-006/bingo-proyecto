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

        usuario = self.scope["user"]
        
        # Guardamos datos en memoria para que no se borren en el disconnect
        self.es_admin = usuario.is_staff if usuario.is_authenticated else False
        self.mi_cedula = usuario.username if usuario.is_authenticated else "Invitado"
        self.alias_seguro = "Invitado"

        if self.es_admin:
            return 

        if self.mi_cedula != "Invitado":
            self.alias_seguro = await self.registrar_conexion(self.mi_cedula, self.id_partida)
            if self.alias_seguro:
                lista_activos = await self.obtener_lista_completa_activos()
                await self.channel_layer.group_send(
                    self.group_partida,
                    {
                        'type': 'evento_presencia',
                        'lista_jugadores': lista_activos
                    }
                )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_partida'):
            # Usamos self.mi_cedula que es a prueba de balas contra cierres abruptos
            if hasattr(self, 'mi_cedula') and self.mi_cedula != "Invitado" and not getattr(self, 'es_admin', False):
                await self.registrar_desconexion(self.mi_cedula, self.id_partida)
                
                lista_activos = await self.obtener_lista_completa_activos()
                await self.channel_layer.group_send(
                    self.group_partida,
                    {
                        'type': 'evento_presencia',
                        'lista_jugadores': lista_activos
                    }
                )

            await self.channel_layer.group_discard(self.group_partida, self.channel_name)
            await self.channel_layer.group_discard(self.group_tienda, self.channel_name)
            await self.channel_layer.group_discard(self.group_chat, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo_evento = data.get('tipo')

        if tipo_evento == 'chat':
            alias_usar = getattr(self, 'alias_seguro', "Invitado")
            await self.guardar_historial_chat(self.id_bingo, alias_usar, data['mensaje'])
            await self.channel_layer.group_send(
                self.group_chat,
                {'type': 'evento_chat', 'mensaje': data['mensaje'], 'usuario': alias_usar}
            )
            
        elif tipo_evento == 'admin_broadcast':
            if getattr(self, 'es_admin', False):
                await self.channel_layer.group_send(
                    self.group_partida,
                    {'type': 'evento_partida', 'datos': {'evento': 'alerta_admin', 'mensaje': data['mensaje']}}
                )
        
        elif tipo_evento == 'reclamo_bingo':
            alias_usar = getattr(self, 'alias_seguro', "Invitado")
            codigo_carton = data.get('codigo_carton', 'DESCONOCIDO')
            await self.channel_layer.group_send(
                self.group_partida,
                {'type': 'evento_partida', 'datos': {'evento': 'alerta_reclamo', 'alias': alias_usar, 'codigo': codigo_carton}}
            )

        elif tipo_evento == 'marcar_casilla':
            carton_codigo = data.get('carton_codigo')
            numero = data.get('numero')
            
            if not hasattr(self, 'mi_cedula') or self.mi_cedula == "Invitado": return 
                
            @database_sync_to_async
            def procesar_marcado(c_cedula, c_codigo, c_numero, c_partida):
                try:
                    from .models import Jugador
                    from .services import marcar_casilla_manual
                    jugador = Jugador.objects.get(cedulaidentidadjugador=c_cedula)
                    return marcar_casilla_manual(jugador.idjugador, c_codigo, c_numero, c_partida)
                except Exception as e:
                    return False

            exito = await procesar_marcado(self.mi_cedula, carton_codigo, numero, self.id_partida)
            
            if exito:
                await self.send(text_data=json.dumps({
                    'canal': 'partida',
                    'datos': {'evento': 'casilla_marcada_ok', 'carton': carton_codigo, 'numero': numero}
                }))

    async def evento_chat(self, event):
        await self.send(text_data=json.dumps({'canal': 'chat', 'usuario': event['usuario'], 'mensaje': event['mensaje']}))

    async def evento_partida(self, event):
        await self.send(text_data=json.dumps({'canal': 'partida', 'datos': event['datos']}))

    async def evento_tienda(self, event):
        await self.send(text_data=json.dumps({'canal': 'tienda', 'datos': event['datos']}))

    async def evento_presencia(self, event):
        await self.send(text_data=json.dumps({'canal': 'presencia', 'lista_jugadores': event['lista_jugadores']}))

    @database_sync_to_async
    def obtener_id_bingo(self, id_partida):
        try: return PartidaBingo.objects.get(idpartidabingo=id_partida).idbingo_id
        except PartidaBingo.DoesNotExist: return None
        
    @database_sync_to_async
    def registrar_conexion(self, cedula, id_partida):
        from .models import Jugador, SesionJuego, PlataformaJuego, PartidaBingo
        from django.utils import timezone
        import uuid
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            partida = PartidaBingo.objects.get(idpartidabingo=id_partida)
            plataforma, _ = PlataformaJuego.objects.get_or_create(nombreplataforma='Web Oficial', defaults={'urlplataforma': '/', 'estadoplataforma': True})
            
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(estadosesion='Finalizada', fechafinsesion=timezone.now())
            
            SesionJuego.objects.create(
                idplataforma=plataforma, idjugador=jugador, idpartida=partida,
                fechainiciosesion=timezone.now(), ipconexion='127.0.0.1', dispositivoconexion='Conexión En Vivo',
                estadosesion='Activa', navegadorweb='Socket de Juego', tokenconexion=str(uuid.uuid4())
            )
            return jugador.aliasjugador
        except Exception:
            return None

    @database_sync_to_async
    def registrar_desconexion(self, cedula, id_partida):
        from .models import Jugador, SesionJuego, PartidaBingo
        from django.utils import timezone
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            partida = PartidaBingo.objects.get(idpartidabingo=id_partida)
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(
                estadosesion='Finalizada', fechafinsesion=timezone.now(), motivocierre='Salió de la Sala'
            )
        except Exception as e:
            print(f"Error en desconexion: {e}")

    @database_sync_to_async
    def guardar_historial_chat(self, id_bingo, alias, texto):
        from .models import Bingo, MensajeChat
        try:
            bingo = Bingo.objects.get(idbingo=id_bingo)
            MensajeChat.objects.create(idbingo=bingo, usuario=alias, mensaje=texto)
            if MensajeChat.objects.filter(idbingo=bingo).count() > 50:
                ids_a_guardar = MensajeChat.objects.filter(idbingo=bingo).order_by('-fechahora')[:50].values_list('idmensaje', flat=True)
                MensajeChat.objects.filter(idbingo=bingo).exclude(idmensaje__in=list(ids_a_guardar)).delete()
        except Exception:
            pass
        
    @database_sync_to_async
    def obtener_lista_completa_activos(self):
        from .models import Jugador
        jugadores = Jugador.objects.filter(
            sesionjuego__idpartida_id=self.id_partida,
            sesionjuego__estadosesion='Activa'
        ).distinct().order_by('aliasjugador')
        return [j.aliasjugador for j in jugadores]


# =========================================================
# CONSUMIDOR TIENDA (ARREGLADO)
# =========================================================
class TiendaConsumer(AsyncWebsocketConsumer):
    
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

        usuario = self.scope["user"]
        self.mi_cedula = usuario.username if usuario.is_authenticated else "Invitado"
        self.es_admin = usuario.is_staff if usuario.is_authenticated else False

        if self.es_admin: return

        if self.mi_cedula != "Invitado":
            await self.registrar_conexion(self.mi_cedula, self.id_partida)
            lista_activos = await self.obtener_lista_completa_activos()
            await self.channel_layer.group_send(
                self.group_partida,
                {'type': 'evento_presencia', 'lista_jugadores': lista_activos}
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'mi_cedula') and self.mi_cedula != "Invitado" and not getattr(self, 'es_admin', False):
            await self.registrar_desconexion(self.mi_cedula, self.id_partida)
            
            # FIX: Corregido el nombre de la función que rompía el código
            lista_activos = await self.obtener_lista_completa_activos()
            await self.channel_layer.group_send(
                self.group_partida,
                {'type': 'evento_presencia', 'lista_jugadores': lista_activos}
            )

        await self.channel_layer.group_discard(self.group_partida, self.channel_name)
        await self.channel_layer.group_discard(self.group_tienda, self.channel_name)
        await self.channel_layer.group_discard(self.group_chat, self.channel_name)

    async def evento_tienda(self, event):
        await self.send(text_data=json.dumps({'canal': 'tienda', 'datos': event['datos']}))

    async def evento_presencia(self, event):
        await self.send(text_data=json.dumps({'canal': 'presencia', 'lista_jugadores': event['lista_jugadores']}))

    async def evento_partida(self, event):
        await self.send(text_data=json.dumps({'canal': 'partida', 'datos': event['datos']}))

    async def evento_chat(self, event):
        await self.send(text_data=json.dumps({'canal': 'chat', 'usuario': event['usuario'], 'mensaje': event['mensaje']}))

    @database_sync_to_async
    def obtener_id_bingo(self, id_partida):
        try: return PartidaBingo.objects.get(idpartidabingo=id_partida).idbingo_id
        except PartidaBingo.DoesNotExist: return None

    @database_sync_to_async
    def registrar_conexion(self, cedula, id_partida):
        from .models import Jugador, SesionJuego, PlataformaJuego, PartidaBingo
        from django.utils import timezone
        import uuid
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            partida = PartidaBingo.objects.get(idpartidabingo=id_partida)
            plataforma, _ = PlataformaJuego.objects.get_or_create(nombreplataforma='Web Oficial', defaults={'urlplataforma': '/', 'estadoplataforma': True})
            
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(estadosesion='Finalizada', fechafinsesion=timezone.now())
            SesionJuego.objects.create(
                idplataforma=plataforma, idjugador=jugador, idpartida=partida,
                fechainiciosesion=timezone.now(), ipconexion='127.0.0.1', dispositivoconexion='Conexión Tienda',
                estadosesion='Activa', navegadorweb='Socket Tienda', tokenconexion=str(uuid.uuid4())
            )
            return jugador.aliasjugador
        except Exception:
            return None

    @database_sync_to_async
    def registrar_desconexion(self, cedula, id_partida):
        from .models import Jugador, SesionJuego, PartidaBingo
        from django.utils import timezone
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            partida = PartidaBingo.objects.get(idpartidabingo=id_partida)
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(
                estadosesion='Finalizada', fechafinsesion=timezone.now(), motivocierre='Salió de la Sala'
            )
        except Exception:
            pass
            
    @database_sync_to_async
    def obtener_lista_completa_activos(self):
        from .models import Jugador
        jugadores = Jugador.objects.filter(
            sesionjuego__idpartida_id=self.id_partida,
            sesionjuego__estadosesion='Activa'
        ).distinct().order_by('aliasjugador')
        return [j.aliasjugador for j in jugadores]