# -*- coding: utf8 -*-

import os
import pymysql

SUBJECT_ID = 25
con1 = pymysql.connect('localhost', 'root', 'pwd', 'docato') # система 1
con2 = pymysql.connect('localhost', 'admin', 'test', 'docato', port=3307) # система 2
#
cur1 = con1.cursor();
cur2 = con2.cursor();
P7_NO_CUE = '-20' # значение pcode для P7 у которого не привязан текстовый фрагмент

def listToDict(lst):
    op = {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}
    return op

def dprint(str):
	if False:   # печатать или нет команды удаления объектов
		print(str)

# tested
def sys2_get_document(con, doc_id):
	cur = con.cursor()
	r = cur.execute('select "url",url,"title",title,"authors",authors,"content_type",content_type,"source_file",source_file,"converted_content",converted_content,"state",state,"load_time",load_time,"subject_id",subject_id from docato_document where id={0};'.format(doc_id))
	data = cur.fetchone()
	if bool(data):
		dic = listToDict(data)
		#print(dic)
		#  {'url': '', 'title': '72305', 'authors': '', 'content_type': 'xml', 'source_file': 'src/72305.xml', 'converted_content': 1, 'state': 1, 'load_time': datetime.datetime(2019, 4, 22, 16, 5, 23, 745314), 'subject_id': 1}
		return dic,data
	else:
		print('no document with id',doc_id)
# tested
def insert_discuss(con1, cur1, url, title, authors, content_type, source_file, converted_content, state, load_time, subject_id):
	#cur1 = con1.cursor()
	r = cur1.execute('INSERT into docato_document(url, title, authors, content_type, source_file, converted_content, state, load_time, subject_id) '+
				'values("{0}", "{1}", "{2}", "{3}", "{4}", "%s", "{5}", "{6}", {7});'.format(url, title, authors, content_type, source_file, state, load_time, subject_id)
				, (converted_content))
	id1 = con1.insert_id()
	dprint('delete from docato_document where id='+str(id1)+';')
	return id1
# tested
def sys_get_fragments_of_document(cur, doc_id):
	cur.execute('select id, user_id, document_id, date, name, is_all_text from docato_fragment where document_id={};'.format(doc_id))
	data = cur.fetchall()
	fragments = []
	for i in data :
		f = {"id":i[0], "name":i[4], "user_id":i[1], "document_id":i[2], "date":i[3], "is_all_text":i[5]}
		fragments.append(f)
		cur.execute('select start_char, end_char, comment_id, nickname from docato_fragmentcontent where fragment_id={0} ;'.format(i[0]))
		fragmentcontent = cur.fetchone();
		f["fragmentcontent"] = fragmentcontent

	return fragments

def create_fragment(con1, cur, doc_id, pname):
	#print('doc_id, pname, value',doc_id, pname, value)
	cur.execute('select id from docato_frametype where name = "{0}"'.format(pname))
	frametype = cur.fetchone()[0]
	#print('frametype',frametype)
	cur.execute('insert into docato_frame(doc_id, type_id, name) values({0}, {1}, "{2}")'.format(doc_id, frametype, pname+'__#'))
	frame = con1.insert_id();
	dprint('delete from docato_frame where id='+str(frame)+';')
	return frame, frametype

def fill_params_of_frame(con1, cur, frame, frametype, pname, key, value, start,end,text):
	cur.execute("select id from docato_baseslot where frame_type_id = {0} and name='{1}' ".format(frametype, key))
	baseslot = cur.fetchone()[0]
	#
	cur.execute("select id from django_content_type where model = 'integerslot' and app_label='docato' ;");
	polymorphic_ctype_id_intSlot = cur.fetchone()[0];
	cur.execute("select id from django_content_type where model = 'integerslotvalue' and app_label='docato' ;");
	polymorphic_ctype_id_intSlotValue = cur.fetchone()[0];
	cur.execute("select id from django_content_type where model = 'classlabelslotvalue' and app_label='docato' ;");
	polymorphic_ctype_id_classlabelSlotValue = cur.fetchone()[0];
	classLabel = polymorphic_ctype_id_intSlotValue if pname != 'P3' else polymorphic_ctype_id_classlabelSlotValue
	#
	cur.execute('insert into docato_baseslotvalue(frame_id,polymorphic_ctype_id,slot_id) values({0}, {1}, {2})'.format(frame, classLabel, baseslot))
	bsv = con1.insert_id();
	dprint('delete from docato_baseslotvalue where id='+str(bsv)+';')
	#
	cur.execute('insert into docato_slotvaluewithcue(baseslotvalue_ptr_id) values({0})'.format(bsv))
	dprint('delete from docato_slotvaluewithcue where baseslotvalue_ptr_id='+str(bsv)+';')
	#
	if pname!='P3':
		cur.execute('insert into docato_integerslotvalue(slotvaluewithcue_ptr_id, value) values({0}, {1})'.format(bsv, value))
		dprint('delete from docato_integerslotvalue where slotvaluewithcue_ptr_id='+str(bsv)+';')
	else:
		# if P3 classlabel
		cur.execute('insert into docato_classlabelslotvalue(slotvaluewithcue_ptr_id, value) values({0}, "-")'.format(bsv))
		dprint('delete from docato_classlabelslotvalue where slotvaluewithcue_ptr_id='+str(bsv)+';')
	#
	if value != int(P7_NO_CUE):  # если надо добавить тектовый фрагмент, то добавляем, иначе - не надо т.к. не задано
		cur.execute('insert into docato_cue(slot_value_id, start, end, text) values({0}, {1}, {2}, "{3}")'.format(bsv,start,end,text))
		dc =  con1.insert_id();
		dprint('delete from docato_cue where id='+str(dc)+';')
	return bsv
	

