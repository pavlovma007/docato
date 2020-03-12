#!/usr/bin/env python
# -*- coding:utf-8 -*-
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from lxml import etree
from lxml.html.soupparser import fromstring

browser = webdriver.PhantomJS(service_log_path='/var/log/ghostdriver.log')

# экспортируемая функция,
def get_post_html_uft8(url):
	browser.get(url)

	# ожидаем прогрузки и js
	delay = 30 # seconds
	try:
		myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.ID, 'comments')))
		print("Page is ready!")
	except TimeoutException:
		print("Loading took too much time!")
	driver = browser
	driver.set_window_size(1000, 550)
	# удаляем лишнее со страницы
	node = driver.find_element_by_xpath("//div")
	script = "arguments[0].insertAdjacentHTML('afterEnd', arguments[1])"
	driver.execute_script(script, node, '''
	<script>
	window.addEventListener("DOMContentLoaded", function(e) {
		document.querySelector('header').remove();
		document.querySelector('.app__inner').style.paddingTop=0;
		document.querySelector('.sidebar').remove();
		document.querySelector('.page-story__comments').remove();
		document.querySelector('.stories-feed__message').remove();
		document.querySelector('.section-hr').remove();
		document.querySelector('.page-story__cedit').remove();
		document.querySelector('.page-story__similar').remove();
		document.querySelector('.page-story__placeholder').remove();
		document.querySelector('div.story__footer').remove();
		document.querySelector('.stories-feed__message').remove();
		document.querySelector('footer').remove();
		document.querySelector('.main').style.width = '100%';
		document.querySelector('.app__inner').style.maxWidth= '100%'; 
    });
	var timestamp = new Date().getTime();
	document.getElementsByTagName('img').forEach(function(img){
		img.src = img.src+'?t='+timestamp;
	});


    window.name = 'neediframeresize';       
	</script>
	''')
	# получаем то, что получилось
	s = driver.execute_script('return document.getElementsByTagName("html")[0].outerHTML')
	height = driver.execute_script('return document.getElementsByClassName("page-story__story")[0].scrollHeight')
	just_story = driver.execute_script('return document.getElementsByClassName("story__content-inner")[0].outerHTML')
	just_head =  driver.execute_script('return document.getElementsByTagName("head")[0].outerHTML')
	title_text = driver.execute_script('return document.title')
	# перегоняем в html строку, чтобы немного подправить для быстрого отображения (no lazy)
	doc = fromstring(just_story) #driver.page_source  # s
	#meta = doc.xpath('//meta[@charset]')[0]
	#meta.set('charset', 'utf-8')
	#
	for div in doc.xpath("//div[contains(@class, 'image-lazy')]"):
		fig = div.getparent()
		rect = fig.findall('svg/rect')
		h = '';
		if rect:
			rect = rect[0]
			h = 'height:%s' % rect.get('height')
		else:
			svg = fig.xpath('*/svg')
			if bool(svg) :
				svg = svg[0]
				viewbox = svg.get('viewbox')
				viewbox =viewbox.split(' ')
				h = 'height:%s' % viewbox[3]
		fig.set('style', h)
	title = etree.Element('H3'); title.text = title_text; doc[0].insert(0, title )
	# перегоняем в строку
	s = etree.tostring(doc, method='html')
	#
	#with open('page.html', 'wb') as f:   f.write(s.encode('utf-8'))
	#
	return s.encode('utf-8'), height , just_head.encode('utf-8')

#driver.quit()
if __name__ == '__main__':
	s = get_post_html_uft8('https://pikabu.ru/story/_7226424')  # test
	#print(s)