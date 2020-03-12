#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

import lxml.html
import sys, re


class PostWithCommentsXml(object):
    def __init__(self, id, root_name="post"):

        self._xml = ET.fromstring(
            "<?xml version='1.0' encoding='UTF-8'?><%s id='%s'></%s>" % (root_name, id, root_name))
        
        self._xml.set('xmlns:lj', 'http://www.w3.org/1999/xhtml')
        
        self._xml.append(ET.Element('meta'))
        self._xml.append(ET.Element('content'))
        self._xml.append(ET.Element('comments'))

        self.default_tags = {'crawled_comments_count', 'crawled_time'}
        self.len_content = 0
        
        self.br_re_pat = re.compile('<br(\s)*?/?>')
        self.anytag_re_pat = re.compile('<([^>])+?>')

    def add_meta(self, tag, content):
        if tag not in self.default_tags:
            self._add_meta(tag, content)

    def _add_meta(self, tag, content):
        self._xml.find('./meta').append(ET.Element(tag))
        self._xml.find('./meta/%s' % tag).text = content

    def add_comment(self, id, parent, content, additional=None):
        comment_elem = self._create_comment_elem(id, parent, content, additional)
        if (parent == 0 or parent == "0"):
            self._xml.find('.//comments').append(comment_elem)
        else:
            self._xml.find(".//comment[@id='%s']" % parent).append(comment_elem)

    def _create_comment_elem(self, id, parent, content, additional):
        comment = ET.Element('comment')

        comment.set("id", str(id))
        comment.set("parent", str(parent))

        content_el = ET.Element('content')

        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&', '&amp;')
        # content = content.replace('"', '&quot;')
        # content = content.replace("\n", " ")
        # content = self.br_re_pat.sub("\n", content)
        content = self.anytag_re_pat.sub(" ", content)
        # content = content.replace("\n", " <br/> ")
        
        content_el.text = content
        comment.append(content_el)

        for attr in additional:
            comment.set(attr, str(additional[attr]))

        return comment

    def set_content(self, content):
        self._xml.find('./content').text = content
        self.len_content = len(content)

    def comments_count(self):
        return len(self._xml.findall(".//comment"))

    def save(self, filepath):
        self._add_meta("len_content_utf_8", str(self.len_content))
        self._add_meta("crawled_comments_count", str(self.comments_count()))
        self._add_meta("crawled_time", str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        xmlstr = minidom.parseString(ET.tostring(self._xml)).toprettyxml(indent="   ")
        with open(filepath, "w") as f:
            if ((3,) > sys.version_info):   # wtf ? мы что не знаем версию и окружение в котором работаем ?
                f.write(xmlstr.encode('utf-8'))
            else:
                f.write(xmlstr)

        logging.info("Successfully saved %s", filepath)


class PostWithCommentsXmlHandler(object):
    def __init__(self, xml_path, h=False):
        with open(xml_path, 'r') as f:
            x = f.read()
            if h: self._h = lxml.html.fromstring(x)
            self.post = ET.fromstring(x)
            self.id = self.post.attrib['id']

    def get_meta(self, meta):
        t = self.post.find("./meta/{}".format(meta))
        if hasattr(t, 'text'):
            return t.text if t.text is not None else ""
        else:
            return ""

    def content_len(self):
        content = self.post.find("./content").text
        if isinstance(content, (unicode)):
            return len(content)
        else:
            return 0

    def title_len(self):
        return len(self.get_meta('title'))

    def comments_count(self):
        return len(self.post.findall(".//comment"))

    def comments_lens(self):
        return [len(comment.text) if comment.text is not None else 0 for comment in
                self.post.findall("./comments//content")]

    def get_content(self, with_comments=True, only_comments=False):
        xp = "//content/text()" if with_comments else "./content/text()"
        xp = "//comments//content/text()" if only_comments else xp
        return _post2text(self._h, xp)


def _post2text(_h, xp):
    return '\n'.join([t_ for cont_item in _h.xpath(xp)
                      for t_ in _cont_from_elem(cont_item)])


def _cont_from_elem(elem):
    try:
        return lxml.html.fromstring(elem.strip()).xpath("//text()")
    except Exception as e:
        return ['']
