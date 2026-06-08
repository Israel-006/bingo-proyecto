web: daphne -b 0.0.0.0 -p $PORT django_prueba.asgi:application
worker: celery -A django_prueba worker -l info -P eventlet
