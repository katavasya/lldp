import re
import pexpect
import sys
import telnetlib3
import string
import time
neighbour_list = []     # общий список свитчей, полученный через lldp
port_lldp = []  # указатель, с какого порта растет свитч-сосед

# Создание списка свитчей из списка из нок-тулза
# sh_sw = open('test (4).txt')
open_noc = str(open('/home/andrey/topo').read().strip())
list_IP_noc = []
list_uplink_noc = []
port_transit_noc = []
list_transit_noc = []
for line in open_noc.split('\n'):
    if 'ink' in line:
        list_IP_noc.append(re.search(r'\d+\.\d+\.\d+\.\d+', line).group())  # вытаскиваем IP
        list_uplink_noc.append((re.search(r'\t\d+\t', line).group()).strip())   # вытаскиваем аплинки
        port_transit_noc.append(((re.search(r'\t\d+\t\d+', line).group()).strip().split('\t'))[1])  # из \t\uplink\t\transit вытягиваем транзит
        list_transit_noc.append((re.findall(r'\d+\.\d+\.\d+\.\d+', line))[1])   # вытаскиваем ip транзитных свитчей
    if '<--' in line:
        other_house = (re.findall(r'\d+\.\d+\.\d+\.\d+', line))[1]  # свитч, с которого растет заданный дом. Он нам не нужен
bad_uplink = []
bad_transit = []
# Начинаем цикл по списку из нок-тулза
for ip in list_IP_noc:
    print('---------------------','Свитч '+ip,sep='\n')

# ------------------ Поиск аплинка на свитче --------------------------------------------------------------------------

    open_switch = pexpect.spawn('/home/andrey/tel3 ' + ip)
    open_switch.expect('#')
    open_switch.sendline('show switch')
    open_switch.sendline('a')
    open_switch.expect('#')
    sh_sw = str(open_switch.before).replace('\\n',' ').replace('\\r','\n')      # превратить то, что получили от свитча в
    # строку(получится целый текст) и нормальную форму: перенос по строчкам, убирание \\n и \\r

    for line in sh_sw.split('\n'):          # разбить тот текст на список, чтобы пройтись циклом по отдельным строчкам, а не буквам
        if 'VLAN Name' in line:             # если эта фраза есть в строке -
            sh_sw_vlan = re.search('\d+', line).group()         # ищем в этой строке номер влана по этому шаблону
            continue                                            # и выходим из цикла for
        elif 'Default Gateway' in line:                               # если эта фраза есть в строке -
            sh_sw_gateway = re.search('\d+\.\d+\.\d+\.\d+', line).group()    # ищем мак абонента по этому шаблону
            if sh_sw_vlan:
                break
            continue

    open_switch.expect('#')
    open_switch.sendline('show arpentry')
    open_switch.sendline('a')
    open_switch.expect('#')
    arpe = str(open_switch.before).replace('\\n',' ').replace('\\r','\n')

    for line in arpe.split('\n'):		# ищем в sh arpe мак шлюза по IP
        if sh_sw_gateway+' ' in line:
            mac_gateway = re.search('\w+-\w+-\w+-\w+-\w+-\w+', line).group()
            break

    # ищем порт аплинк (sh fdb mac шлюза)
    open_switch.expect('#')
    open_switch.sendline('show fdb mac_address ' + mac_gateway)
    open_switch.sendline('a')
    open_switch.expect('#')
    sh_fdb = str(open_switch.before).replace('\\n',' ').replace('\\r','\n')
    for line in sh_fdb.split('\n'):
        if sh_sw_vlan in line and mac_gateway.upper() in line:
            port_uplink = ''.join(re.search(r' \d\d ', line).group().split())
            break

# -----------------------------------------------------------------------------------------

    # заход на свитч и ввод lldp
    # open_switch = pexpect.spawn('/home/andrey/tel3 ' + ip)
    open_switch.expect('#')
    # open_switch.interact()
    # open_switch.sendline('disable clipaging')
    # open_switch.expect('#')
    open_switch.sendline('show lldp remote_ports  ')
    open_switch.sendline('a')
    # time.sleep(3)
    open_switch.expect('#')
    all_lldp = str(open_switch.before).replace('\\n', ' ').replace('\\r', '\n')
    open_switch.sendline('logo')
    #open_switch = pexpect.spawn('/home/andrey/tel3 ' + ip)
    # open_switch.sendline('sh arpe')
    # open_switch.expect('#')
    # open_switch.sendline('show fdb p ' + arr_line[-1].replace('Port ID : ', '').strip())
    # open_switch.sendline('a')
    # open_switch.expect('#')
    # sh_fdb = str(open_switch.before).replace('\\n', ' ').replace('\\r', '\n')

