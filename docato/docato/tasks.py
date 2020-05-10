# -*- coding: utf8 -*-
from celery import task
from django.utils import timezone
from docato_proj.celery import app
import celery
import logging, requests, os, tempfile, mimetypes, unidecode, traceback, subprocess
from django.core.files import File
from django.template.defaultfilters import slugify
from django.conf import settings
import ujson
import tempfile
import zipfile

logger = logging.getLogger('preprocessing')
print('TASKS.py imported')


@app.task(name='load-data-for-document')
def process_doc(doc_id):
	from models import Document
	try:
		from docato.docato.preprocessor import Preprocessor
	except ImportError:
		from docato.preprocessor import Preprocessor
	import preprocessing
	from feature_extraction import extract_features
	#
	try:
		logger.info('Got doc %s to process', doc_id)
		doc = Document.objects.get(id = doc_id)
		if doc.source_file:
			doc.content_type = os.path.splitext(doc.source_file.name)[1][1:].lower()
			logger.info('Extracted content-type %s from the uploaded filename %s' % (doc.content_type, doc.source_file.name))
		else:
			logger.info('Requesting file from %s' % doc.url)
			resp = requests.get(doc.url)

			if 'content-type' in resp.headers:
				doc.content_type = mimetypes.guess_extension(resp.headers['content-type'].split(';')[0])[1:].lower()
				logger.info('Content type %s from header %s' % (doc.content_type, resp.headers['content-type']))
			else:
				logger.info('Response contains no content-type header, assuming html...')
				doc.content_type = 'html'

			is_html = doc.content_type in preprocessing.HTML_EXTENSIONS
			if is_html:
				doc.content_type = preprocessing.PDF_EXTENSION
			with tempfile.NamedTemporaryFile(dir = os.path.join(settings.MEDIA_ROOT,
																Document.UPLOAD_TO),
											 prefix = slugify(unidecode.unidecode(doc.title)) + '_',
											 suffix = '.' + doc.content_type,
											 delete = False) as tmp_f:
				fname = tmp_f.name
			if is_html:
				logger.info('Getting html to pdf')
				subprocess.check_call(['wkhtmltopdf', doc.url.encode('utf8'), fname])
				with open(fname, 'r') as tmp_f:
					doc.source_file.save(fname, File(tmp_f))
			else:
				logger.info('Dumping request body to file')
				with open(fname, 'w+b') as tmp_f:
					djfile = File(tmp_f)
					for chunk in resp.iter_content(10000):
						tmp_f.write(chunk)
					doc.source_file.save(fname, djfile)
		doc.save()
		logger.info('The doc is saved, preprocessing...')
		Preprocessor()(doc, settings.CONVERTED_PAGE_WIDTH)
		logger.info('The doc is saved, analyzing...')
		extract_features(doc)
		doc.state = Document.States.ANALYZED
		logger.info('The doc %s has been successfully processed!' % doc.id)
	except Exception as err:
		doc.preproc_state = Document.States.ERROR
		logger.error('An error has occurred when processing the doc %s: %s\n%s' % (doc.title, err, traceback.format_exc()))
	doc.save()

@app.task(name='load-data-for-discussion')
def process_discussion(doc_id, url):
	from models import Document
	try:
		from docato.docato.Crawlers.pikabu.Crawler import discussion_pikabu_get_byurl
	except ImportError:
		from docato.Crawlers.pikabu.Crawler import discussion_pikabu_get_byurl

	#
	logger.info('Got doc %s to process', doc_id)
	doc = Document.objects.get(id=doc_id)
	# в media-dir лежит zip архив, в котором все файлы дискуссии, надо  положить главный html этой дискуссии в converted_content
	try :
		html_text = discussion_pikabu_get_byurl(url)
	except Exception as ex:
		logger.error('не смог обработать документ %s: %r\n%s' % (doc_id, ex, traceback.format_exc()))
		doc.state = Document.States.ANALYZED
		doc.converted_content = '<html><head></head>ошибка случилась  <br/>{}</html>'.format(ex.message)  # todo + стек трейс
		doc.state = Document.States.ERROR
		doc.save()
		return
	doc.content_type = 'pikabu.html'# preprocessing.PDF_EXTENSION
	doc.converted_content = html_text  #'<html><head></head>hello world</html>'
	doc.state = Document.States.ANALYZED
	doc.preproc_state = Document.States.ANALYZED
	doc.save()
	return

from lxml.html.soupparser import fromstring
from lxml.cssselect import CSSSelector
from itertools import chain
import collections
import re
import base64
try:
	from docato.docato.models import *
	from docato.docato_proj.settings import MEDIA_ROOT
except ImportError:
	from docato.models import *
	from docato_proj.settings import MEDIA_ROOT

#
def _stringify_children(node):
	parts = ([node.text] +
			list(chain(*([c.text, tostring(c), c.tail] for c in node.getchildren()))) +
			[node.tail])
	# filter removes possible Nones in texts and tails
	return ''.join(filter(None, parts))