def correct_p7_fields(data):
	data = list(data)
	keys = set()
	for row in data:
		pname, pcode, ptext = row
		keys.add(pname)
	if 'Р7.1. Пробл_Автор' in keys or 'Р7.2. Пробл_Состояние' in keys or 'Р7.3. Пробл_Причины' in keys or 'Р7.4. Пробл_План' in keys or 'Р7.5. Пробл_Адресат' in keys:
		# надо дополнять т.к. имеются P7
		if 'Р7.1. Пробл_Автор' not in keys:
			data.append( ('Р7.1. Пробл_Автор', -10, P7_NO_CUE) )
		if 'Р7.2. Пробл_Состояние' not in keys:
			data.append( ('Р7.2. Пробл_Состояние', -10, P7_NO_CUE) )
		if 'Р7.3. Пробл_Причины' not in keys:
			data.append( ('Р7.3. Пробл_Причины', -10, P7_NO_CUE) )
		if 'Р7.4. Пробл_План' not in keys :
			data.append( ('Р7.4. Пробл_План', -10, P7_NO_CUE) )
		if 'Р7.5. Пробл_Адресат' not in keys:
			data.append( ('Р7.5. Пробл_Адресат', -10, P7_NO_CUE) )
	else:
		pass
	return tuple(data)

