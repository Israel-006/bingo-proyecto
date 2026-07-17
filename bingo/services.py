import random, ast, uuid, json
from django.contrib.auth.models import User
from django.db import transaction
from django.core.files.storage import default_storage 
from .models import Socio, Jugador, TipoSocio, CartonPartidaBingo

def generar_matriz_bingo():
    Carton = {
        'B': random.sample(range(1, 16), 5),
        'I': random.sample(range(16, 31), 5),
        'N': random.sample(range(31, 46), 5),
        'G': random.sample(range(46, 61), 5),
        'O': random.sample(range(61, 76), 5)
    }
    Carton['N'][2] = "FREE" 
    return Carton

def generar_lote_cartones(cantidad):
    nuevos_cartones = []
    firmas_existentes = set()

    while len(nuevos_cartones) < cantidad:
        matriz = generar_matriz_bingo()
        firma = tuple(
            matriz['B'] + matriz['I'] + 
            [matriz['N'][0], matriz['N'][1], matriz['N'][3], matriz['N'][4]] + 
            matriz['G'] + matriz['O']
        )
        if firma not in firmas_existentes:
            firmas_existentes.add(firma)
            serial_unico = f"CTN-{str(uuid.uuid4())[:8].upper()}"
            nuevos_cartones.append({
                'codigo': serial_unico,
                'matriz': matriz
            })
    return nuevos_cartones


# =========================================================
# GESTIÓN DE PERFILES, BORRADO LÓGICO Y CREDENCIALES
# =========================================================

def actualizar_socio_y_credenciales(id_socio, cedula, nombres, apellidos, telefono, estado, id_tipo_socio, password_nueva=None):
    with transaction.atomic():
        socio = Socio.objects.select_for_update().get(idsocio=id_socio)
        estado_antiguo = socio.estadosocio
        cedula_antigua = socio.cisocio

        tipo_socio_obj = TipoSocio.objects.get(idtiposocio=id_tipo_socio)
        user = None
        if estado_antiguo == 'Activo':
            user = User.objects.filter(username=cedula_antigua).first()
        else:
            user = User.objects.filter(username=f"inactivo_{socio.idsocio}_{cedula_antigua}"[:150]).first()

        socio.cisocio = cedula
        socio.primernombresocio = nombres
        socio.primerapellidosocio = apellidos
        socio.telefonopersonalsocio = telefono
        socio.estadosocio = estado
        socio.idtiposocio = tipo_socio_obj
        socio.save()

        if user:
            if estado == 'Inactivo':
                prefijo = f"inactivo_{socio.idsocio}_"
                if not user.username.startswith(prefijo):
                    user.username = f"{prefijo}{cedula}"[:150]
                    if user.email and not user.email.startswith(prefijo):
                        user.email = f"{prefijo}{user.email}"[:254]
                user.is_active = False
            else:
                user.username = cedula
                prefijo = f"inactivo_{socio.idsocio}_"
                if user.email and user.email.startswith(prefijo):
                    user.email = user.email.replace(prefijo, "", 1)
                user.is_active = True
            
            if password_nueva:
                user.set_password(password_nueva)
            user.save()


def actualizar_jugador_y_credenciales(id_jugador, alias, cedula, correo, estado, password_nueva=None):
    with transaction.atomic():
        jugador = Jugador.objects.select_for_update().get(idjugador=id_jugador)
        estado_antiguo = jugador.estadocuentajugador
        cedula_antigua = jugador.cedulaidentidadjugador
        
        user = None
        if cedula_antigua:
            if estado_antiguo == 'Activo':
                user = User.objects.filter(username=cedula_antigua).first()
            else:
                user = User.objects.filter(username=f"inactivo_j{jugador.idjugador}_{cedula_antigua}"[:150]).first()

        jugador.aliasjugador = alias
        jugador.cedulaidentidadjugador = cedula
        jugador.correojugador = correo
        jugador.estadocuentajugador = estado
        jugador.save()

        if user:
            if estado in ['Suspendido', 'Moroso']:
                prefijo = f"inactivo_j{jugador.idjugador}_"
                if not user.username.startswith(prefijo):
                    user.username = f"{prefijo}{cedula}"[:150]
                    if user.email and not user.email.startswith(prefijo):
                        user.email = f"{prefijo}{correo}"[:254]
                user.is_active = False
            else:
                user.username = cedula
                if correo:
                    user.email = correo
                prefijo = f"inactivo_j{jugador.idjugador}_"
                if user.email and user.email.startswith(prefijo):
                    user.email = user.email.replace(prefijo, "", 1)
                user.is_active = True
            
            if password_nueva:
                user.set_password(password_nueva)
            user.save()


