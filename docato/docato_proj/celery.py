# -*- coding: utf8 -*-
from __future__ import absolute_import

import os

from celery import Celery

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docato_proj.settings')

#app = Celery('docato_proj')
app = Celery('docato_proj', broker='amqp://admin:mypass@127.0.0.1:5673',backend='rpc://') #,include=['test_celery.tasks'] # TODO перенести параметры в настройки

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.update(
    #CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend',
    #BROKER_URL = 'amqp://guest:guest@127.0.0.1:5672/',
    #BROKER_URL = 'redis://redis',
    #BROKER_URL = 'redis://127.0.0.1',
    #CELERY_RESULT_BACKEND = 'redis://localhost/0',
)
