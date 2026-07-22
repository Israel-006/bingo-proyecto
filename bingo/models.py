from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

# Create your models here.
class TipoSocio(models.Model):
    idtiposocio = models.AutoField(primary_key=True)
    nombretiposocio = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Nombre del Tipo de Socio"
    )
    roltiposocio = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Rol del Socio"
    )
    descripciondetiposocio = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        verbose_name="Descripción"
    )
    
    def __str__(self):
        return f"{self.nombretiposocio} ({self.roltiposocio})"

    class Meta:
        db_table = 'TipoSocio'
        verbose_name = 'Tipo de Socio'
        verbose_name_plural = 'Tipos de Socio'

def validarfechanacimiento(value):
    hoy = date.today()
    if value > hoy:
        raise ValidationError('La fecha de nacimiento no puede ser una fecha futura.')
    hace100anios = hoy.year - 100
    if value.year < hace100anios:
        raise ValidationError(f'La fecha de nacimiento es demasiado antigua (Límite: {hace100anios}).')

def validar_cedula_ecuatoriana(cedula):
    if not cedula or not cedula.isdigit() or len(cedula) != 10:
        raise ValidationError('La cédula debe tener exactamente 10 dígitos numéricos para ser válida en Ecuador.')
    
    provincia = int(cedula[:2])
    if provincia < 1 or (provincia > 24 and provincia != 30):
        raise ValidationError('Código de provincia inválido.')
    
    tercer_digito = int(cedula[2])
    if tercer_digito >= 6:
        raise ValidationError('Tercer dígito inválido para personas naturales.')
    
    # Validación con Algoritmo Módulo 10
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = sum(
        (int(cedula[i]) * coeficientes[i]) - 9 if (int(cedula[i]) * coeficientes[i]) >= 10 else (int(cedula[i]) * coeficientes[i])
        for i in range(9)
    )
    
    digito_verificador = (10 - (total % 10)) % 10
    if digito_verificador != int(cedula[9]):
        raise ValidationError('La cédula ecuatoriana ingresada no es válida.')

class Socio(models.Model):
    SEXO_CHOICES = [
        ('H', 'Hombre'),
        ('M', 'Mujer'),
    ]
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Pendiente', 'Pendiente'),
        ('Inactivo', 'Inactivo'),
    ]
    idsocio = models.AutoField(primary_key=True)
    idtiposocio = models.ForeignKey(
        'TipoSocio', 
        on_delete=models.PROTECT, 
        db_column='idtiposocio',
        verbose_name="Tipo de Socio"
    )
    primernombresocio = models.CharField(max_length=40, verbose_name="Primer Nombre")
    segundonombresocio = models.CharField(max_length=40, null=True, blank=True, verbose_name="Segundo Nombre")
    primerapellidosocio = models.CharField(max_length=40, verbose_name="Primer Apellido")
    segundoapellidosocio = models.CharField(max_length=40, verbose_name="Segundo Apellido")
    nacionalidad = models.CharField(max_length=50, default='Ecuatoriana', verbose_name="Nacionalidad")
    correosocio = models.EmailField(max_length=200, unique=True, null=True, blank=True, verbose_name="Correo Electrónico")
    cisocio = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[validar_cedula_ecuatoriana], # AQUÍ ESTÁ LA MAGIA
        verbose_name="Cédula de Identidad"
    )
    foto_cedula_frontal = models.ImageField(upload_to='media/socio/cedula/frontal/', null=True, blank=True, verbose_name="Foto Cédula Frontal")
    foto_cedula_trasera = models.ImageField(upload_to='media/socio/cedula/trasera/', null=True, blank=True, verbose_name="Foto Cédula Trasera")
    fotosocio = models.ImageField(
        upload_to='media/socio/foto/', 
        null=True, 
        blank=True, 
        verbose_name="Avatar/Foto"
    )  
    fechanacimientosocio = models.DateField(
        validators=[validarfechanacimiento],
        verbose_name="Fecha de Nacimiento",
        help_text="El socio no puede ser mayor de 100 años ni haber nacido en el futuro."
    )
    telefonopersonalsocio = models.CharField(max_length=10, verbose_name="Teléfono Personal")
    telefonotrabajosocio = models.CharField(max_length=25, null=True, blank=True, verbose_name="Teléfono Trabajo")
    direcciondomiciliosocio = models.CharField(max_length=255, verbose_name="Dirección Domicilio")
    direcciontrabajosocio = models.CharField(max_length=255, null=True, blank=True, verbose_name="Dirección Trabajo")
    sexosocio = models.CharField(
        max_length=1, 
        choices=SEXO_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name="Sexo"
    )
    estadosocio = models.CharField(
        max_length=10, 
        choices=ESTADO_CHOICES, 
        default='Activo', 
        verbose_name="Estado"
    )

    def __str__(self):
        return f"{self.primerapellidosocio} {self.primernombresocio} - {self.cisocio}"

    class Meta:
        db_table = 'Socio'
        verbose_name = 'Socio'
        verbose_name_plural = 'Socios'