def actualizar_avatar_perfil(request, socio, jugador, nueva_foto):
    avatar_url = None
    
    if jugador:
        if jugador.avatarjugador and default_storage.exists(jugador.avatarjugador.name):
            default_storage.delete(jugador.avatarjugador.name)
        jugador.avatarjugador = nueva_foto
        jugador.save()
        avatar_url = jugador.avatarjugador.url
        
    if socio:
        if socio.fotosocio and default_storage.exists(socio.fotosocio.name):
            default_storage.delete(socio.fotosocio.name)
        socio.fotosocio = nueva_foto
        socio.save()
        if not jugador:
            avatar_url = socio.fotosocio.url
            
    if avatar_url:
        request.session['avatar_url'] = avatar_url
    return True

# =========================================================
# LÓGICA DE AUDITORÍA Y PATRONES DE BINGO (ÁRBITRO DIGITAL)
# =========================================================

def auditar_patron_bingo(matriz, bolas_llamadas, modalidad):
    """
    Escáner matricial: Mapea el cartón en un array y 
    verifica todas las combinaciones (rotaciones e inversiones).
    """
    # 1. Aplanar el carton a un array de 25 celdas
    celdas = []
    for i in range(5):
        celdas.extend([matriz['B'][i], matriz['I'][i], matriz['N'][i], matriz['G'][i], matriz['O'][i]])
        
    # Aseguramos que las bolas cantadas sean comparadas como strings
    bolas_str = [str(b).strip() for b in bolas_llamadas]

    # 2. Diccionario Maestro de Patrones (Incluye giros y espejos permitidos)
    patrones = {
        'Tabla Llena': [[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24]],
        'Las Cuatro Esquinas': [[0, 4, 20, 24]],
        'En Diagonal': [[0, 6, 12, 18, 24], [4, 8, 12, 16, 20]],
        'Forma de X': [[0, 4, 6, 8, 12, 16, 18, 20, 24]],
        'Forma de Cruz': [[2, 7, 10, 11, 12, 13, 14, 17, 22]],
        'Marco de Foto': [[0,1,2,3,4, 5,9, 10,14, 15,19, 20,21,22,23,24]],
        'Linea Vertical': [
            [0, 5, 10, 15, 20], [1, 6, 11, 16, 21], [2, 7, 12, 17, 22], [3, 8, 13, 18, 23], [4, 9, 14, 19, 24]
        ],
        'Forma de L': [
            [0, 5, 10, 15, 20, 21, 22, 23, 24], 
            [0, 1, 2, 3, 4, 5, 10, 15, 20],     
            [0, 1, 2, 3, 4, 9, 14, 19, 24],     
            [20, 21, 22, 23, 24, 19, 14, 9, 4]  
        ],
        'Forma de C': [
            [0, 1, 2, 3, 4, 5, 10, 15, 20, 21, 22, 23, 24], # C normal
            [0, 1, 2, 3, 4, 9, 14, 19, 24, 20, 21, 22, 23], # C invertida
            [0, 5, 10, 15, 20, 21, 22, 23, 24, 4, 9, 14, 19], # U (C hacia arriba)
            [20, 15, 10, 5, 0, 1, 2, 3, 4, 9, 14, 19, 24]  # n (C hacia abajo)
        ],
        'Forma de U': [
            [0, 5, 10, 15, 20, 21, 22, 23, 24, 4, 9, 14, 19], # U normal
            [20, 15, 10, 5, 0, 1, 2, 3, 4, 9, 14, 19, 24], # n (U invertida)
            [0, 1, 2, 3, 4, 5, 10, 15, 20, 21, 22, 23, 24], # C (U acostada)
            [0, 1, 2, 3, 4, 9, 14, 19, 24, 20, 21, 22, 23]  # C invertida
        ],
        'Forma de T': [
            [0,1,2,3,4, 7, 12, 17, 22], 
            [20,21,22,23,24, 17, 12, 7, 2], 
            [4,9,14,19,24, 13, 12, 11, 10], 
            [0,5,10,15,20, 11, 12, 13, 14]  
        ],
        'Forma de H': [
            [0, 5, 10, 15, 20, 11, 12, 13, 4, 9, 14, 19, 24], 
            [0, 1, 2, 3, 4, 7, 12, 17, 20, 21, 22, 23, 24]       
        ],
        'Forma de Z': [
            [0,1,2,3,4, 8, 12, 16, 20,21,22,23,24], 
            [0,1,2,3,4, 6, 12, 18, 20,21,22,23,24], 
            [4,9,14,19,24, 18, 12, 6, 0,5,10,15,20], 
            [0,5,10,15,20, 16, 12, 8, 4,9,14,19,24]  
        ],
        'Forma de Flecha': [
            [2, 6, 8, 12, 17, 22],   
            [22, 16, 18, 12, 7, 2],  
            [10, 6, 16, 12, 13, 14], 
            [14, 8, 18, 12, 11, 10]  
        ]
    }
    
    # FIX: Busqueda robusta e insensible a mayúsculas para evitar el fallback a "Tabla Llena"
    modalidad_limpia = str(modalidad).strip().lower()
    patrones_lower = {k.lower(): v for k, v in patrones.items()}
    marcadas_requeridas = patrones_lower.get(modalidad_limpia, patrones_lower['tabla llena'])
    
    # 3. Validar si CUALQUIERA de las orientaciones válidas se cumple
    for opcion in marcadas_requeridas:
        es_ganador_opcion = True
        for idx in opcion:
            if idx == 12: 
                continue # El centro (FREE) siempre es comodín válido
            if str(celdas[idx]).strip() not in bolas_str:
                es_ganador_opcion = False
                break
        if es_ganador_opcion:
            return True # ¡Bingo! Encontró una orientación ganadora
            
    return False

