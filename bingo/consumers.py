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
        
        # El Admin entra como espectador silencioso
        if usuario.is_authenticated and usuario.is_staff:
            self.alias_seguro = None
            self.sesion_id = None
            return 

        # Registro inteligente de sesión
        cedula = usuario.username if usuario.is_authenticated else "Invitado"
        if cedula != "Invitado":
            resultado = await self.registrar_conexion(cedula, self.id_partida)
            if resultado and resultado[0]:
                self.alias_seguro = resultado[0]
                self.sesion_id = resultado[1] # Guardamos el ID único de ESTA pestaña
                
                lista_activos = await self.obtener_lista_completa_activos()
                await self.channel_layer.group_send(
                    self.group_partida,
                    {
                        'type': 'evento_presencia',
                        'lista_jugadores': lista_activos
                    }
                )
        else:
            self.alias_seguro = "Invitado"
            self.sesion_id = None

    async def disconnect(self, close_code):
        if hasattr(self, 'group_partida'):
            usuario = self.scope["user"]
            
            if usuario.is_authenticated and not usuario.is_staff:
                if hasattr(self, 'alias_seguro') and self.alias_seguro and self.alias_seguro != "Invitado":
                    cedula = usuario.username
                    sesion_id = getattr(self, 'sesion_id', None)
                    
                    # Le decimos que SOLO finalice esta sesión específica
                    await self.registrar_desconexion(cedula, self.id_partida, sesion_id)
                    
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
            
        elif tipo_evento == 'admin_broadcast':
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

        elif tipo_evento == 'marcar_casilla':
            carton_codigo = data.get('carton_codigo')
            numero = data.get('numero')
            
            cedula = self.scope["user"].username if self.scope["user"].is_authenticated else "Invitado"
            if cedula == "Invitado": return 
                
            @database_sync_to_async
            def procesar_marcado(c_cedula, c_codigo, c_numero, c_partida):
                try:
                    from .models import Jugador
                    from .services import marcar_casilla_manual
                    jugador = Jugador.objects.get(cedulaidentidadjugador=c_cedula)
                    return marcar_casilla_manual(jugador.idjugador, c_codigo, c_numero, c_partida)
                except Exception as e:
                    return False

            exito = await procesar_marcado(cedula, carton_codigo, numero, self.id_partida)
            
            if exito:
                await self.send(text_data=json.dumps({
                    'canal': 'partida',
                    'datos': {
                        'evento': 'casilla_marcada_ok',
                        'carton': carton_codigo,
                        'numero': numero
                    }
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
    def obtener_alias_jugador(self, username):
        from .models import Jugador
        try: return Jugador.objects.get(cedulaidentidadjugador=username).aliasjugador
        except: return username 

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
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(estadosesion='Finalizada', fechafinsesion=timezone.now())
            
            sesion = SesionJuego.objects.create(
                idplataforma=plataforma, idjugador=jugador, idpartida=partida,
                fechainiciosesion=timezone.now(), ipconexion='127.0.0.1', dispositivoconexion='Conexión En Vivo',
                estadosesion='Activa', navegadorweb='Socket de Juego', tokenconexion=str(uuid.uuid4())
            )
            # AHORA RETORNAMOS EL ID DE LA SESIÓN
            return jugador.aliasjugador, sesion.idsesionjuego 
        except Exception:
            return None, None

    @database_sync_to_async
    def registrar_desconexion(self, cedula, id_partida, sesion_id=None):
        from .models import Jugador, SesionJuego
        from django.utils import timezone
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            if sesion_id:
                # SI TENEMOS EL ID, SOLO MATAMOS ESA PESTAÑA
                SesionJuego.objects.filter(idsesionjuego=sesion_id, estadosesion='Activa').update(
                    estadosesion='Finalizada', fechafinsesion=timezone.now(), motivocierre='Salió de la Sala'
                )
            else:
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
# CONSUMIDOR TIENDA (AHORA ARREGLADO Y BLINDADO)
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

        cedula = self.scope["user"].username if self.scope["user"].is_authenticated else "Invitado"
        if cedula != "Invitado":
            resultado = await self.registrar_conexion(cedula, self.id_partida)
            if resultado and resultado[0]:
                self.alias_seguro = resultado[0]
                self.sesion_id = resultado[1]
                
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
            cedula = self.scope["user"].username if self.scope["user"].is_authenticated else "Invitado"
            if cedula != "Invitado":
                sesion_id = getattr(self, 'sesion_id', None)
                await self.registrar_desconexion(cedula, self.id_partida, sesion_id)
                
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

    # Agregamos estos receptores para que no crashee cuando BingoConsumer hable
    async def evento_tienda(self, event):
        await self.send(text_data=json.dumps({'canal': 'tienda', 'datos': event['datos']}))

    async def evento_presencia(self, event):
        await self.send(text_data=json.dumps({'canal': 'presencia', 'lista_jugadores': event['lista_jugadores']}))

    async def evento_partida(self, event):
        await self.send(text_data=json.dumps({'canal': 'partida', 'datos': event['datos']}))

    async def evento_chat(self, event):
        await self.send(text_data=json.dumps({'canal': 'chat', 'usuario': event['usuario'], 'mensaje': event['mensaje']}))

    # Helper methods
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
            plataforma, _ = PlataformaJuego.objects.get_or_create(
                nombreplataforma='Web Oficial', defaults={'urlplataforma': '/', 'estadoplataforma': True}
            )
            SesionJuego.objects.filter(idjugador=jugador, idpartida=partida, estadosesion='Activa').update(estadosesion='Finalizada', fechafinsesion=timezone.now())
            sesion = SesionJuego.objects.create(
                idplataforma=plataforma, idjugador=jugador, idpartida=partida,
                fechainiciosesion=timezone.now(), ipconexion='127.0.0.1', dispositivoconexion='Conexión Tienda',
                estadosesion='Activa', navegadorweb='Socket Tienda', tokenconexion=str(uuid.uuid4())
            )
            return jugador.aliasjugador, sesion.idsesionjuego
        except Exception:
            return None, None

    @database_sync_to_async
    def registrar_desconexion(self, cedula, id_partida, sesion_id=None):
        from .models import Jugador, SesionJuego
        from django.utils import timezone
        try:
            jugador = Jugador.objects.get(cedulaidentidadjugador=cedula)
            if sesion_id:
                SesionJuego.objects.filter(idsesionjuego=sesion_id, estadosesion='Activa').update(
                    estadosesion='Finalizada', fechafinsesion=timezone.now(), motivocierre='Salió de la Sala'
                )
            else:
                SesionJuego.objects.filter(idjugador=jugador, idpartida_id=id_partida, estadosesion='Activa').update(
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