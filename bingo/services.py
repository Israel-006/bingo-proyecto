import random
import uuid
from django.contrib.auth.models import User
from django.db import transaction
from django.core.files.storage import default_storage 
from .models import Socio, Jugador, TipoSocio, CartonPartidaBingo

def generar_matriz_bingo():
    Carton = {
        'B': sorted(random.sample(range(1, 16), 5)),
        'I': sorted(random.sample(range(16, 31), 5)),
        'N': sorted(random.sample(range(31, 46), 5)),
        'G': sorted(random.sample(range(46, 61), 5)),
        'O': sorted(random.sample(range(61, 76), 5))
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
    Escáner matricial: Mapea el cartón en una matriz booleana de 5x5
    y verifica matemáticamente si se cumple el patrón de victoria.
    """
    columnas = ['B', 'I', 'N', 'G', 'O']
    # Grid de 5x5 lleno de False
    marcados = [[False for _ in range(5)] for _ in range(5)]
    
    # Aseguramos que las bolas cantadas sean comparadas como strings
    bolas_llamadas_str = [str(b).strip() for b in bolas_llamadas]

    # 1. PINTAR LA MATRIZ DE VERDADEROS (Aciertos)
    for col_idx, col_nombre in enumerate(columnas):
        for fila_idx in range(5):
            numero = matriz[col_nombre][fila_idx]
            if str(numero).upper() == 'FREE':
                marcados[fila_idx][col_idx] = True # Centro libre siempre es válido
            elif str(numero).strip() in bolas_llamadas_str:
                marcados[fila_idx][col_idx] = True

    # 2. VALIDACIÓN DEL PATRÓN
    if modalidad == 'Tabla Llena':
        return all(all(celda for celda in fila) for fila in marcados)
        
    elif modalidad == 'Las Cuatro Esquinas':
        return marcados[0][0] and marcados[0][4] and marcados[4][0] and marcados[4][4]
        
    elif modalidad == 'Linea Vertical':
        # Cualquiera de las 5 columnas llenas
        return any(all(marcados[fila][col] for fila in range(5)) for col in range(5))
        
    elif modalidad == 'En Diagonal':
        # Diagonal principal o inversa
        diag1 = all(marcados[i][i] for i in range(5))
        diag2 = all(marcados[i][4-i] for i in range(5))
        return diag1 or diag2
        
    elif modalidad == 'Forma de X':
        # Ambas diagonales a la vez
        diag1 = all(marcados[i][i] for i in range(5))
        diag2 = all(marcados[i][4-i] for i in range(5))
        return diag1 and diag2
        
    elif modalidad == 'Forma de Cruz':
        # Fila 3 y Columna N (Ambas cruzan en el FREE)
        fila_central = all(marcados[2][c] for c in range(5))
        col_central = all(marcados[f][2] for f in range(5))
        return fila_central and col_central
        
    elif modalidad == 'Marco de Foto':
        # Todo el borde exterior
        b_sup = all(marcados[0][c] for c in range(5))
        b_inf = all(marcados[4][c] for c in range(5))
        b_izq = all(marcados[f][0] for f in range(5))
        b_der = all(marcados[f][4] for f in range(5))
        return b_sup and b_inf and b_izq and b_der
        
    elif modalidad == 'Forma de L':
        col_izq = all(marcados[f][0] for f in range(5))
        fila_inf = all(marcados[4][c] for c in range(5))
        return col_izq and fila_inf
        
    elif modalidad == 'Forma de C':
        col_izq = all(marcados[f][0] for f in range(5))
        fila_sup = all(marcados[0][c] for c in range(5))
        fila_inf = all(marcados[4][c] for c in range(5))
        return col_izq and fila_sup and fila_inf
        
    elif modalidad == 'Forma de T':
        fila_sup = all(marcados[0][c] for c in range(5))
        col_central = all(marcados[f][2] for f in range(5))
        return fila_sup and col_central
        
    elif modalidad == 'Forma de U':
        col_izq = all(marcados[f][0] for f in range(5))
        col_der = all(marcados[f][4] for f in range(5))
        fila_inf = all(marcados[4][c] for c in range(5))
        return col_izq and col_der and fila_inf
        
    elif modalidad == 'Forma de H':
        col_izq = all(marcados[f][0] for f in range(5))
        col_der = all(marcados[f][4] for f in range(5))
        fila_central = all(marcados[2][c] for c in range(5))
        return col_izq and col_der and fila_central
        
    elif modalidad == 'Forma de Z':
        fila_sup = all(marcados[0][c] for c in range(5))
        diag_inversa = all(marcados[i][4-i] for i in range(5))
        fila_inf = all(marcados[4][c] for c in range(5))
        return fila_sup and diag_inversa and fila_inf
        
    elif modalidad == 'Forma de Flecha':
        # Punta apuntando arriba
        punta = marcados[0][2]
        alas = marcados[1][1] and marcados[1][3]
        tallo = marcados[2][2] and marcados[3][2] and marcados[4][2]
        return punta and alas and tallo
        
    return False

def validar_carton_hibrido(codigo_carton, id_partida):
    """
    Árbitro Digital Principal
    """
    try:
        asignacion = CartonPartidaBingo.objects.select_related('idcarton', 'idpartida', 'idjugador').get(
            idcarton__codigocarton=codigo_carton,
            idpartida_id=id_partida
        )
        
        partida = asignacion.idpartida
        matriz = asignacion.idcarton.matriznumeros
        
        # Limpieza de las bolas cantadas a una lista pura
        bolas_cantadas_str = partida.bolascantadas.replace('B','').replace('I','').replace('N','').replace('G','').replace('O','')
        bolas_cantadas_lista = [b.strip() for b in bolas_cantadas_str.split(',') if b.strip()]
        
        # OBTENEMOS LA MODALIDAD Y ENVIAMOS A AUDITAR
        modalidad_ronda = getattr(partida, 'modalidad_victoria', 'Tabla Llena')
        es_valido = auditar_patron_bingo(matriz, bolas_cantadas_lista, modalidad_ronda)
        
        return {
            'existe': True,
            'valido': es_valido,
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