def validar_carton_hibrido(codigo_carton, id_partida):
    """
    Árbitro Digital 'Smart Hybrid'
    Diferencia entre jugadores activos en la web (exige clics) y jugadores externos (exige matemática pura).
    """
    import json
    try:
        asignacion = CartonPartidaBingo.objects.select_related('idcarton', 'idpartida', 'idjugador').get(
            idcarton__codigocarton=codigo_carton,
            idpartida_id=id_partida
        )
        
        partida = asignacion.idpartida
        matriz = asignacion.idcarton.matriznumeros
        modalidad_ronda = getattr(partida, 'modalidad_victoria', 'Tabla Llena')

        bolas_str = partida.bolascantadas.replace('B','').replace('I','').replace('N','').replace('G','').replace('O','')
        bolas_oficiales = [str(b.strip()) for b in bolas_str.split(',') if b.strip().isdigit()]
        
        # 1. FILTRO ABSOLUTO: Verificamos si el cartón sirve matemáticamente con las bolas de la mesa
        es_ganador_matematico = auditar_patron_bingo(matriz, bolas_oficiales, modalidad_ronda)
        
        if not es_ganador_matematico:
            return {'existe': True, 'valido': False, 'mensaje': 'El cartón no cumple el patrón ganador con las bolas actuales.'}

        # 2. FILTRO INTELIGENTE: Diferenciar Web vs Zoom
        if asignacion.idjugador:
            from .models import SesionJuego
            # Verificamos si el dueño del cartón tiene la pestaña abierta AHORA MISMO
            esta_conectado_web = SesionJuego.objects.filter(
                idjugador=asignacion.idjugador,
                idpartida=partida,
                estadosesion='Activa'
            ).exists()

            if esta_conectado_web:
                # Si está en la web, LO OBLIGAMOS a tener sus casillas marcadas
                marcados_db = []
                if getattr(asignacion, 'numerosmarcados', None):
                    try: marcados_db = json.loads(asignacion.numerosmarcados)
                    except: 
                        import ast
                        try: marcados_db = ast.literal_eval(asignacion.numerosmarcados)
                        except: pass
                
                marcados_str = [str(num) for num in marcados_db]
                es_ganador_clicks = auditar_patron_bingo(matriz, marcados_str, modalidad_ronda)
                
                if not es_ganador_clicks:
                    # El jugador está online pero fue perezoso y no marcó
                    return {'existe': True, 'valido': False, 'mensaje': 'El jugador está en línea pero no ha marcado las casillas digitales requeridas.'}

        # Si pasó todos los filtros (Es de Zoom o es de Web y SÍ marcó)
        return {
            'existe': True,
            'valido': True,
            'jugador': asignacion.idjugador.aliasjugador if asignacion.idjugador else 'Jugador Anónimo',
            'origen': 'Web' if asignacion.idjugador else 'Externo',
            'id_jugador': asignacion.idjugador.idjugador if asignacion.idjugador else None
        }

    except CartonPartidaBingo.DoesNotExist:
        return {
            'existe': False,
            'valido': False,
            'mensaje': 'Código no registrado para esta ronda.'
        }
    
