#!/usr/bin/env python
# -*- coding:utf-8 -*-
#import docker
#import datetime
#import collections

from flask import Flask, request
import thread
import logging
import os
import re
import sys
import subprocess
import xml.etree.ElementTree as ET
import hashlib
import socket
from lxml import etree
from lxml.html.soupparser import fromstring
from pikabu_getpost import get_post_html_uft8
from crawler_tokenize import mark_tokens_in_etree
from wget_whole_page import wget_whole_page
from contextlib import closing
from django.conf import settings

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


WGET_PORT = find_free_port() # settings.WGET_PORT             # порт на котором можно серфить внутри контейнера, это другой порт не "для снаружи"
MEDIA_DIR = settings.MEDIA_ROOT
TMP_DIR = settings.TMP_DIR


# сервит переработанный html дискуссии, чтобы wget забрал whole page с этого адреса и переделал ссылки на локальные
class view_Server :
    def __init__(self, port ):
        self.data = {}
        self.app = Flask(__name__)
        @self.app.route("/data")
        def data():
            id = request.args.get('id')
            return self.data[id]
        #
        def flaskThread():
            self.app.run(port=port)
        #
        thread.start_new_thread(flaskThread,())
    def add_data(self, data_in_utf8):
        m = hashlib.sha256()
        m.update(data_in_utf8)
        dst = m.hexdigest()
        self.data[dst] = data_in_utf8
        return dst
    def remove_data(self, id):
        del self.data[id]
app = view_Server(WGET_PORT)
###########

# sys.path.append('../')
# sys.path.append('../utils')

sys.path.append('docato/comments_crawling')
sys.path.append('docato/comments_crawling/utils')

from crawler_utils import Downloader
from comment_handle import _make_comment_html_from_xml, _make_comment_links_json

