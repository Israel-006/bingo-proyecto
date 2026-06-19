from django.db import connection
from bingo.models import CartonPartidaBingo

try:
    # Capturamos el campo desde la lógica del modelo
    campo = CartonPartidaBingo._meta.get_field('numerosmarcados')
    
    # Forzamos a la base de datos a crear la columna saltando las migraciones
    with connection.schema_editor() as editor:
        editor.add_field(CartonPartidaBingo, campo)
        
    print("¡ÉXITO! La columna se forzó en PostgreSQL correctamente.")
except Exception as e:
    print("AVISO (Quizás la columna ya existía):", e)