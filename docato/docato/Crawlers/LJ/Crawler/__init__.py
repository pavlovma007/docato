#!/usr/bin/env python
# -*- coding:utf-8 -*-
#import docker
#import datetime
#import collections
import json

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
from getpost import get_post_page
from crawler_tokenize import mark_tokens_in_etree
from wget_whole_page import wget_whole_page
from contextlib import closing
from django.conf import settings

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 4102))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

WGET_PORT = find_free_port() # settings.WGET_PORT             # порт на котором можно серфить внутри контейнера, это другой порт не "для снаружи"

MEDIA_DIR = '/docato_data/media' #settings.MEDIA_ROOT
TMP_DIR = '/tmp' # settings.TMP_DIR

# сервиc переработанный html дискуссии, чтобы wget забрал whole page с этого адреса и переделал ссылки на локальные
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

class LJWithCommentsProcessor(object):
    def __init__(self, opts=None):
        self.downloader = Downloader(delay=0.2)
        self.post_id_re_pat = re.compile(r'(\d+)$')

    def __call__(self, item):
        # обрежем и возьмем только базовую часть , чтобы начать с петвой страницы
        url = item
        if '?' in url:
            url = url.split('?')[0]
        return self._process_post(url)

    def _process_LJ_page(self, page_url):
        post_data, comments_json_o = get_post_page(page_url)
        whole_etree = fromstring(post_data)

        comment_element = whole_etree.find('.//div[@id="comments"]')
        pages_urls = []
        try:
            pages = whole_etree.find_class('b-pager-first')[0]
            pages_urls = [elem.attrib['href'] for elem in pages.iter() if elem.tag is 'a' and elem.attrib['href']]
        except :
            pass
        # удалить не нужный "мусор"
        header = whole_etree.find('.//header');
        header.getparent().remove(header)
        # вернуть нужное
        return whole_etree, comment_element, comments_json_o, pages_urls
    # ok
    def _process_post(self, post_url):
        # делаем сам пост - первая страница
        whole_etree, comment_element, comment_json, pages_urls = self._process_LJ_page(post_url)
        base_url = post_url.split('livejournal.com')[0]+'livejournal.com';
        # получили 1) сама страница с постом 2)  url для следующих страниц, 3) comment_json этой страницы 4) comment element container
        # запросить другие страницы , при этом добавить коментарии в базовую страницу, дополнить список comment_json
        visited = set(post_url)
        for link in pages_urls[1:]:
            new_url=base_url+link;
            if new_url not in visited:
                next_page_etree, ce, cj, pu = self._process_LJ_page(new_url)
                visited.add(new_url)
                # добавить в общее whole_etree коментарии
                comment_element.append(ce)
                # пополнить comment_json
                comment_json += cj


        # серфим суммарный документ, чтобы его скачать (токенизация ниже)
        s = etree.tostring(whole_etree, method='html')
        summ_post_and_comm = app.add_data(s.encode('utf-8'))
        # по этому url будет брать wget ресурсы
        url = 'http://localhost:{port}/data?id={}'.format(summ_post_and_comm, port=WGET_PORT)
        #
        slug = 'lj_discuss_{}'.format( re.sub('/','_',post_url) )
        wget_whole_page(TMP_DIR, slug, url)
        os.rename( '{0}/{1}/localhost:{2}/data?id={3}.html'.format(TMP_DIR, slug, WGET_PORT, summ_post_and_comm),
                   '{0}/{1}/localhost:{2}/index.html'.format(TMP_DIR, slug, WGET_PORT))
        #  прочитаем главный файл и немного его перезапишем
        with open('{0}/{1}/localhost:{2}/index.html'.format(TMP_DIR, slug, WGET_PORT), 'r') as content_file:
            content = content_file.read()
            content2 = re.sub(r'\.\./(.*?[\"\)\'\>])', 'discuss_resource?slug={0}&path=\g<1>'.format(slug), content)
            content2 = re.sub(r'http:\/\/localhost:{}\/static'.format(WGET_PORT), '/static', content2)
            # немного заменил содержимое и запишем в другое место
            content2 = mark_tokens_in_etree(content2)
            with open('{0}/{1}/index.html'.format(TMP_DIR, slug), 'w') as wholepage:
                wholepage.write(content2)
        # сохраним все коментарии
        with open('{0}/{1}/comments.json'.format(TMP_DIR, slug), 'w') as wholepage:
            wholepage.write(json.dumps(comment_json))
        # сожмём содержимое
        #zip -rm Output folder1  folder2  file1
        command = 'zip -rm {1}.zip ./ ; mv "{0}/{1}/{1}.zip" "{2}" ; rm -r {0}/{1}'.format(TMP_DIR, slug, MEDIA_DIR)
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
# def process_docs(opts):
#     procs = PikabuWithCommentsProcessor(opts)
#     fetcher = FromFileFetcher(opts) # IdsGenerateFetcher(opts)
#     process_items_simulteaniously(opts, fetcher, procs)
    
#################################################################################################

#   MAIN CODE
def discussion_LJ_get_byurl(url):
    proc = LJWithCommentsProcessor({})
    return proc.__call__(url)

if __name__ == '__main__':
    #text = discussion_LJ_get_byurl('https://historical-fact.livejournal.com/12651.html?page=2')
    #text = discussion_LJ_get_byurl('https://haspar-arnery.livejournal.com/565738.html?media&utm_source=recommended&utm_content=main_block')
    text = discussion_LJ_get_byurl('https://tapkin.livejournal.com/3054738.html')
    pass