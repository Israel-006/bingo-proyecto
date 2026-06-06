"""
URL configuration for django_prueba project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from bingo import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # ==========================================
    # 1. COMUNES (Páginas públicas y base)
    # ==========================================
    path('', views.inicio, name='inicio'),
    path('bingo-publico/', views.bingo_publico, name='bingo'), # Apunta a comunes/bingo.html

    # ==========================================
    # 2. CUENTAS (Autenticación y Perfiles)
    # ==========================================
    path('login/', views.inicio_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    
    # Registro de usuarios
    path('registro/opciones/', views.seleccion_registro, name='seleccion_registro'),
    path('registro/socio/', views.registro_socio, name='registro_socio'),
    path('registro/jugador/', views.registro_jugador, name='registro_jugador'),
    
    # Gestión del perfil del usuario logueado
    path('mi-cuenta/bancaria/', views.cuenta_bancaria, name='cuenta_bancaria'),
    path('mi-cuenta/ahorros/', views.ahorro, name='ahorro'),
    path('premios-y-regalos/', views.regalo, name='regalo'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/mis_cartones', views.mis_cartones, name='mis_cartones'),
    path('perfil/mis_cartones/pdf/<int:id_bingo>/', views.descargar_cartones_pdf, name='descargar_cartones_pdf'),
    

    # ==========================================
    # 3. ADMINISTRADOR (Consolas de Mando)
    # ==========================================
    # Esta es la ruta maestra que carga tu archivo dashboard.html (SPA)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/reporte-socios-estrella/', views.reporte_socios_puntuales, name='reporte_socios_puntuales'),
    path('dashboard/reporte-liquidacion/<int:id_bingo>/', views.reporte_liquidacion_bingo, name='reporte_liquidacion_bingo'),
    path('dashboard/reporte-cartera/', views.reporte_cartera_prestamos, name='reporte_cartera_prestamos'),
    path('dashboard/reporte-caja-pdf/', views.reporte_caja_semanal_pdf, name='reporte_caja_semanal_pdf'),

    # ==========================================
    # 4. NEGOCIO (Finanzas y Ventas)
    # ==========================================
    path('negocio/aportes/', views.control_aportes, name='control_aportes'),
    path('negocio/creditos/', views.creditos, name='creditos'),
    path('negocio/metodos-pago/', views.metodos_pago, name='metodos_pago'),
    path('negocio/pagos/', views.pago, name='pago'),
    path('negocio/venta-cartones/', views.venta_cartones, name='venta_cartones'),

    # ==========================================
    # 5. PARTIDA (El Motor del Juego en Vivo)
    # ==========================================
    # Vistas del Jugador
    path('juego/sala-espera/<int:id_partida>/', views.sala_espera, name='sala_espera'),
    path('juego/sala-espera/desempate/<int:id_partida>/', views.sala_espera_desempate, name='sala_espera_desempate'), # Actualizada con ID
    path('juego/tablero-en-vivo/<int:id_partida>/', views.tablero_tiempo_real, name='tablero_tiempo_real'), # Recomendado con ID
    path('juego/sesion/<int:id_partida>/', views.sesion_juego, name='sesion_juego'),
    
    # Vistas del Administrador / Operador del Bingo
    path('juego/partida/<int:id_partida>/estado-json/', views.estado_partida_json, name='estado_partida_json'),
    path('juego/admin/tablero/<int:id_partida>/', views.tablero_admin, name='tablero_admin'),
    path('juego/admin/desempate/<int:id_partida>/', views.desempate_admin, name='desempate_admin'),
    path('juego/admin/consola/<int:id_partida>/', views.consola_juego, name='consola_juego'), # Nueva ruta
    
    # Logica de las bolas
    path('api/partida/<int:id_partida>/sacar_bola/', views.sacar_bola_api, name='sacar_bola_api'),


]