class CuentaBancaria(models.Model):
    TIPO_CUENTA_CHOICES = [
        ('Ahorro', 'Ahorro'),
        ('Corriente', 'Corriente'),
    ]
    ESTADO_CUENTA_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    idcuentabancaria = models.AutoField(primary_key=True)
    idsocio = models.ForeignKey(
        'Socio', 
        on_delete=models.PROTECT, 
        db_column='idsocio',
        verbose_name="Socio Titular"
    )   
    nombrebanco = models.CharField(max_length=100, verbose_name="Nombre del Banco")
    numerocuenta = models.CharField(max_length=30, unique=True, verbose_name="Número de Cuenta")    
    tipocuenta = models.CharField(
        max_length=20, 
        choices=TIPO_CUENTA_CHOICES, 
        verbose_name="Tipo de Cuenta"
    )  
    esprincipal = models.BooleanField(
        default=False, 
        verbose_name="¿Es cuenta principal?"
    )  
    fecharegistro = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de Registro"
    )
    estadocuenta = models.CharField(
        max_length=10, 
        choices=ESTADO_CUENTA_CHOICES, 
        default='Activo', 
        verbose_name="Estado de la Cuenta"
    )

    def clean(self):
        super().clean()
        if self._state.adding:
            cantidadcuentas = CuentaBancaria.objects.filter(idsocio=self.idsocio).count()
            if cantidadcuentas >= 2:
                raise ValidationError(
                    "Bloqueo de seguridad: El socio ya tiene el límite máximo de 2 cuentas bancarias registradas."
                )
    
    def __str__(self):
        return f"{self.nombrebanco} - {self.numerocuenta} (Socio ID: {self.idsocio_id})"

    class Meta:
        db_table = 'CuentaBancaria'
        verbose_name = 'Cuenta Bancaria'
        verbose_name_plural = 'Cuentas Bancarias'
        constraints = [
            models.UniqueConstraint(
                fields=['idsocio'], 
                condition=Q(esprincipal=True), 
                name='uq_cuentabancaria_esprincipal_por_socio'
            )
        ]

class MetodoPago(models.Model):
    ESTADO_METODO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    idmetodopago = models.AutoField(primary_key=True)
    nombremetodopago = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nombre del Método de Pago"
    )   
    descripcionmetodopago = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        verbose_name="Descripción del Método"
    )    
    estadometodopago = models.CharField(
        max_length=20, 
        choices=ESTADO_METODO_CHOICES, 
        default='Activo', 
        verbose_name="Estado del Método"
    )    
    urlmetodopago = models.CharField(
        max_length=255, 
        verbose_name="URL o Enlace del Método"
    )

    def __str__(self):
        return f"{self.nombremetodopago} ({self.estadometodopago})"

    class Meta:
        db_table = 'MetodoPago'
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'

class Prestamo(models.Model):
    ESTADO_PRESTAMO_CHOICES = [
        ('Solicitado', 'Solicitado'),
        ('Aprobado', 'Aprobado'),
        ('En Curso', 'En Curso (Pagando)'),
        ('Liquidado', 'Liquidado'),
    ]
    idprestamo = models.AutoField(primary_key=True)    
    idsocio = models.ForeignKey(
        'Socio', 
        on_delete=models.PROTECT, 
        db_column='idsocio',
        related_name='prestamos_solicitados',
        verbose_name="Socio Solicitante"
    )
    idgarante1 = models.ForeignKey(
        'Socio', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_column='idgarante1',
        related_name='garantias_primarias',
        verbose_name="Garante Auxiliar si socio no paga"
    )
    idgarante2 = models.ForeignKey(
        'Socio', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_column='idgarante2',
        related_name='garantias_secundarias',
        verbose_name="Garante Auxiliar 2 si socio no paga"
    )
    idcuentadestino = models.ForeignKey(
        'CuentaBancaria', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_column='idcuentadestino',
        verbose_name="Cuenta para desembolso"
    )
    montoprestamosolicitado = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))], 
        verbose_name="Monto Solicitado"
    )    
    tasainteres = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Tasa de Interés (%)"
    )    
    montototalpagar = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Monto Total a Pagar"
    )    
    saldopendiente = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Saldo Pendiente"
    ) 
    numerocuotas = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Número de Cuotas"
    )    
    fechasolicitud = models.DateField(verbose_name="Fecha de Solicitud")
    fechavencimiento = models.DateField(verbose_name="Fecha de Vencimiento")    
    estadoprestamo = models.CharField(
        max_length=20, 
        choices=ESTADO_PRESTAMO_CHOICES, 
        default='Solicitado', # Por lógica, todo préstamo inicia como solicitado
        verbose_name="Estado del Préstamo"
    )

    def __str__(self):
        return f"Préstamo #{self.idprestamo} - Socio ID: {self.idsocio_id} - {self.estadoprestamo}"

    class Meta:
        db_table = 'Prestamo'
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'

