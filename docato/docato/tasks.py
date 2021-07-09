# -*- coding: utf8 -*-
from celery import task
from django.db import transaction
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
# for export
from lxml.html.soupparser import fromstring
from lxml.cssselect import CSSSelector
from lxml.etree import tostring
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
		from docato.docato.Crawlers.Facebook.Crawler import discussion_FB_get_byurl
		from docato.docato.Crawlers.LJ.Crawler import discussion_LJ_get_byurl
	except ImportError:
		from docato.Crawlers.pikabu.Crawler import discussion_pikabu_get_byurl
		from docato.Crawlers.Facebook.Crawler import discussion_FB_get_byurl
		from docato.Crawlers.LJ.Crawler import discussion_LJ_get_byurl

	#
	logger.info('Got doc %s to process', doc_id)
	doc = Document.objects.get(id=doc_id)
	# в media-dir лежит zip архив, в котором все файлы дискуссии, надо  положить главный html этой дискуссии в converted_content
	try :
		if 'pikabu.ru' in url:
			html_text, authors = discussion_pikabu_get_byurl(url)
			doc.content_type = 'pikabu.html'  # preprocessing.PDF_EXTENSION
			doc.authors = authors
			doc.converted_content = html_text
			doc.state = Document.States.ANALYZED
			doc.preproc_state = Document.States.ANALYZED
		if 'facebook.com' in url:
			doc.content_type = 'facebook.html'
			html_text = discussion_FB_get_byurl(url)
			doc.authors = ''
			doc.converted_content = html_text
			doc.state = Document.States.ANALYZED
			doc.preproc_state = Document.States.ANALYZED
		if 'livejournal.com' in url:
			doc.content_type = 'livejournal.html'
			html_text = discussion_LJ_get_byurl(url)
			doc.authors = ''
			doc.converted_content = html_text
			doc.state = Document.States.ANALYZED
			doc.preproc_state = Document.States.ANALYZED


	except Exception as ex:
		logger.error('не смог обработать документ %s: %r\n%s' % (doc_id, ex, traceback.format_exc()))
		print('не смог обработать документ %s: %r\n%s' % (doc_id, ex, traceback.format_exc()))
		#
		with transaction.atomic():
			doc.converted_content = '<html><head></head>ошибка случилась  <br/>{}</html>'.format(ex.message)
			doc.state = Document.States.ERROR
			doc.save()
		return
	doc.save()
	return


#
def _stringify_children(node):
	parts = ([node.text] +
			list(chain(*([c.text, tostring(c), c.tail] for c in node.getchildren()))) +
			[node.tail])
	# filter removes possible Nones in texts and tails
	return ''.join(filter(None, parts))

def get_filecontent_from_zip(pathzip, pathfile):
	with zipfile.ZipFile(pathzip, 'r', zipfile.ZIP_DEFLATED) as archive:
		try:
			content = archive.read(pathfile)
			return content
		except KeyError:
			pass
	return ''

# извлечь текстовые блоки из html документа
def get_text_blocks_of_discussion(tree, dt, slug, main_authors):
	def get_tokens_indexes(spans):
		max_token = -1
		min_token  = 999999999999
		for s in spans:
			if 'data-token-id' not in s.attrib.keys():
				continue
			#
			tid = int(s.attrib['data-token-id'])
			if tid<min_token: min_token = tid
			if tid>max_token: max_token = tid
		return min_token, max_token

	# main text block - post
	text_block_0 =  dict(id=0, owner_id=-1, datetime=dt, author=main_authors, edited=False, offset_from=None, offest_to=None)
	pathzip = os.path.join(MEDIA_ROOT, '%s.zip' % (slug))
	# если authors не разобран, то попробовать его взять из архива
	if not bool(main_authors):
		authors = get_filecontent_from_zip(pathzip, 'authors.json')
	else:
		authors = main_authors
	# внимание!!!  в body тело поста долждно идти вторым div (  [1] )всегда!
	min_token, max_token = get_tokens_indexes( tree.findall('.//body//div')[1].findall('.//span')  )
	text_block_0 =  dict(id=0, owner_id=-1, datetime=str(dt), author=authors, edited=False, offset_from=min_token, offest_to=max_token)
	#
	# other blocks
	blocks = [ text_block_0 ]
	comments = ujson.loads( get_filecontent_from_zip(pathzip, 'comments.json') )
	comments = comments['comments']
	_nocommentsinpage_counter = 0 # для отладки, иногда почему то коменты отсутствуют в html и не имеют токенов разметки, файлы comments.json и анализ текста страницы делвается отдельно,
	# поэтому возможно отсутствуют некоторые коментарии, которые добавлялись между разбором страницы и скачивании комментариев
	for id in comments.keys():
		comment = comments[id]
		#
		try:
			all_spans = tree.xpath("//div[@id = '%s']" % id)[0].findall(".//span")
		except IndexError as ex:
			_nocommentsinpage_counter+=1
			continue
		min_token, max_token = get_tokens_indexes(all_spans)
		#
		block = dict(id=id, owner_id=comment['answer'], datetime=str(comment['date']),
					 author=comment['nick'], edited=False,
					 offset_from=min_token, offest_to=max_token)
		#
		blocks.append(block)
	return blocks

