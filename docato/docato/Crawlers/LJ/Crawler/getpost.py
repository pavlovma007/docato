#!/usr/bin/env python
# -*- coding:utf-8 -*-
import json
import re
import sys
import time
import urllib2

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from lxml import etree
from lxml.html.soupparser import fromstring

browser = webdriver.PhantomJS(service_log_path='/var/log/ghostdriver.log')

# экспортируемая функция,
def get_post_page(post_page_url):
	browser.get(post_page_url)

	# ожидаем прогрузки и js
	#time.sleep(5);
	delay= 30
	try:
		myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.TAG_NAME,"body")))
		print("Page is ready!")
	except TimeoutException:
		print("Loading took too much time!")
		#
		# raise it again
		t, v, tb = sys.exc_info()
		raise t, v, tb

	driver = browser
	driver.set_window_size(1000, 550)
	# удаляем лишнее со страницы
	node = driver.find_element_by_xpath("//div")
	script = "arguments[0].insertAdjacentHTML('afterEnd', arguments[1])"
	driver.execute_script(script, node, '''
	<script>
	window.addEventListener("DOMContentLoaded", function(e) {
		// выберем все сообщения
		jQuery('input.b-leaf-actions-checkbox[type="checkbox"]').prop('checked', 1);
		// кликнуть кнопку развернуть
		jQuery('button[value="expand"]').click();
		jQuery('li.b-leaf-actions-expand a').click(); // для другого способа верстки
		
		// сам пост развернуть 
		post_elem = document.querySelector('article.entry-content');
		// если там есть сылка для распахнуть, то нажать ее 
		post_expand = post_elem.querySelector('.ljcut-link-expand');
		if(!!post_expand){
			post_expand.click()
		}
    });
	</script>
	''')
	# ждём пока сработаю все асинхронные скрипты (3-4 сек)
	time.sleep(30)
	# получаем то, что получилось
	s = driver.execute_script('return document.getElementsByTagName("html")[0].outerHTML')

	# получим комментарии
	# в коде страницы есть строка которая начинается с такого текста: (ниже) и это json с ними
	# Site.page = {"
	data = urllib2.urlopen(post_page_url)
	for line in data:  # files are iterable
		if 'Site.page = {"' in line:
			comment_json = re.sub('Site.page = ', '', line)
			comment_json = comment_json[:-2]
			comment_json_o = json.loads(comment_json)
			try:
				comment_json_o = comment_json_o['comments']
			except KeyError:
				pass
			#
			try:
				comment_json_o = comment_json_o['LJ_cmtinfo']
			except KeyError:
				pass
			break


	# перегоняем в html строку, чтобы немного подправить для быстрого отображения (no lazy)
	#doc = fromstring(s)
	# перегоняем в строку
	#s = etree.tostring(doc, method='html')
	#
	#with open('page.html', 'wb') as f:   f.write(s.encode('utf-8'))
	#
	return s.encode('utf-8'), comment_json_o

if __name__ == '__main__':
	pass