class Pago(models.Model):
    ESTADO_PAGO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Validado', 'Validado'),
        ('Rechazado', 'Rechazado'),
    ]
    idpago = models.AutoField(primary_key=True) 
    idprestamo = models.ForeignKey(
        'Prestamo', 
        on_delete=models.PROTECT, 
        db_column='idprestamo',
        verbose_name="Préstamo"
    )
    idmetodopago = models.ForeignKey(
        'MetodoPago', 
        on_delete=models.PROTECT, 
        db_column='idmetodopago',
        verbose_name="Método de Pago"
    )
    montopagado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Monto Pagado"
    )
    numeroreferencia = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="Número de Referencia"
    )
    fechapago = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de Registro del Pago"
    )
    fechaconfirmacionadmin = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha Confirmación Admin"
    )
    comprobantepago = models.FileField(
        upload_to='media/pago/comprobantes_pagos/', 
        max_length=255, 
        null=False, 
        blank=False, 
        verbose_name="Archivo del Comprobante"
    )
    estadopago = models.CharField(
        max_length=20, 
        choices=ESTADO_PAGO_CHOICES, 
        default='Pendiente', 
        verbose_name="Estado del Pago"
    )

    def __str__(self):
        return f"Pago {self.idpago} - {self.idprestamo.idsocio} (${self.montopagado})"

    class Meta:
        db_table = 'Pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'


class UnidadMonetaria(models.Model):
    # Definimos las opciones para la restricción CHECK
    TIPO_MONEDA_CHOICES = [
        ('Efectivo', 'Efectivo'),
        ('Virtual', 'Virtual'),
    ]

    idunidadmonetaria = models.AutoField(primary_key=True)
    nombremoneda = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Moneda")
    tipomoneda = models.CharField(max_length=12, choices=TIPO_MONEDA_CHOICES, verbose_name="Tipo de Moneda")
    simbolomoneda = models.CharField(max_length=255, verbose_name="Símbolo")
    tasaconversionmoneda = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, verbose_name="Tasa de Conversión")
    estadomoneda = models.BooleanField(default=True, verbose_name="Estado Activo")

    class Meta:
        db_table = 'unidadmonetaria'
        verbose_name = 'Unidad Monetaria'
        verbose_name_plural = 'Unidades Monetarias'

    def __str__(self):
        # Esto hará que en los selectores se vea bonito, ej: "Dólares ($)" o "Gemas (💎)"
        return f"{self.nombremoneda} ({self.simbolomoneda})"

class Bingo(models.Model):
    TIPO_BINGO_CHOICES = [
        ('Virtual', 'Virtual'),
        ('Presencial', 'Presencial'),
    ]
    ESTADO_BINGO_CHOICES = [
        ('Programado', 'Programado'),
        ('En Curso', 'En Curso'),
        ('Finalizado', 'Finalizado'),
        ('Cancelado', 'Cancelado'),
    ]
    idbingo = models.AutoField(primary_key=True)
    idunidad_venta = models.ForeignKey(UnidadMonetaria, on_delete=models.PROTECT, related_name='bingos_venta')
    idunidad_premio = models.ForeignKey(UnidadMonetaria, on_delete=models.PROTECT, related_name='bingos_premio')
    titulobingo = models.CharField(
        max_length=150, 
        verbose_name="Título del Bingo"
    )
    fechaprogramadabingo = models.DateTimeField(
        verbose_name="Fecha y Hora del Evento"
    )
    tipobingo = models.CharField(
        max_length=20, 
        choices=TIPO_BINGO_CHOICES,
        verbose_name="Tipo de Bingo"
    )
    lugarbingo = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Lugar (si es presencial)"
    )
    urlsesionbingo = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Link de la sesión (si es virtual)"
    )
    preciocarton = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio del Cartón"
    )
    premiomayor = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Monto del Premio Mayor"
    )
    descripcionpremiomayor = models.CharField(
        max_length=100, 
        verbose_name="¿Qué es el premio mayor?"
    )
    estadobingo = models.CharField(
        max_length=20, 
        choices=ESTADO_BINGO_CHOICES, 
        default='Programado',
        verbose_name="Estado del Bingo"
    )
    rutaimagenpremiomayor = models.ImageField(
        upload_to='media/bingo/imagen_premio_mayor/', 
        max_length=300, 
        null=True, 
        blank=True,
        verbose_name="Imagen del Premio"
    )
    urlvideopromocional = models.FileField(
        upload_to='media/bingo/video_promocional/', 
        max_length=300, 
        null=True, 
        blank=True,
        verbose_name="Video Promocional"
    )
    descripcionpremios = models.TextField(
        max_length=500, 
        null=True, 
        blank=True, 
        verbose_name="Descripción de otros premios"
    )

    def __str__(self):
        return f"{self.titulobingo} ({self.fechaprogramadabingo.date()})"

    class Meta:
        db_table = 'Bingo'
        verbose_name = 'Bingo'
        verbose_name_plural = 'Bingos'