# Fíjate que añadimos 'partida_id' aquí en los parámetros
def marcar_casilla_manual(jugador_id, carton_codigo, numero, partida_id):
    """
    Guardia de Seguridad: Verifica que el clic del jugador sea legal en la ronda correcta.
    BLINDADO: Usa select_for_update() para evitar condiciones de carrera masivas.
    """
    from django.db import transaction
    try:
        # Iniciamos transacción atómica para que los clics del piloto automático hagan fila
        with transaction.atomic():
            # 1. Buscar el cartón en juego (BLOQUEAMOS LA FILA HASTA TERMINAR EL GUARDADO)
            asignacion = CartonPartidaBingo.objects.select_for_update().select_related('idcarton', 'idpartida').get(
                idcarton__codigocarton=carton_codigo, 
                idjugador_id=jugador_id,
                idpartida_id=partida_id  
            )
            partida = asignacion.idpartida
            
            # 2. Validar que la bola SÍ salió en la mesa del admin
            if not partida.bolascantadas:
                return False
                
            bolas_cantadas_str = partida.bolascantadas.replace('B','').replace('I','').replace('N','').replace('G','').replace('O','')
            bolas_cantadas_lista = [b.strip() for b in bolas_cantadas_str.split(',') if b.strip()]
            
            if str(numero) not in bolas_cantadas_lista:
                return False 
                
            # 3. Validar que el número SÍ existe en ese cartón
            import json, ast
            if isinstance(asignacion.idcarton.matriznumeros, str):
                try: matriz = json.loads(asignacion.idcarton.matriznumeros)
                except: matriz = ast.literal_eval(asignacion.idcarton.matriznumeros)
            else:
                matriz = asignacion.idcarton.matriznumeros
                
            numero_existe = False
            for letra in ['B', 'I', 'N', 'G', 'O']:
                if numero in matriz[letra] or str(numero) in matriz[letra]:
                    numero_existe = True
                    break
                    
            if not numero_existe:
                return False 
                
            # 4. Guardar la marca (Al estar bloqueado, no se sobreescriben los clics)
            marcados = []
            if getattr(asignacion, 'numerosmarcados', None):
                try: marcados = json.loads(asignacion.numerosmarcados)
                except: marcados = ast.literal_eval(asignacion.numerosmarcados)
                    
            if numero not in marcados and str(numero) not in marcados:
                marcados.append(numero)
                asignacion.numerosmarcados = json.dumps(marcados)
                asignacion.cantidadaciertos += 1
                asignacion.save()
                return True
            else:
                return True
                
    except Exception as e:
        print(f"Error en marcado manual: {e}")
        return False