# составляет список свитчей-соседей, полученный по lldp

    # sh_sw = open('test (1).txt')
    # output = str(sh_sw.read())
    arr_line = []            # по сути, не нужная, временная переменная для вывода номера порта, который находится на 2 строки выше
    # dict_neighbour = dict()
    for line in all_lldp.split('\n'):       # идем по строчкам вывода lldp (они разбиты на строчки \n)
        if 'Port ID :' in line:             # как раз та унылая конструкция
            arr_line.append(line)           # добавляем в список порты, на которых видны lldp свитчи
        try:                                    # чтобы не вываливался с ошибкой, когда не найдет ip в lldp
            if 'System Name' in line:   # в этой строке ищем ip соседа
                neighbour_temp = (re.search(r'\d+\.\d+\.\d+\.\d+', line).group())
                if str(arr_line[-1]).replace('Port ID : ', '').strip() == port_uplink:  # если порт, который пришел по
                # lldp - аплинковый, меняем формулировку в выводе
                    print('Uplink  :', str(arr_line[-1]).replace('Port ID : ', '').strip(), ' -', neighbour_temp)
                    if str(arr_line[-1]).replace('Port ID : ', '').strip() != list_uplink_noc[list_IP_noc.index(ip)] \
                            or neighbour_temp != list_transit_noc[list_IP_noc.index(ip)]:
                        bad_uplink.append(ip)
                else:
                    print(arr_line[-1], '-', neighbour_temp)  # последний элемент из списка портов выводим
                    if str(arr_line[-1]).replace('Port ID : ', '').strip() != port_transit_noc[list_IP_noc.index(neighbour_temp)]:
                       bad_transit.append(ip)
                # проверка того, что свитча еще нет в списке и чтобы было все в пределах одного дома:
                if neighbour_temp not in neighbour_list and neighbour_temp != other_house:
                    neighbour_list.append(neighbour_temp)
                    port_lldp.append(str(arr_line[-1]).replace('Port ID : ', '').strip())       # добавляем порт, за которым сосед в список
                continue
                # dict_neighbour['Port'].update([str(arr_line[-1]).replace('Port ID : ', '')])
                # dict_neighbour['Port'] = str(arr_line[-1]).replace('Port ID : ','')
                # dict_neighbour.setdefault('Port: ',[]).append(str(arr_line[-1]).replace('Port ID : ',''))
                # dict_neighbour.setdefault('IP_neighbour',[]).append(neighbour)
                # print(dict_neighbour['Port'])

                # dict_neighbour = dict.setdefault(('Port',[]).append('123'), ('IP_neighbour',)])
                # dict_neighbour =  dict([('Port', str(arr_line[-1]).replace('Port ID : ','')), ('IP_neighbour',neighbour)])
        except:
# проверка того, что с этого порта летит не один мак
#             sh_sw = open('test (3).txt')
#             output = str(sh_sw.read())
#             open_switch.sendline('\n')
            open_switch = pexpect.spawn('/home/andrey/tel3 ' + ip)
            open_switch.expect('#')
            open_switch.sendline('show fdb p ' + arr_line[-1].replace('Port ID : ', '').strip())
            open_switch.sendline('a')
            open_switch.expect('#')
            sh_fdb = str(open_switch.before).replace('\\n', ' ').replace('\\r', '\n')
            # open_switch.sendline('logo')
            for line_temp in sh_fdb.split('\n')[::-1]:
                if 'Total Entries' in line_temp:
                    if int(re.search(r'\d+', line_temp).group()) >= 2:
                        print('Возможно, на свитче ', ip, 'за портом ', arr_line[-1], 'есть свитч, стоит проверить')
                        break
                    else:
                        print('Возможно, на свитче ', ip, 'за портом ', arr_line[-1], 'нет свитча, но можно проверить')
                        break
            # print(port_lldp,neighbour_list)

# sh_sw.close()
# сравнение списков свитчей:
# for i in list_IP_noc:
#     for j in neighbour_list:
#         if i == j:
#             break
#             print(i)
# print('qqq')

# тут сравнивается 2 списка на предмет того, какие значения есть в первом списке и нет во втором и наоборот:
list_IP_noc = set(list_IP_noc)                  # Разбиваем строку на ip, а то он посимвольно будет проходить и делаем из списка множество
neighbour_list = set(neighbour_list)
print('---------------------')
print('Получено по нок-тулзу: ', int(len(list_IP_noc)))
print('Получилось по lldp:', int(len(neighbour_list)))
# if len(list_IP_noc.split('\n')) > len(neighbour_list.split('\n')):
#     print(set(list_IP_noc.split('\n'))).difference(set(neighbour_list.split('\n')))
# elif len(list_IP_noc.split('\n')) < len(neighbour_list.split('\n')):
#     print(set(neighbour_list.split('\n'))).difference(set(list_IP_noc.split('\n')))
# else:
#     print('списки равны')
    # or len(list_IP_noc.split('\n')) < len(neighbour_list.split('\n')):
if bad_transit or bad_uplink:
    print('Что-то не так с аплинком: ',bad_uplink,' или транзитом: ',bad_transit)
if list_IP_noc.difference(neighbour_list) or neighbour_list.difference(list_IP_noc):    # если списки не пустые:
    # вывод отсортированного и сравненного списка свитчей
    print('По lldp не получены эти свитчи: ', *sorted(sorted((list_IP_noc.difference(neighbour_list))), key=len), sep='\n')
    print('По нок-тулзу не учтены эти свитчи: ', *sorted(sorted((neighbour_list.difference(list_IP_noc))), key=len), sep='\n')
else:
    print('списки равны')