class Ahorro(models.Model):
    TIPO_AHORRO_CHOICES = [
        ('Obligatorio', 'Obligatorio'),
        ('Voluntario', 'Voluntario'),
    ]
    # FIX: Se corrigieron los estados para coincidir con la lógica que manejamos en Python/HTML
    ESTADO_AHORRO_CHOICES = [
        ('Acreditado', 'Acreditado'),
        ('Pendiente', 'Pendiente'),
        ('Rechazado', 'Rechazado'),
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    idahorro = models.AutoField(primary_key=True)
    idsocio = models.ForeignKey(
        'Socio', 
        on_delete=models.PROTECT, 
        db_column='idsocio',
        verbose_name="Socio"
    )
    idbingo = models.ForeignKey(
        'Bingo', 
        on_delete=models.SET_NULL,
        null=True,  
        blank=True, 
        db_column='idbingo',
        verbose_name="Bingo Asociado"
    )
    tipoahorro = models.CharField(
        max_length=50, 
        choices=TIPO_AHORRO_CHOICES, 
        verbose_name="Tipo de Ahorro"
    )
    montoahorro = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        # Se quitó la validación estricta de mayor a 0 para permitir los RETIROS (números negativos)
        verbose_name="Monto Ahorrado"
    )
    fechaahorro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Ahorro"
    )
    comentarioahorro = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Comentario"
    )
    estadoahorro = models.CharField(
        max_length=25, 
        choices=ESTADO_AHORRO_CHOICES, 
        verbose_name="Estado del Ahorro"
    )
    idmetodopago = models.ForeignKey(
        'MetodoPago', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idmetodopago',
        verbose_name="Cuenta de Destino"
    )
    comprobanteahorro = models.FileField(
        upload_to='media/ahorro/comprobantes/', 
        null=True, 
        blank=True, 
        verbose_name="Comprobante de Ahorro"
    )
    # FIX: AQUÍ ES EL LUGAR CORRECTO PARA ESTA COLUMNA
    origenahorro = models.CharField(
        max_length=50, 
        default='Directo', 
        null=True, 
        blank=True, 
        verbose_name="Origen del Ahorro"
    )
    def __str__(self):
        return f"Ahorro #{self.idahorro} - Socio {self.idsocio_id} (${self.montoahorro})"

    class Meta:
        db_table = 'Ahorro'
        verbose_name = 'Ahorro'
        verbose_name_plural = 'Ahorros'

class Jugador(models.Model):
    ESTADO_CUENTA_CHOICES = [
        ('Activo', 'Activo'),
        ('Suspendido', 'Suspendido'),
        ('Moroso', 'Moroso'),
    ]
    idjugador = models.AutoField(primary_key=True)
    idsocio = models.ForeignKey(
        'Socio', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idsocio',
        verbose_name="Socio Vinculado"
    )
    nombresjugador = models.CharField(
        max_length=150, 
        null=True, 
        blank=True, 
        verbose_name="Nombres Completos"
    )
    apellidosjugador = models.CharField(
        max_length=150, 
        null=True, 
        blank=True, 
        verbose_name="Apellidos Completos"
    )
    nacionalidad = models.CharField(max_length=50, default='Ecuatoriana', verbose_name="Nacionalidad")
    cedulaidentidadjugador = models.CharField(
        max_length=20, 
        unique=True, 
        null=True, 
        blank=True, 
        #validators=[validar_cedula_ecuatoriana], # VALIDADOR ACTIVO
        verbose_name="Cédula de Identidad"
    )
    foto_cedula_frontal = models.ImageField(upload_to='media/jugador/cedula/frontal/', null=True, blank=True, verbose_name="Foto Cédula Frontal")
    foto_cedula_trasera = models.ImageField(upload_to='media/jugador/cedula/trasera/', null=True, blank=True, verbose_name="Foto Cédula Trasera")
    avatarjugador = models.ImageField(
        upload_to='media/jugador/avatar/', 
        null=True, 
        blank=True, 
        verbose_name="Avatar/Foto"
    )  
    aliasjugador = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="Alias en el Juego"
    )
    correojugador = models.EmailField(
        max_length=200, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="Correo Electrónico"
    )   
    fecharegistrojugador = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de Registro"
    )
    saldocreditojugador = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Saldo/Crédito (Dinero Real)"
    )
    saldovirtualjugador = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Saldo Virtual (Fichas/Puntos)"
    )
    estadocuentajugador = models.CharField(
        max_length=20, 
        choices=ESTADO_CUENTA_CHOICES, 
        default='Activo',
        verbose_name="Estado de Cuenta"
    )

    def clean(self):
        super().clean()
        if not self.idsocio:
            errores = {}
            if not self.nombresjugador:
                errores['nombresjugador'] = "Los nombres son obligatorios para jugadores externos."
            if not self.apellidosjugador:
                errores['apellidosjugador'] = "Los apellidos son obligatorios para jugadores externos."
            if not self.cedulaidentidadjugador:
                errores['cedulaidentidadjugador'] = "La cédula es obligatoria para verificar la identidad."
            if not self.correojugador:
                errores['correojugador'] = "El correo es obligatorio para contactar al jugador."
            if errores:
                raise ValidationError(errores)

    def __str__(self):
        if self.nombresjugador and self.apellidosjugador:
            return f"{self.nombresjugador} {self.apellidosjugador} ({self.aliasjugador})"
        return self.aliasjugador or f"Jugador {self.idjugador}"

    class Meta:
        db_table = 'Jugador'
        verbose_name = 'Jugador'
        verbose_name_plural = 'Jugadores'

