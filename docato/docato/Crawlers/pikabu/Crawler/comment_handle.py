#!/usr/bin/env python
# -*- coding:utf-8 -*-
from lxml import etree
from lxml.html.soupparser import fromstring
from jinja2 import Template
import json as json


def _make_comment_links_json(xml_text):
	doc = etree.XML(xml_text)
	comments = {}
	comment_parents = {}  # anwser -> parent
	root_comments = []
	for c in doc.xpath('//comment'):
		cj = {}
		cj["id"] = c.get("id");
		cj["nick"] = c.get("nick");
		cj["date"] = c.get("date");
		cj["answer"] = c.get("answer");
		cj["rating"] = c.get("rating");
		cj["text"] = c.text;
		comments[cj["id"]] = cj
		if cj["answer"] != '0':
			comment_parents[cj["id"]] = cj["answer"]
		else:
			root_comments.append(cj)

	obj = {"comments": comments, "comment_parents": comment_parents, "root_comments": root_comments}
	s = json.dumps(obj, encoding='utf-8')
	print(s)
	return s, obj


    # ok
def _make_comment_html_from_xml(xml_text):
        doc = etree.XML(xml_text)
        # сделаем иерархию, а не плоскую схему со ссылками
        def modify_for_hierarchical_doc(doc):
            for each_not_root_comment in doc.xpath("//comment[@answer != '0']" ):
                p_id = each_not_root_comment.get('answer')
                parent = doc.xpath("//comment[@id = '%s']" %  p_id)[0]
                parent.append(each_not_root_comment);
            return etree.tostring(doc), doc
        newdoc, doc = modify_for_hierarchical_doc(doc)
        # преобразуем к виду html
        template = Template('''
{% macro show_comment(c) %}
    <div class="comment_body" id="{{c.get('id')}}" style="position: relative;">
      <span class="isa_control">Author: </span><span class="comment_author"><b  class="isa_control">{{c.get('nick')}}</b></span>,
      <span  class="isa_control">Date:   </span><span class="comment_date"><b  class="isa_control">{{c.get('date')}}</b></span>
      (<span class="comment_answerto isa_control"><a href='#' onclick='$(".comment_body[id={{c.get('answer')}}]")[0].scrollIntoView(); event.preventDefault();'><i  class="isa_control">answer_to {{c.get('answer')}}</i></a> 
      </span><span class="comment_rank"><i  class="isa_control">rank {{c.get('rating')}}</i></span>)
      <div>{{c.text}}</div>
      {% if len(c.xpath('comment'))>0 %}
        {% for c in c.xpath('comment') %}
            {{show_comment(c)}}
        {% endfor %} 
      {%endif%}
    </div>
{% endmacro %}
<html>
<head>
<link href="/static/docato/css/tree.css" rel="stylesheet" type="text/css"/>
<script src="/static/docato/js/jquery-1.9.1.js" type="text/javascript"></script>
<script src="/static/docato/js/tree.js" type="text/javascript"></script>
<style>.comment_body{
    margin-left: 15px;
    border-left-style: solid;
    border-left-color: burlywood;
    padding-left: 5px;
}</style>
</head>
<body>
{% for c in comments %}
    {{show_comment(c)}}
{% endfor %} 
<script>window.name = 'neediframeresize';</script>
</body></html>''')
        s = template.render(comments=doc, len=len)
        #
        # опять преобразуем в xml чтобы дальше обработать
        doc = fromstring(s)
        #сделаем нормально картинки
        for i in doc.xpath('//figure/div/a/img'):
            # i = img
            fig = i.getparent().getparent().getparent()
            rect = fig.xpath('//rect')[0]
            w = rect.get('width')
            h = rect.get('height')
            i.set('width', w);i.set('height', h); i.set('src', i.get('data-src'))
            div = fig.getparent()
            div.append(i) #
            div.remove(fig)
        # обработаем видео
        for i in doc.xpath('//figure/div[@class="comment-external-video__content"]'):
            fig = i.getparent().getparent()
            s_link = i.get('data-external-link')  # todo
            s_img = i.get('data-thumb')
            rect = fig.xpath('//rect')[0]
            w = rect.get('width')
            h = rect.get('height')
            i.set('width', w);i.set('height', h); i.set('src', s_img )
            div = fig.getparent()
            cont = etree.SubElement(div, 'div', {"style":"position:relative;height:{}".format(h) });
            img=etree.SubElement(cont,'img', i.attrib);
            a = etree.SubElement(div, 'a', {'href':s_link, 'target': "__blank"} ) ; a.text = s_link;
            etree.SubElement(div,'br');
            div.remove(fig) # test

        s = unicode( etree.tostring(doc, method='html') )
        # result_tree = transform(doc)
        # formatted_html = unicode(result_tree)
        # plain_text = etree.tostring(result_tree, encoding='unicode', method='text')

        #plain_html = etree.tostring(result_tree, encoding='unicode', method='xml')
        #f = open('test.html','wb') ; f.write(s.encode('utf-8').strip()); f.close() # TODO remove
        #
        #  сделать serve html в фоне так, чтобы потом его убить
        # запустить в фоне html
        return s.encode('utf-8').strip(), doc
