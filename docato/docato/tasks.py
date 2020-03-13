# -*- coding: utf8 -*-
from celery import task
from docato_proj.celery import app
import logging, requests, os, tempfile, mimetypes, unidecode, traceback, subprocess
from django.core.files import File
from django.template.defaultfilters import slugify
from django.conf import settings

logger = logging.getLogger('preprocessing')
print('TASKS.py imported')


@app.task(name='load-data-for-document')
def process_doc(doc_id):
	from models import Document
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
	discuss_type = 'pikabu' in url
	slug = '100500'
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