class TarjetaRecarga(models.Model):
    ESTADO_TARJETA_CHOICES = [
        ('Activa', 'Activa'),
        ('Inactiva', 'Inactiva'),
    ]
    TIPO_SALDO_CHOICES = [
        ('Efectivo', 'Saldo Real ($)'),
        ('Virtual', 'Fichas Virtuales'),
    ]
    
    idtarjetarecarga = models.AutoField(primary_key=True)
    nombretarjetarecarga = models.CharField(max_length=100, verbose_name="Nombre del Paquete")
    tiposaldo = models.CharField(max_length=20, choices=TIPO_SALDO_CHOICES, verbose_name="Tipo de Saldo Destino")
    montotarjetarecarga = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad de Saldo/Puntos que Otorga")
    preciodetarjetarecarga = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta (Lo que paga el usuario)")
    descripciontarjetarecarga = models.TextField(verbose_name="Beneficios (Separados por comas)")
    estado = models.CharField(max_length=15, choices=ESTADO_TARJETA_CHOICES, default='Activa')
    espopular = models.BooleanField(default=False, verbose_name="¿Es la tarjeta más popular?")

    def __str__(self):
        return f"{self.nombretarjetarecarga} - {self.tiposaldo} (${self.preciodetarjetarecarga})"

    class Meta:
        db_table = 'TarjetaRecarga'
        verbose_name = 'Tarjeta de Recarga'
        verbose_name_plural = 'Tarjetas de Recarga'

class TransaccionRecarga(models.Model):
    ESTADO_TRANSACCION_CHOICES = [
        ('Pendiente', 'Pendiente de Pago/Aprobación'),
        ('Completada', 'Completada y Saldo Acreditado'),
        ('Rechazada', 'Rechazada/Cancelada'),
    ]
    
    idtransaccion = models.AutoField(primary_key=True)
    idjugador = models.ForeignKey(
        'Jugador', 
        on_delete=models.CASCADE, 
        db_column='idjugador', 
        verbose_name="Jugador Solicitante"
    )
    idtarjeta = models.ForeignKey(
        'TarjetaRecarga', 
        on_delete=models.PROTECT, # PROTECT evita que borres una tarjeta si alguien ya la compró (protege tu contabilidad)
        db_column='idtarjeta', 
        verbose_name="Paquete Comprado"
    )
    
    # Guardamos una "foto" de los valores exactos en el momento de la compra
    monto_pagado = models.DecimalField(
        max_digits=10, decimal_places=2, 
        verbose_name="Monto Total a Pagar"
    )
    saldo_acreditar = models.DecimalField(
        max_digits=10, decimal_places=2, 
        verbose_name="Saldo/Puntos a Acreditar"
    )
    
    fechatransaccion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fechaactualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    # Datos técnicos de la pasarela de pago (PayPal, Transferencia, etc.)
    metodopago = models.CharField(max_length=50, null=True, blank=True, verbose_name="Método de Pago")
    referenciapago = models.CharField(max_length=100, null=True, blank=True, verbose_name="ID de Transacción (Pasarela)")
    comprobante = models.ImageField(upload_to='media/jugador/Comprobante_recargas/', null=True, blank=True, verbose_name="Comprobante (Si es manual)")
    
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_TRANSACCION_CHOICES, 
        default='Pendiente', 
        verbose_name="Estado"
    )

    def __str__(self):
        return f"TXN-{self.idtransaccion} | {self.idjugador.aliasjugador} | {self.idtarjeta.nombretarjetarecarga}"

    class Meta:
        db_table = 'TransaccionRecarga'
        verbose_name = 'Transacción de Recarga'
        verbose_name_plural = 'Historial de Transacciones'

class Regalo(models.Model):
    ESTADO_REGALO_CHOICES = [
        ('Acumulado', 'Acumulado'),
        ('Sorteado', 'Sorteado'),
        ('Entregado', 'Entregado'),
    ]
    idregalo = models.AutoField(
        primary_key=True, 
        verbose_name="ID de Regalo"
    )
    idsocio = models.ForeignKey(
        'Socio', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idsocio',
        verbose_name="Socio Donante"
    )
    idpartida = models.ForeignKey(
        'PartidaBingo', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idpartida',
        verbose_name="Sorteado en Ronda"
    )
    nombreregalo = models.CharField(
        max_length=100, 
        verbose_name="Nombre/Tipo de Regalo"
    )
    descripcionregalo = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        verbose_name="Descripción o Mensaje"
    )
    valorregalo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Valor del Regalo ($)"
    )
    fechaentregaregalo = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Entrega"
    )
    estadoregalo = models.CharField(
        max_length=20, 
        choices=ESTADO_REGALO_CHOICES, 
        verbose_name="Estado del Regalo"
    )
    fechaultimaactualizacion = models.DateTimeField(
        auto_now=True, 
        verbose_name="Última Actualización"
    )
    urlimagen = models.ImageField(
        upload_to='media/socio/regalo/imagenes/', 
        verbose_name="Imagen del Regalo"
    )

    def __str__(self):
        return f"{self.nombreregalo} - {self.estadoregalo}"

    class Meta:
        db_table = 'Regalo'
        verbose_name = 'Regalo/Premio'
        verbose_name_plural = 'Catálogo de Regalos'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estadoregalo__in=['Acumulado', 'Sorteado', 'Entregado']),
                name='chk_regalo_estadoregalo'
            )
        ]