class PikabuWithCommentsProcessor(object):
    def __init__(self, opts=None):
        self.downloader = Downloader(delay=0.2)
        self.post_id_re_pat = re.compile(r'(\d+)$')

    def __call__(self, item):
        re_res = self.post_id_re_pat.search( item )
        return self._process_post_id( int( re_res.group(1) ) )


    # ok
    def _process_post_id(self, post_id):
        comments , comments_xmltext= self._download_comments(post_id)
        #
        logging.info("Loaded %s comments for %s post", len(comments), post_id)
        # делаем html фрейм с комментариями к посту
        comment_data , comment_etree = _make_comment_html_from_xml(comments_xmltext)
        #
        # todo сохранить это куда то например в zip перед упаковкой
        json_s, json_obj = _make_comment_links_json(comments_xmltext)
        # делаем сам пост , чтобы отсечь все лишнее
        post_data , post_height, just_head_data = get_post_html_uft8(self._make_post_url(post_id))
        #post_data_id = app.add_data(post_data)

        post_etree = fromstring(post_data)
        just_head = fromstring(just_head_data)
        for_delete = []
        for el in for_delete:
            p = el.getparent()
            if bool(p):
                p.remove(el)
        #
        # соединим это вместе
        postcontainer = etree.Element("div");
        comment_etree.find('body').insert(0, postcontainer)
        for el in post_etree.xpath('//img[@data-src]'):
            el.set('src', el.get('data-src'))
            el.set('style', "opacity: 100;")
        for el in just_head.findall('.//')[1:]:
            comment_etree.find('head').append(el)
        for el in [ i for i in post_etree[0]]:  # дополнить body
            postcontainer.append(el)
        s = etree.tostring(comment_etree, method='html')
        #f = open('summ_post_and_comm.html', 'wb'); f.write(s.encode('utf-8')); f.close()
        #
        # серфим суммарный документ
        summ_post_and_comm = app.add_data(s.encode('utf-8'))
        # по этому url будет брать wget ресурсы
        url = 'http://localhost:{port}/data?id={}'.format(summ_post_and_comm, port=WGET_PORT)
        #
        # start wget process  https://gist.github.com/dannguyen/03a10e850656577cfb57
        slug = 'pikabu_discuss_{}'.format(post_id)
        wget_whole_page(TMP_DIR, slug, url)
        os.rename( '{0}/{1}/localhost:{2}/data?id={3}.html'.format(TMP_DIR, slug, WGET_PORT, summ_post_and_comm),
                   '{0}/{1}/localhost:{2}/index.html'.format(TMP_DIR, slug, WGET_PORT))
        #  прочитаем главный файл и немного его перезапишем
        content = None
        with open('{0}/{1}/localhost:{2}/index.html'.format(TMP_DIR, slug, WGET_PORT), 'r') as content_file:
            content = content_file.read()
            # немного заменил содержимое и запишем в другое место
            content2 = re.sub(r'\.\./(.*?[\"\)\'\>])', 'discuss_resource?slug={0}&path=\g<1>'.format(slug), content)
            content2 = re.sub(r'http:\/\/localhost:{}\/static'.format(WGET_PORT), '/static', content2)
            content2 = mark_tokens_in_etree(content2)
            with open('{0}/{1}/index.html'.format(TMP_DIR, slug), 'w') as content_file2:
                content_file2.write(content2)
        # сожмём содержимое
        #zip -rm Output folder1  folder2  file1
        command = 'zip -rm {1} ./ ; mv "{0}/{1}/{1}.zip" "{2}" ; rm -r {0}/{1}'.format(TMP_DIR, slug, MEDIA_DIR)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, cwd=os.path.join(TMP_DIR, slug)) #
        process.wait()
        #
        # удалить ресурс с серфинга
        app.remove_data(summ_post_and_comm)
        #
        return  content2


    # ok
    def _make_comments_download_url(self, post_id):
        url = "https://pikabu.ru/generate_xml_comm.php?id=" + str(post_id)
        return url

    def _make_comment_url(self, post_id, doc_id):
        return "https://pikabu.ru/story/" + str(post_id) + "?comment=" + doc_id
    # ok
    def _make_post_url(self, post_id):
        return "https://pikabu.ru/story/_" + str(post_id)

    # ok
    def _download_comments(self, post_id):
        url = self._make_comments_download_url(post_id)
        res_cont = self.downloader.download(url)
        comments = ET.fromstring(res_cont.encode('utf-8'))
        return comments, res_cont.encode('utf-8')

    # def _extract_content_from_elem(self, elem, sep=' '):
    #     content = ""
    #     for t in elem.itertext():
    #         content += t + sep
    #     return content

    # def enshure_that_dir_exists(self, dir):
    #     if os.path.exists(dir):
    #         if os.path.isdir(dir):
    #             return True
    #         else:
    #             logging.info('Dir path is alreasy exists (file: %s). Increasing dirname...', dir)
    #             self.current_subdir = self.current_subdir + 1
    #             self.current_dir = os.path.join(self._opts.out_dir, str(self.current_subdir))
    #             self.enshure_that_dir_exists(self.current_dir)
    #     else:
    #         os.mkdir(dir)

#################################################################################################
def process_docs(opts):
    procs = PikabuWithCommentsProcessor(opts)
    fetcher = FromFileFetcher(opts) # IdsGenerateFetcher(opts)
    process_items_simulteaniously(opts, fetcher, procs)
    
#################################################################################################

#   MAIN CODE
def discussion_pikabu_get_byurl(url):
    pass
    proc = PikabuWithCommentsProcessor({})
    return proc.__call__(url)

if __name__ == '__main__':
    #discussion_pikabu_get_byurl('https://pikabu.ru/story/na_khalyavu_uksus_sladkiy_7226424')
    #discussion_pikabu_get_byurl('https://pikabu.ru/story/vremya_menyaet_lyudey_7264733')
    discussion_pikabu_get_byurl('https://pikabu.ru/story/ya_devushka_i_ya_ne_ponimayu_togo_feminizma_kotoryiy_sushchestvuet_v_realiyakh_nashego_obshchestva_6561974')