def fill_parameters_of_frame(fragment_id :int, doc_id :int, start, end, text): # в системе 2 текск "cue" привязан к фрагменту а не к параметру
	# тут будут фрагменты, создаваемые динамически по требованию, чтобы в них заполнять несколько слотов
	fragments_id_dic = { "P1": None, "P2": None, "P3": None, "P4": None, "P5": None, "P6 (konflict_sotrud)": None, "P7": None  }

	cur2.execute('select distinct t3.name, t2.name, t2.description from docato_fragment_parametervalues as t1 inner join docato_parametervalue as t2 on (t1.parametervalue_id=t2.id) inner join docato_parameter as t3 on (t2.parameter_id=t3.id) where fragment_id={0}'.format(fragment_id))
	data = cur2.fetchall()
	data = correct_p7_fields(data)
	for row in data: # строка - один параметр
		pname, pcode, ptext = row
		#print('pname, pcode, ptext',pname, pcode, ptext)
		if pname=='P1':
			#sys1_make_P1(con1, doc_id, pname, 'value', pcode, start, end, text)
			if not bool(fragments_id_dic["P2"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, pname)			# создадим сам фрагмент
				fragments_id_dic["P1"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P1"][0] , fragments_id_dic["P1"][1], pname, 'value', pcode, start,end,text)
		elif pname=='P2':
			#sys1_make_P2(con1,doc_id, pname, 'value', pcode, start,end,text)
			if not bool(fragments_id_dic["P2"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, pname)
				fragments_id_dic["P2"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P2"][0] , fragments_id_dic["P2"][1], pname, 'value', pcode, start,end,text)
		elif pname=='P3':
			#sys1_fill_param_key(con1, doc_id, pname, 'value', ptext, start, end, text)
			if not bool(fragments_id_dic["P3"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, pname)
				fragments_id_dic["P3"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P3"][0] , fragments_id_dic["P3"][1], pname, 'value', ptext, start,end,text)
		elif pname=='P4 (process_result)':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P4', 'process_result', v, start, end, text)
			if not bool(fragments_id_dic["P4"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P4')
				fragments_id_dic["P4"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P4"][0] , fragments_id_dic["P4"][1], 'P4', 'process_result', v, start,end,text)
		elif pname=='P4 (razd_druzh)':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P4', 'razd_druzh', v, start, end, text)
			if not bool(fragments_id_dic["P4"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P4')
				fragments_id_dic["P4"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P4"][0] , fragments_id_dic["P4"][1], 'P4', 'razd_druzh', v, start,end,text)
		elif pname=='P4 (sub_dom)':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P4', 'sub_dom', v, start, end, text)
			if not bool(fragments_id_dic["P4"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P4')
				fragments_id_dic["P4"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P4"][0] , fragments_id_dic["P4"][1], 'P4', 'sub_dom', v, start,end,text)
		elif pname=='P5':
			#sys1_make_P5(con1,doc_id, pname,'value', pcode, start,end,text)
			if not bool(fragments_id_dic["P5"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, pname)
				fragments_id_dic["P5"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P5"][0] , fragments_id_dic["P5"][1], pname, 'value', pcode, start,end,text)
		elif pname=='P6 (konflict_sotrud)':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, pname, 'value', v, start, end, text)
			if not bool(fragments_id_dic["P6 (konflict_sotrud)"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, pname)
				fragments_id_dic["P6 (konflict_sotrud)"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P6 (konflict_sotrud)"][0] , fragments_id_dic["P6 (konflict_sotrud)"][1], pname, 'value', v, start,end,text)
		elif pname=='Р7.1. Пробл_Автор':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P7', '1. Пробл_Автор', v, start, end, text)
			if not bool(fragments_id_dic["P7"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P7')
				fragments_id_dic["P7"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P7"][0] , fragments_id_dic["P7"][1], 'P7', '1. Пробл_Автор', v, start,end,text)
		elif pname=='Р7.2. Пробл_Состояние':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P7', '2. Пробл_Состояние', v, start, end, text)
			if not bool(fragments_id_dic["P7"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P7')
				fragments_id_dic["P7"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P7"][0] , fragments_id_dic["P7"][1], 'P7', '2. Пробл_Состояние', v, start,end,text)
		elif pname=='Р7.3. Пробл_Причины':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P7', '3. Пробл_Причины', v, start, end, text)
			if not bool(fragments_id_dic["P7"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P7')
				fragments_id_dic["P7"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P7"][0] , fragments_id_dic["P7"][1], 'P7', '3. Пробл_Причины', v, start,end,text)
		elif pname=='Р7.4. Пробл_План':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P7', '4. Пробл_План', v, start, end, text)
			if not bool(fragments_id_dic["P7"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P7')
				fragments_id_dic["P7"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P7"][0] , fragments_id_dic["P7"][1], 'P7', '4. Пробл_План', v, start,end,text)
		elif pname=='Р7.5. Пробл_Адресат':
			v = -10 if ptext=='unknown' else int(ptext)
			#sys1_fill_param_key(con1, doc_id, 'P7', '5. Пробл_Адресат', v, start, end, text)
			if not bool(fragments_id_dic["P7"]):
				frame, frametype = create_fragment(con1, cur1, doc_id, 'P7')
				fragments_id_dic["P7"] = (frame, frametype)
			bsv = fill_params_of_frame(con1, cur1, fragments_id_dic["P7"][0] , fragments_id_dic["P7"][1], 'P7', '5. Пробл_Адресат', v, start,end,text)
		else:
			print('какой то НЕИЗВЕСТНЫЙ ПАРАМЕТР =', pname)


def sys1_make_P1(con1, doc_id, pname, key, value,start, end, text):
	sys1_fill_param_key(con1, doc_id, pname, key, value, start, end, text) # обрабатывается аналогично, в значения value уходят code числа
def sys1_make_P2(con1, doc_id, pname, key, value,start, end, text):
	sys1_fill_param_key(con1, doc_id, pname, key, value, start, end, text) # обрабатывается аналогично, в значения value уходят code числа
def sys1_make_P5(con1, doc_id, pname, key, value,start, end, text):
	sys1_fill_param_key(con1, doc_id, pname, key, value, start, end, text) # обрабатывается аналогично, в значения value уходят code числа


def save_params(doc_id,fragments2):
	for f2 in fragments2:
		fc = f2["fragmentcontent"]
		start = 0
		end = 0
		text = '--not filled--'
		if fc:
			start = fc[0]; end = fc[1]
		#print('start,end', start,end)
		fill_parameters_of_frame(f2["id"], doc_id, start, end, text)
if __name__ == '__main__':
	with con2:
		cur2.execute('select docato_document.id from docato_fragment inner join docato_fragment_parametervalues on docato_fragment.id=fragment_id inner join docato_document on docato_document.id=docato_fragment.document_id group by docato_document.id;')
		sys2_documents = [i[0] for i in cur2.fetchall() ]
		print('sys2_documents=',sys2_documents)

		for d2 in sys2_documents: # d2 is a id (int)
			doc_dic, doc_tupple  = sys2_get_document(con2, d2)
			#print(doc_dic["url"])
			
			# вставляем документ в систему 1
			id1: int = insert_discuss(con1, cur1, doc_dic["url"], '_'+doc_dic["title"], doc_dic["authors"], doc_dic["content_type"], doc_dic["source_file"], doc_dic["converted_content"], doc_dic["state"], doc_dic["load_time"], SUBJECT_ID)
			#print('doc sys2', d2, ' sys1', id1)
			
			fragments2= sys_get_fragments_of_document(cur2 , d2 )
			#print(fragments2)
			#> fragments= [{'id': 33, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': None}, {'id': 34, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': None}, {'id': 35, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': None}, {'id': 36, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (388, 435, 7512932, 'ftyruoert')}, {'id': 37, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (461, 475, 7515748, 'sis_cia')}, {'id': 38, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (501, 514, 7516004, 'ftyruoert')}, {'id': 39, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (536, 663, 7554660, 'hanop')}, {'id': 40, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (685, 691, 7516516, 'e_d_w')}, {'id': 41, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (713, 713, 7575396, 'aliasy')}, {'id': 42, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (735, 739, 7524708, 'dafnyskills')}, {'id': 43, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (765, 793, 7531108, 'ext_1830888')}, {'id': 44, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (815, 841, 7531364, 'e_d_w')}, {'id': 45, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (867, 926, 7533924, 'ftyruoert')}, {'id': 46, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (948, 950, 7537252, 'e_d_w')}, {'id': 47, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (976, 1126, 7513188, 'sergey_as1976')}, {'id': 48, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1152, 1572, 7515492, 'sis_cia')}, {'id': 49, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1615, 1646, 7536996, 'kogemiaka_1')}, {'id': 50, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1668, 1826, 7540324, 'dmitry_sablin')}, {'id': 51, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1848, 1861, 7525476, 'ext_3459566')}, {'id': 52, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1887, 1895, 7513444, 'blade_g')}, {'id': 53, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1942, 1969, 7514212, 'ext_2260769')}, {'id': 54, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (1995, 2003, 7515236, 'sis_cia')}, {'id': 55, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2025, 2296, 7542884, 'hanop')}, {'id': 56, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': None}, {'id': 57, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': None}, {'id': 58, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2322, 2440, 7524196, 'ross_fanera')}, {'id': 59, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2466, 2530, 7532644, 'scabii')}, {'id': 60, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2556, 2596, 7548260, 'ross_fanera')}, {'id': 61, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2618, 2623, 7555428, 'scabii')}, {'id': 62, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2649, 2682, 7516260, 'e_d_w')}, {'id': 63, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2708, 2783, 7518820, 'ext_3172792')}, {'id': 64, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2809, 2874, 7522660, 'e_d_w')}, {'id': 65, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2896, 2949, 7527524, 'i_g_2016')}, {'id': 66, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (2971, 3020, 7536484, 'kogemiaka_1')}, {'id': 67, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3046, 3268, 7517796, 'ext_3172792')}, {'id': 68, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3294, 3363, 7526244, 'ext_3459566')}, {'id': 69, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3389, 3443, 7526500, 'euk05')}, {'id': 70, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3465, 3504, 7526756, 'ext_3459566')}, {'id': 71, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3526, 3568, 7538276, 'kogemiaka_1')}, {'id': 72, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3590, 3657, 7803236, 'ext_4150511')}, {'id': 73, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3679, 3715, 7532132, 'ext_2260769')}, {'id': 74, 'name': None, 'user_id': 6, 'document_id': 4, 'date': datetime.date(2019, 5, 23), 'is_all_text': 0, 'fragmentcontent': (3737, 3755, 7598948, 'kitai_gorod')}]
			
			save_params(id1, fragments2)




	#con1.rollback()
	con1.commit()
	exit(0)
################################## EXIT ########################

# mysqldump -h 0.0.0.0 -u root  -ppwd docato | gzip > ../after_atempts1_типыдлядискуссийбездискуссий.sql.gz