class AporteSemanal(models.Model):
    ESTADO_APORTE_CHOICES = [
        ('Pendiente', 'Pendiente de Pago'),
        ('En Revision', 'En Revisión'),
        ('Al Dia', 'Al Día'),
        ('Atrasado', 'Atrasado'),
    ]
    METODO_INGRESO_CHOICES = [
        ('Efectivo', 'Efectivo'),
        ('Transferencia', 'Transferencia'),
        ('Fisico', 'Físico'),
    ]
    idaporte = models.AutoField(
        primary_key=True, 
        verbose_name="ID de Aporte"
    )
    idsocio = models.ForeignKey(
        'Socio', 
        on_delete=models.CASCADE, 
        db_column='idsocio',
        verbose_name="Socio"
    )
    idregalo = models.ForeignKey(
        'Regalo', 
        on_delete=models.CASCADE, 
        db_column='idregalo',
        verbose_name="Regalo Asignado",
        
        null=True, 
        blank=True,
    )
    idbingo = models.ForeignKey(
        'Bingo', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idbingo',
        verbose_name="Bingo Asociado"
    )
    numerosemana = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="Número de Semana"
    )
    fechaplanificadadada = models.DateTimeField(
        verbose_name="Fecha Planificada"
    )
    fechaentregareal = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Entrega Real"
    )
    metodoingreso = models.CharField(
        max_length=50, 
        choices=METODO_INGRESO_CHOICES,
        null=True,  
        blank=True,
        verbose_name="Método de Ingreso"
    )
    referenciaingreso = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Referencia/Comprobante"
    )
    estadoaporte = models.CharField(
        max_length=20, 
        choices=ESTADO_APORTE_CHOICES,
        null=True, 
        blank=True,
        verbose_name="Estado del Aporte"
    )
    montoaporte = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monto del Aporte"
    )
    idmetodopago = models.ForeignKey(
        'MetodoPago', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idmetodopago',
        verbose_name="Cuenta de Destino"
    )
    comprobanteaporte = models.FileField(
        upload_to='media/aportes/comprobantes/', 
        null=True, 
        blank=True, 
        verbose_name="Comprobante de Cuota Semanal"
    )
    # FIX: AQUÍ SE ELIMINÓ EL CAMPO "origenahorro" QUE ESTABA EN LA TABLA INCORRECTA
    def __str__(self):
        return f"Aporte {self.idaporte} - Socio: {self.idsocio_id} - Semana: {self.numerosemana}"

    class Meta:
        db_table = 'AporteSemanal'
        verbose_name = 'Aporte Semanal'
        verbose_name_plural = 'Control de Aportes Semanales'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estadoaporte__in=['Pendiente', 'En Revision', 'Al Dia', 'Atrasado']),
                name='chk_aportesemanal_estadoaporte'
            ),
            models.CheckConstraint(
                condition=models.Q(metodoingreso__in=['Efectivo', 'Transferencia', 'Fisico']) | models.Q(metodoingreso__isnull=True),
                name='chk_aportesemanal_metodoingreso'
            )
            
        ]

class PartidaBingo(models.Model):
    ESTADO_PARTIDA_CHOICES = [
        ('Programada', 'Programada'),
        ('En Juego', 'En Juego'),
        ('Verificando', 'Verificando'),
        ('Desempate', 'Desempate'),
        ('Finalizada', 'Finalizada'),
    ]
    ESTADO_MODALIDAD_CHOICES = [
        ('Las Cuatro Esquinas', 'Las Cuatro Esquinas'),
        ('Tabla Llena', 'Tabla Llena'),
        ('Linea Vertical', 'Linea Vertical'),
        ('En Diagonal', 'En Diagonal'),
        ('Forma de X', 'Forma de X'),
        ('Forma de Cruz', 'Forma de Cruz'),
        ('Marco de Foto', 'Marco de Foto'),
        ('Forma de L', 'Forma de L'),
        ('Forma de C', 'Forma de C'),
        ('Forma de T', 'Forma de T'),
        ('Forma de U', 'Forma de U'),
        ('Forma de H', 'Forma de H'),
        ('Forma de Z', 'Forma de Z'),
        ('Forma de Flecha', 'Forma de Flecha'),
    ]
    ESTADO_PREMIO_MATERIAL_CHOICES = [
        ('No Aplica', 'No Aplica'),
        ('Pendiente', 'Pendiente'),
        ('Entregando', 'Entregando'),
        ('Entregado', 'Entregado'),
    ]
    idpartidabingo = models.AutoField(primary_key=True)
    idbingo = models.ForeignKey(
        'Bingo', 
        on_delete=models.PROTECT, 
        db_column='idbingo',
        verbose_name="Evento de Bingo"
    )
    idjugadororganador = models.ForeignKey(
        'Jugador', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idjugadororganador',
        verbose_name="Jugador Organizador / Ganador"
    )
    idaporte = models.ForeignKey(
        'AporteSemanal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idaporte',
        verbose_name="Aporte Semanal a la partida de bingo"
    )
    nombreronda = models.CharField(
        max_length=100, 
        verbose_name="Nombre de la Ronda"
    )
    modalidad_victoria = models.CharField(
        max_length=50, 
        choices=ESTADO_MODALIDAD_CHOICES, 
        verbose_name="Modalidad de juego (relleno de carton)"
    )
    valorpremio = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True, 
        blank=True, 
        verbose_name="Valor del premio"
    )
    premiomaterial = models.CharField(
        max_length=150, 
        null=True, 
        blank=True, 
        verbose_name="Premio Material"
    )
    estadopremiomaterial = models.CharField(
        max_length=20, 
        choices=ESTADO_PREMIO_MATERIAL_CHOICES, 
        default='No Aplica',
        verbose_name="Estado Logístico del Premio"
    )
    estadopartida = models.CharField(
        max_length=20, 
        choices=ESTADO_PARTIDA_CHOICES, 
        default='En Juego',
        verbose_name="Estado de la Partida"
    )
    bolascantadas = models.TextField(
        verbose_name="Historial de Bolas Cantadas"
    )
    ultimabola = models.IntegerField(
        verbose_name="Última Bola Cantada"
    )
    haydesempate = models.BooleanField(
        null=True, 
        blank=True, 
        verbose_name="¿Hubo Desempate?"
    )
    # varchar(max) para guardar múltiples IDs separados por comas
    idbingadores = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="IDs de los Ganadores"
    )   
    bolamayordesempate = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="Bola Mayor (Desempate)"
    )   
    sorteodesempate = models.JSONField(null=True, blank=True, default=dict)
    horainicio = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Hora de Inicio"
    )   
    horafin = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Hora de Finalización"
    )


    def __str__(self):
        return f"{self.nombreronda} - Bingo {self.idbingo_id} ({self.estadopartida})"

    class Meta:
        db_table = 'PartidaBingo'
        verbose_name = 'Partida de Bingo'
        verbose_name_plural = 'Partidas de BAingo'