def export_doc(document, myprint):
	myprint('<br/><br/>ДОКУМЕНТ №'+str(document.id)+'<br/>')
	result = dict()
	tree = fromstring(document.converted_content)
	tokens = collections.OrderedDict()
	sel = CSSSelector('span.chunk')
	chunks =  [e for e in sel(tree)]
	for c in chunks:
		m = re.search('token_(\d+)', c.attrib['class'])
		if bool(m) :
			t_id = m.group(1)
			tokens[ t_id ] = c.text
		else:
			pass # не должно быть такого
			myprint('не должно быть такого') # todo to log for user
	#
	# токены
	result['tokens'] = tokens
	myprint('массив tokens длинной='+str(len(tokens)))
	#
	# текст составленный из токенов
	result['plain_text']= ' '.join( [c.text for c in chunks] )
	myprint('plain_text  длинной=' + str(len(result['plain_text'])))
	#
	# Source_file # document.source_file.name
	full_path = os.path.join(settings.MEDIA_ROOT, document.source_file.name)
	try:
		with open(full_path, "rb") as file_src_of_doc:
			encoded_string = base64.b64encode(file_src_of_doc.read())
		result['Source_file']= encoded_string
		myprint('+Source_file OK - is FOUND')
	except IOError:
		result['Source_file']=None # поле будет пустым, если файл не найден
		myprint('+Source_file ISNOT FOUND')
	#
	# state обработан, не обработан
	result['state'] = document.state
	myprint('+state')
	#
	# title
	result['state'] = document.title
	#
	# load_time
	result['load_time'] = str(document.load_time)
	myprint('+load_time')
	#
	# content_type ? for example pdf
	result['content_type'] = document.content_type
	myprint('+content_type')
	#
	# slots and frames
	cues = document.all_cues
	frames = dict()
	slots = dict()
	for c in cues:
		cue = {"start": c.start , "end": c.end ,  "text": c.text}
		slot_id = c.slot_value.id
		slot_name = c.slot_value.slot.name # имя слота в системе типов
		if type(c.slot_value) in [ClassLabelSlotValue, IntegerSlotValue, RealSlotValue, ObjectSlotValue]:
			slot_value = c.slot_value.value
		elif type(c.slot_value) in [ObjectSlotValue]:
			slot_value = c.slot_value
		else:
			myprint('ошибка: тип слота не обработан:'+str(c.slot_value.slot))
		#
		frame_id = c.slot_value.frame.id
		frame_type = c.slot_value.frame.type.name
		frame_name = c.slot_value.frame.name
		#
		#  build objects
		slot = slots[slot_id] if slot_id in slots else dict(cues=[], name=slot_name)
		slot['cues'].append(cue)
		slot['name'] = slot_name
		slot['value'] = slot_value
		slots[slot_id] = slot
		frame = frames[frame_id] if frame_id in frames else dict(slots=[], type=frame_type, id=frame_id, name=frame_name)
		frames[frame_id] = frame
		frame['slots'].append(slot)
	# put frames structure to json
	result['frames'] = [frames[sk] for sk in frames.keys()]
	myprint('обработано '+str(len(cues))+' фреймов/пометок в документе '+str(document.id))

	return ujson.dumps(result)

def build_export_channel_name(task_id):
	return 'project-export-tid-%s'%task_id
@app.task(name='project-export')
def project_export(proj_id):
	from models import Project
	# try:
	# 	from docato.docato.Crawlers.pikabu.Crawler import discussion_pikabu_get_byurl
	# except ImportError:
	# 	from docato.Crawlers.pikabu.Crawler import discussion_pikabu_get_byurl

	#
	logger.info('Got proj_id %s to process for EXPORT ', proj_id)
	project = Project.objects.get(id=proj_id)
	task_id = celery.current_task.request.id
	#   send
	def send_log_message(msg):
		import pika
		url = os.environ.get('CLOUDAMQP_URL',  app.conf.BROKER_URL )
		params = pika.URLParameters(url)
		params.socket_timeout = 5
		#
		connection = pika.BlockingConnection(params)  # Connect to CloudAMQP
		channel = connection.channel()  # start a channel
		qname=build_export_channel_name(task_id)
		channel.queue_declare(queue=qname )  # Declare a queue
		# send a message
		channel.basic_publish(exchange='', routing_key='project-export-tid-%s'%task_id, body=msg)
		#print ("[x] Message sent to consumer")
		connection.close()
	#
	subjects = Project.objects.filter(id=proj_id).get().subjects.all()
	project_document_count = 0
	#
	tmparchive = os.path.join(MEDIA_ROOT, 'archive_P_%s_date_%s.zip'%(proj_id, timezone.now()) )
	with zipfile.ZipFile(tmparchive, 'w', zipfile.ZIP_DEFLATED) as archive:

		for s in subjects:
			documents_portion = list( s.docs.defer("converted_content").only("id","title").all() )

			for d in documents_portion:
				d_json = export_doc(d, send_log_message)
				# сохранить в файл
				# упаковать документы в архив
				archive.writestr('proj_%s_subj_%s_doc_%s.txt'%(proj_id, s.id, d.id), d_json)

			project_document_count +=  1
		archive.close()
		send_log_message('project export archive is ready!<br/>')
	send_log_message('in project '+str(proj_id)+' found '+str(project_document_count)+' documents')
	download_filename = archive.filename[len(MEDIA_ROOT):]
	send_log_message('DOWNLOAD EXPORTED ZIP FILE : <a target="_blank" href="/media_export%s" >'%download_filename +download_filename+ '</a>')
	return


# # TDD
# import django
# django.setup()
# #
# d = Document.objects.get(id=341)
# def f(msg):
# 	print(msg)
# export_doc(d,f)
