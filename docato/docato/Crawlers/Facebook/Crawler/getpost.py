#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys
import time

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

		const all = document.querySelectorAll('*');

		// post text : data-ad-preview="message"
		var postText = null, postElem = null; 
		for (let elem of all) {
			if(elem.getAttribute('data-ad-preview') && elem.getAttribute('data-ad-preview')=="message"){
				postElem = elem;
				postText = elem.textContent;
				break;
			}
		}


		/*
			поиск элемента с текстом : "Показать ещё 14 комментариев" и кликнуть его 
		*/

		var open_comments = null;
		for (let elem of all) {
		  if(elem.textContent && elem.textContent.startsWith("Показать ещё")){
			//console.log(elem);
			open_comments = elem; // last
		  }
		  //console.log(elem.textContent);
		}
		if(open_comments)
			open_comments.click();

		/*
			нажать все кнопки div[role="button"]  с текстом "Ещё"  чтобы подгрузить коментарии целиком
		*/
		// список комментариев  ul -> li   внутри третьего родителя текста поста
		setTimeout(function(){
			//let T = postElem.parentNode.parentNode.parentNode
			let commentElements = document.querySelectorAll('.cu .cv')
			for(let cei in commentElements){
				let ce=commentElements[cei];
				if(!!ce.querySelector){
					let escho = ce.querySelector('div > div > div:nth-child(2) > div > div > div > div > div > div > div:nth-child(2)');
					//console.log(ce, escho);
					if(escho && escho.textContent.endsWith("Ещё") ){
						let span_button = ce.querySelector('div > div > div:nth-child(2) > div > div > div > div > div > div > div:nth-child(2) div[role="button"]');
						span_button.click();
					}
				}
			}
			
			/* 	перемещаем role="article" в role="main" при этом удаляем остальное
				data-pagelet="root"  удаляем
			*/
			// ищем первый main. 
			var main = null;
			for (let elem of all) {
				if(elem.getAttribute('role') && elem.getAttribute('role')=='main'){
					main = elem
					break;
				}
			}
			// ищем article
			var article = null;
			for (let elem of all) {
				if(elem.getAttribute('role') && elem.getAttribute('role')=="article"){
					article = elem
					break;
				}
			}
			document.body.append(article);
			// ищем мусор и удаляем 
			for (let elem of all) {
				if(elem.getAttribute('data-pagelet') && elem.getAttribute('data-pagelet')=="root"){
					if(elem.parentNode)
						elem.parentNode.remove(elem);
					break;
				}
			}


			/* 	получим список комментариев, текст автор, рейтинг, когда, 
			*/
			comments = []; // тут будут коменты
			let commentElements2 = document.querySelectorAll('.cu .cv')
			for(let ci=0; ci<document.querySelectorAll('.cu .cv').length; ci+=1){
				try{
					let c = document.querySelectorAll('.cu .cv')[ci];
					document.body.setAttribute('data-com', ''+ci );
					//console.log(c);
					if(!!c){
						//let info = c.querySelector('h3').textContent ; //chrome c.querySelector('[aria-label]').getAttribute('aria-label');
						let username= c.querySelector('h3').textContent; // chrome: tmp2.querySelector('span').textContent;
						let commentText = c.querySelector('div[class] ').textContent; // chrome tmp2.querySelector('div:nth-child(2)').textContent;
						// let userurl=  ''; // chrome c.querySelector('a').href;
						//let tmp2 = c.querySelector('div > div > div:nth-child(2) > div > div > div > div > div > div');
						let when = c.querySelector('abbr').textContent; // chrome c.querySelector('ul > li:nth-child(2)').textContent;
						
						let comment = {	
							//info: info,  
							//userurl:userurl,   
							text:commentText, 
							name:username, 
							when:when
						};
						document.body.setAttribute('data-comment', JSON.stringify(comment) );
						comments.push(comment);
					}				
				}catch(e){}
			}
			// закинем в body инфу о коментариях
			document.body.setAttribute('data-comments', JSON.stringify(comments) );

		},5000);

    });

    window.name = 'neediframeresize';       
	</script>
	''')
	# ждём пока сработаю все асинхронные скрипты (3-4 сек)
	time.sleep(8)
	# получаем то, что получилось
	s = driver.execute_script('return document.getElementsByTagName("html")[0].outerHTML')
	height = driver.execute_script('return document.body.scrollHeight')
	just_story = driver.execute_script('return document.querySelector("#m_story_permalink_view  p").textContent ')
	title_text = driver.execute_script('return document.title')

	# получим комментарии
	comments = []
	for i in range(int(driver.execute_script('return document.querySelectorAll(".cu .cv").length'))):
		com = driver.execute_script('return document.querySelectorAll(".cu .cv")')[i]
		try:
			username = com.find_elements_by_css_selector('h3')[0].text
			text = com.find_elements_by_css_selector('div[class]')[0].text
			moment = com.find_elements_by_css_selector('abbr')[0].text
			comments.append({"text":text, "when":moment, "username":username})
		except IndexError:
			pass


	#authors = driver.execute_script(
	#	"return document.getElementsByClassName('user__nick story__user-link')[0].getAttribute('href')")

	# перегоняем в html строку, чтобы немного подправить для быстрого отображения (no lazy)
	doc = fromstring(s)
	#
	# перегоняем в строку
	s = etree.tostring(doc, method='html')
	#
	#with open('page.html', 'wb') as f:   f.write(s.encode('utf-8'))
	#
	return s.encode('utf-8'), height, comments

if __name__ == '__main__':
	#s = get_post_html_uft8('https://www.facebook.com/groups/601430053212107/permalink/705945026093942/?comment_id=924229957598780&_rdc=1&_rdr')  # test dd
	#print(s)
	pass