class Carton(models.Model):
    idcarton = models.AutoField(
        primary_key=True, 
        verbose_name="ID Interno del Cartón"
    )  
    codigocarton = models.CharField(
        max_length=30, 
        unique=True, 
        verbose_name="Código/Serial del Cartón"
    )
    matriznumeros = models.JSONField(
        verbose_name="Matriz de Números (Formato JSON)"
    )
    esmaestro = models.BooleanField(
        default=False,
        verbose_name="¿Es Cartón Maestro?"
    )

    def __str__(self):
        tipo = "Maestro" if self.esmaestro else "Temporal"
        return f"{self.codigocarton} - {tipo}"

    class Meta:
        db_table = 'Carton'
        verbose_name = 'Catálogo de Cartón'
        verbose_name_plural = 'Catálogo de Cartones'

class CartonPartidaBingo(models.Model):
    ESTADO_CARTON_CHOICES = [
        ('Disponible', 'Disponible'),
        ('Reservado', 'Reservado'),
        ('Vendido', 'Vendido'),
        ('Anulado', 'Anulado'),
    ]
    idcartonpartida = models.AutoField(primary_key=True)
    idjugador = models.ForeignKey(
        'Jugador', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='idjugador'
    )
    idpartida = models.ForeignKey(
        'PartidaBingo', 
        on_delete=models.CASCADE, 
        db_column='idpartida'
    )
    idcarton = models.ForeignKey(
        'Carton', 
        on_delete=models.PROTECT, 
        db_column='idcarton'
    )
    preciopagado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    fechacompra = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Fecha y Hora de Adquisición"
    )
    estadocarton = models.CharField(
        max_length=20, 
        choices=ESTADO_CARTON_CHOICES, 
        default='Disponible'
    )
    esganador = models.BooleanField(default=False)
    cantidadaciertos = models.IntegerField(default=0)
    numerosmarcados = models.CharField(
        max_length=500, 
        default='[]',
        verbose_name="Números Marcados Manualmente"
    )
    fechaganador = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Momento del Triunfo"
    )

    class Meta:
        db_table = 'CartonPartidaBingo'
        verbose_name = 'Cartón en Juego'
        verbose_name_plural = 'Control de Cartones por Partida'
        constraints = [
            models.UniqueConstraint(
                fields=['idcarton', 'idpartida'], 
                name='uq_cartonpartidabingo_idscompuestos'
            )
        ]

    def __str__(self):
        return f"Partida {self.idpartida_id} - {self.idcarton.codigocarton}"

class PlataformaJuego(models.Model):
    idplataformajuego = models.AutoField(
        primary_key=True, 
        verbose_name="ID de la Plataforma"
    )
    nombreplataforma = models.CharField(
        max_length=25, 
        unique=True, 
        verbose_name="Nombre de la Plataforma"
    )
    logoplataforma = models.ImageField(
        upload_to='media/web/plataforma/logos/', 
        null=True, 
        blank=True, 
        verbose_name="Logo de la Plataforma"
    )
    urlplataforma = models.URLField(
        max_length=255, 
        verbose_name="URL de Acceso"
    )
    descripcionplataforma = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        verbose_name="Descripción"
    )
    estadoplataforma = models.BooleanField(
        default=True, 
        verbose_name="Estado Activo"
    )
    fechaadquisicionlicencia = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Adquisición"
    )
    fechavencimientolicencia = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Vencimiento"
    )
    contactoplataforma = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Contacto del Proveedor"
    )

    def __str__(self):
        return self.nombreplataforma

    class Meta:
        db_table = 'PlataformaJuego'
        verbose_name = 'Plataforma de Juego'
        verbose_name_plural = 'Plataformas de Juego'