# экспорт докумета в json для обучения ИИ
# и дискуссии тоже
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
			# не должно быть такого
			myprint('не должно быть такого')
	#
	# токены
	result['tokens'] = tokens
	myprint('массив tokens длинной='+str(len(tokens)))
	#
	# текст составленный из токенов
	result['plain_text']= ' '.join( [c.text for c in chunks] )
	myprint('plain_text  длинной=' + str(len(result['plain_text'])))
	#
	text_blocks = None
	# if this is a document, then handle source_file else handle as a discussion
	if document.content_type in settings.DISCUSS_CONTENT_TYPES:
		# discussion
		result['is_discussion'] = 1
		result['is_document'] = 0
		myprint('  is a DISCUSSION ' + str(document.content_type))
		html = document.converted_content
		slug = re.search("slug=([\\w\\d_]+)[&$]", html)
		if bool(slug):
			slug = slug.group(1)
			# нужен дальше\ниже для построения Source_file
			full_path = os.path.join(settings.MEDIA_ROOT, slug+'.zip')
			#
			# + построим текстовые блоки
			text_blocks = get_text_blocks_of_discussion(tree, document.load_time, slug, document.authors)

	else:
		# document
		result['is_discussion'] = 0
		result['is_document'] = 1
		# Source_file # document.source_file.name
		full_path = os.path.join(settings.MEDIA_ROOT, document.source_file.name)
	#
	# берем fiilpath и его закатываем в base 64 чем бы он не был
	try:
		with open(full_path, "rb") as file_src_of_doc:
			encoded_string = base64.b64encode(file_src_of_doc.read())
		result['Source_file']= encoded_string
		myprint('+Source_file OK - is FOUND')
	except IOError:
		result['Source_file']=None # поле будет пустым, если файл не найден
		myprint('+Source_file IS NOT FOUND')
	#
	# state обработан, не обработан
	result['state'] = document.state
	myprint('+state')
	#
	# title
	result['title'] = document.title
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
	# если это дискуссия, то есть текстовые блоки, надо их "присобачить"
	if bool(text_blocks):
		result['discussion'] = text_blocks
		myprint('в дискуссии %s текстовых блоков'%len(text_blocks))
	return ujson.dumps(result)



def build_export_channel_name(task_id):
	return 'project-export-tid-%s'%task_id
@app.task(name='project-export')
def project_export(**kwargs): # todo rename task to export_any
	from models import Project
	from models import Subject
	from models import Document
	#
	task_id = celery.current_task.request.id
	#   send
	def send_log_message(msg):
		import pika
		url = os.environ.get('CLOUDAMQP_URL', app.conf.BROKER_URL)
		params = pika.URLParameters(url)
		params.socket_timeout = 5
		#
		connection = pika.BlockingConnection(params)  # Connect to CloudAMQP
		channel = connection.channel()  # start a channel
		qname = build_export_channel_name(task_id)
		channel.queue_declare(queue=qname)  # Declare a queue
		# send a message
		channel.basic_publish(exchange='', routing_key='project-export-tid-%s' % task_id, body=msg)
		# print ("[x] Message sent to consumer")
		connection.close()
	#
	def export_doc_to_archive(d, archive):
		if d.state != Document.States.ANALYZED:
			return
		d_json = export_doc(d, send_log_message)
		# сохранить в файл
		# упаковать документы в архив
		archive.writestr(('proj_%s_subj_%s_doc_%s.json' % (d.subject.project.name, d.subject.name,d.title)).replace('\\','').replace('/',''),      d_json)
	# zip archive
	tmparchive = os.path.join(MEDIA_ROOT, 'archive_date_%s.zip'%(timezone.now()) )
	with zipfile.ZipFile(tmparchive, 'w', zipfile.ZIP_DEFLATED) as archive:
		# получим типа список документов, ид + заголовок
		documents_list = []
		if 'projects' in kwargs.keys():
			for proj_id in [int(p) for p in kwargs['projects'].split(',')]:
				logger.info('Got proj_id %s to process for EXPORT ', proj_id)
				# project = Project.objects.get(id=proj_id)
				subjects = Project.objects.filter(id=proj_id).get().subjects.all()
				for s in subjects:
					documents_portion = list( s.docs.defer("converted_content").only("id","title").all() )
					for d in documents_portion:
						# documents_list.append(d)
						export_doc_to_archive(d,archive)
		if 'subjects' in kwargs.keys():
			for subj_id in [int(p) for p in kwargs['subjects'].split(',')]:
				documents_portion = list(Document.objects.filter(subject=subj_id).defer("converted_content").only("id", "title").all())
				for d in documents_portion:
					# documents_list.append(d)
					export_doc_to_archive(d, archive)
		if 'docs' in kwargs.keys():
			for doc_id in [int(p) for p in kwargs['docs'].split(',')]:
				documents_portion = Document.objects.filter(id=doc_id).defer("converted_content").only("id", "title").all()
				for d in documents_portion:
					# documents_list.append(d)
					export_doc_to_archive(d, archive)
		#
		archive.close()
	send_log_message('project export archive is ready!<br/>')
	send_log_message('in export task '+' found '+str(len(documents_list))+' documents (or discussions)')
	download_filename = archive.filename[len(MEDIA_ROOT):]
	send_log_message('DOWNLOAD EXPORTED ZIP FILE : <b><a target="_blank" href="/media_export%s" >'%download_filename +download_filename+
					 '<button type = "button" class ="btn btn-success" style="margin: auto;display: block;"> Скачать </button>' + '</a></b>'
					)
	send_log_message('SUCCESS')
	return


# # TDD
# import django
# django.setup()
# #
# d = Document.objects.get(id=341)
# def f(msg):
# 	print(msg)
# export_doc(d,f)
