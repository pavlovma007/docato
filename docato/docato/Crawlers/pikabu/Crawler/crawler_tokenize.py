#!/usr/bin/env python
# -*- coding:utf-8 -*-

import xml.etree.ElementTree as ET
import lxml.html
from lxml import etree
from lxml.html.soupparser import fromstring
import re

_badtags = set(["script", 'style'])
_have_a_chars = re.compile(r'\w', re.UNICODE)
_splitter_chars = re.compile(r'[\s,]', re.UNICODE)

def mark_tokens_in_etree(html_text) : # etree doc
	token_counter = 0  # это счетчик
	#
	html = fromstring(html_text)
	body = html.find('body')
	elements = [ i  for i in body.xpath('//*') if bool(i.text) and i.text!='' and i.text!='\n']
	for el in elements:
		if el.tag.lower() in _badtags :
			continue
		if el.get("class") and ( 'isa_control' in el.get("class") ):
			continue
		# тест есть ли тут буквы
		text = el.text
		#if _have_a_chars.match(text)!=None:
		# разобьем на слова, разделителяи идущие подряд заменим на один пробел
		#text = re.sub(r'[\s,]+', ' ', text)
		text_l = text.split(' ')
		token_counter = _subdiv_element_text_to_marked_tokens(el, text_l, token_counter)
		el.text = ''  # больше этот текст не нужен ... потому что будет тогда дублирование
		#print(el.text)
	s = etree.tostring(html,method='html')
	#with open('/home/mp/SATEK/razmetchik/crawler_for_v1/1/test.html', 'w') as f : f.write( etree.tostring(html,method='html')) ;f.close()
	#pass
	return s


def _subdiv_element_text_to_marked_tokens(el, text_l, counter):
	i = counter
	span = etree.Element('span')
	el.insert(0,span)
	for t in text_l:
		token = etree.Element('span', {"class": "chunk token_{}".format(i), "data-token-id":"{}".format(i), })
		token.text = t
		token.append(etree.Entity('nbsp'))
		span.append( token )
		span.append(etree.Entity('shy'))
		i += 1
	return i

# test  ( tdd )
if __name__ == '__main__':
	with open('crawler_for_v1/1/index.html', 'r') as f:
		data = f.read()
		mark_tokens_in_etree(data)