class SesionJuego(models.Model):
    ESTADO_SESION_CHOICES = [
        ('Activa', 'Activa'),
        ('Finalizada', 'Finalizada'),
        ('Caida', 'Caída'),
    ]
    idsesion = models.AutoField(
        primary_key=True, 
        verbose_name="ID de Sesión"
    )
    idplataforma = models.ForeignKey(
        'PlataformaJuego', 
        on_delete=models.CASCADE, 
        db_column='idplataforma',
        verbose_name="Plataforma"
    )
    idjugador = models.ForeignKey(
        'Jugador', 
        on_delete=models.CASCADE, 
        db_column='idjugador',
        verbose_name="Jugador"
    )
    idpartida = models.ForeignKey(
        'PartidaBingo', 
        on_delete=models.CASCADE, 
        db_column='idpartida',
        verbose_name="Partida"
    )
    fechainiciosesion = models.DateTimeField(
        verbose_name="Inicio de Sesión"
    )
    fechafinsesion = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fin de Sesión"
    )
    ipconexion = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name="Dirección IP"
    )
    dispositivoconexion = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name="Dispositivo"
    )
    estadosesion = models.CharField(
        max_length=15, 
        choices=ESTADO_SESION_CHOICES, 
        verbose_name="Estado"
    )
    navegadorweb = models.CharField(
        max_length=150, 
        null=True, 
        blank=True, 
        verbose_name="Navegador"
    )
    tokenconexion = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name="Token de Conexión"
    )
    motivocierre = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name="Motivo de Cierre"
    )

    def __str__(self):
        return f"Sesión {self.idsesion} - Jugador: {self.idjugador_id}"

    class Meta:
        db_table = 'SesionJuego'
        verbose_name = 'Sesión de Juego'
        verbose_name_plural = 'Sesiones de Juego'
        
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estadosesion__in=['Activa', 'Finalizada', 'Caida']),
                name='chk_sesionjuego_estadosesion'
            )
        ]




class ConfiguracionWeb(models.Model):
    idconfiguracion = models.AutoField(primary_key=True)
    titulosobrenosotros = models.CharField(
        max_length=150, 
        default="¿Qué es CoopBingo?",
        verbose_name="Título Sobre Nosotros"
    )
    descripcionsobrenosotros = models.TextField(
        verbose_name="Texto Descriptivo (Sobre Nosotros)"
    )
    imagenpromocional = models.ImageField(
        upload_to='media/web/inicio/', 
        null=True, 
        blank=True, 
        verbose_name="Imagen Promocional del Inicio"
    )
    numerowhatsapp = models.CharField(
        max_length=12, 
        null=True, 
        blank=True, 
        verbose_name="Número de WhatsApp",
        help_text="Incluya el código de país. Ej: +593987654321"
    )
    enlaceinstagram = models.URLField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Perfil de Instagram",
        help_text="Ej: https://instagram.com/coopbingo"
    )
    enlacefacebook = models.URLField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Página de Facebook",
        help_text="Ej: https://facebook.com/coopbingo"
    )
    fechaultimaactualizacion = models.DateTimeField(
        auto_now=True, 
        verbose_name="Última Actualización"
    )

    def __str__(self):
        return "Configuración Global del Sitio Web"

    class Meta:
        db_table = 'ConfiguracionWeb'
        verbose_name = 'Configuración Web'
        verbose_name_plural = 'Configuraciones Web'

class MensajeChat(models.Model):
    idmensaje = models.AutoField(primary_key=True)
    idbingo = models.ForeignKey(Bingo, models.DO_NOTHING, db_column='idbingo')
    usuario = models.CharField(max_length=100)
    mensaje = models.TextField()
    fechahora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mensaje_chat'

class ValoracionSistema(models.Model):
    idvaloracion = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="Usuario"
    )
    puntuacion = models.DecimalField(
        max_digits=2, decimal_places=1,
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('5.0'))],
        verbose_name="Estrellas"
    )
    comentario = models.TextField(verbose_name="Comentario")
    fecha = models.DateTimeField(auto_now=True, verbose_name="Fecha de Valoración")

    def obtener_rol(self):
        # Determinamos de forma dinámica el rol en la plataforma
        from .models import Socio, Jugador
        es_socio = Socio.objects.filter(cisocio=self.usuario.username).exists()
        es_jugador = Jugador.objects.filter(cedulaidentidadjugador=self.usuario.username).exists()
        
        if es_socio and es_jugador:
            return "Socio-Jugador"
        elif es_socio:
            return "Socio"
        elif es_jugador:
            return "Jugador"
        return "Usuario Externo"

    def get_nombre_mostrar(self):
        from .models import Jugador, Socio
        jugador = Jugador.objects.filter(cedulaidentidadjugador=self.usuario.username).first()
        if jugador and jugador.aliasjugador:
            return jugador.aliasjugador
        socio = Socio.objects.filter(cisocio=self.usuario.username).first()
        if socio:
            return f"{socio.primernombresocio} {socio.primerapellidosocio}"
        return self.usuario.first_name

    def estrellas_html(self):
        # Lógica para pintar estrellas enteras, medias o vacías
        html = ""
        puntuacion = float(self.puntuacion)
        for i in range(1, 6):
            if puntuacion >= i:
                html += '<i class="fas fa-star text-warning"></i>'
            elif puntuacion >= i - 0.5:
                html += '<i class="fas fa-star-half-alt text-warning"></i>'
            else:
                html += '<i class="far fa-star text-warning"></i>'
        return html

    class Meta:
        db_table = 'ValoracionSistema'
        verbose_name = 'Valoración del Sistema'
        verbose_name_plural = 'Valoraciones del Sistema'