# -*- coding: utf8 -*-
from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docato_proj.settings')

#app = Celery('docato_proj')
app = Celery('docato_proj',backend='rpc://') #,include=['test_celery.tasks'] # broker='amqp://admin:mypass@rabbit:5672'

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, force=True)
# подстрахуюсь
try:
	import docato.tasks
except ImportError:
	import docato.docato.tasks
print('app.tasks=', app.tasks)

app.conf.update(
	#
	BROKER_URL='amqp://admin:mypass@rabbit:5672',
	#BROKER_URL='amqp://admin:mypass@127.0.0.1:5673',
)
