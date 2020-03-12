# система типов, 
import os
import pymysql

##################################### тут все настроить ################
SUBJECT_ID = 25
con1 = pymysql.connect('localhost', 'root', 'pwd', 'docato') # система 1
##################################### дальше не трогатть ##############
cur1 = con1.cursor()

######  select part
cur1.execute("select id from django_content_type where  model = 'integerslot' and app_label='docato' ")
ct25=cur1.fetchone()[0]  #polymorphic_ctype_id
cur1.execute("select id from django_content_type where  model = 'classlabelslot' and app_label='docato' ")
ct23=cur1.fetchone()[0]  #polymorphic_ctype_id
print('ct25,ct23=',ct25,ct23)
#######
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P1', 1, {0}); #178".format(SUBJECT_ID))
ft_p1=con1.insert_id()
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P2', 1, {0}); #179".format(SUBJECT_ID))
ft_p2=con1.insert_id()
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P3', 1, {0}); #180".format(SUBJECT_ID))
ft_p3=con1.insert_id()
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P4', 1, {0}); #182".format(SUBJECT_ID))
ft_p4=con1.insert_id()
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P5', 1, {0}); #184".format(SUBJECT_ID))
ft_p5=con1.insert_id()
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P6 (konflict_sotrud)', 1, {0}); # 185".format(SUBJECT_ID))
ft_p6=con1.insert_id()
cur1.execute("insert into docato_frametype (name, standalone, subject_id) values ( 'P7', 1, {0}); # 186".format(SUBJECT_ID))
ft_p7=con1.insert_id()
print('docato_frametype ids=',ft_p1,ft_p2,ft_p3,ft_p4,ft_p5,ft_p6,ft_p7)
    
# keys
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'value', '0 (unknown), 1 (нет фрустрации), 2 (фрустрация повышается), 3 (фрустрация понижается)', {0}, {1}, 20); #877".format(ft_p1, ct25))
bs_p1_v=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'value', '0 (unknown), 1 (нет агрессии), 2 (агрессия усиливается), 3(агрессия снижается)', {0}, {1}, 10); #878".format(ft_p2, ct25))
bs_p2_v=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'value', 'unknown, E, n (\"надо\"), инф, I_ (я не виноват!), E\", e_, I, I\", i_, M, M\", m_', {0}, {1}, 20); #897 #classlabel".format(ft_p3, ct23))
bs_p3_v=con1.insert_id()
# p4
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'process_result', '-1, 0, +1,   -10 (unknown)', {0}, {1}, 30); #899".format(ft_p4, ct25))
bs_p4_899=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'razd_druzh', '-1, 0, +1 ,   -10 (unknown)', {0}, {1}, 40); #900".format(ft_p4, ct25))
bs_p4_900=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'sub_dom', '-1, 0, +1,   -10(unknown)', {0}, {1}, 20); #898".format(ft_p4, ct25))
bs_p4_898=con1.insert_id()
#
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'value', '1 (литературный), 2 (стандартный), 3 (защитный), 4(разорванный),  5 (вычурный)', {0}, {1}, 10); #883".format(ft_p5, ct25))
bs_p5_v=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( 'value', '-1, 0, +1,   -10 (unknown)', {0}, {1}, 10); #884".format(ft_p6, ct25))
bs_p6_v=con1.insert_id()
# p7
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( '1. Пробл_Автор', '0.Неопределенный, 1.Я, 2.Мы', {0}, {1}, 20); #901".format(ft_p7, ct25))
bs_p7_901=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( '2. Пробл_Состояние', '0.Не выражено, 1.Положит, 2.Отрицат', {0}, {1}, 30); #902".format(ft_p7, ct25))
bs_p7_902=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( '3. Пробл_Причины', '0.Не указаны, 1.Указаны', {0}, {1}, 40); #903".format(ft_p7, ct25))
bs_p7_903=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( '4. Пробл_План', '0.Отсутствует, 1.Неопределенный, 2.Определенный', {0}, {1}, 50); #904".format(ft_p7, ct25))
bs_p7_904=con1.insert_id()
cur1.execute("insert into docato_baseslot ( name, description, frame_type_id, polymorphic_ctype_id, `order`) values ( '5. Пробл_Адресат', '0.Неопределенный, 1.Мы, 2.Ты/вы, 3.Он, 4.Они', {0}, {1}, 60); #905".format(ft_p7, ct25))
bs_p7_905=con1.insert_id()

print('docato_baseslot ids=',bs_p1_v,bs_p2_v,bs_p3_v,bs_p4_899,bs_p4_900,bs_p4_898,bs_p5_v,bs_p6_v,bs_p7_901,bs_p7_902,bs_p7_903,bs_p7_904,bs_p7_905)

cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p1_v)  ) #877
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p2_v)  ) #878
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p5_v)  ) #883
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p6_v)  ) #884
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p4_898)  ) #898
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p4_899)  ) #899
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p4_900)  ) #900
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p7_901)  ) #901
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p7_902)  ) #902
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p7_903)  ) #903
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p7_904)  ) #904
cur1.execute( "insert into docato_integerslot (baseslot_ptr_id, default_value) values ({0}, 0);".format(bs_p7_905)  ) #905

cur1.execute( "insert into docato_classlabelslot (baseslot_ptr_id, default_value) values ({0}, '-');".format(bs_p3_v)  ) #bs_p3_v

con1.commit()
