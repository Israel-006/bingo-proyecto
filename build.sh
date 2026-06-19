#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# 1. SOLUCIÓN NUCLEAR: Borrar TODAS las tablas corruptas de la base de datos
cat << 'EOF' | python manage.py shell
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
    """)
EOF

# 2. Obligamos a Django a detectar los campos nuevos y construir tablas nuevecitas
python manage.py makemigrations bingo
python manage.py migrate

# 3. Recolectar archivos estáticos
python manage.py collectstatic --no-input

# 4. Crear tu usuario administrador (Tu código original)
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='israel').exists() or \
User.objects.create_superuser('israel', 'israel@gmail.com', '12345')" \
| python manage.py shell