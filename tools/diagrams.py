"""Classic IDEF0 sheets and UML views, in editable draw.io and SVG formats."""
from pathlib import Path
import html,json
from PIL import ImageFont
from xml.etree import ElementTree as E
from text_cleanup import clean_text
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagrams';OUT.mkdir(exist_ok=True)

class Graph:
 def __init__(self,name,w=2000,h=1400,bg='white',grid=False):
  self.name=name;self.w=w;self.h=h;self.bg=bg;self.shapes=[];self.n=1;self.geometry={}
  self.mx=E.Element('mxfile',host='app.diagrams.net',version='24.7.17',type='device')
  d=E.SubElement(self.mx,'diagram',id=name,name=name)
  m=E.SubElement(d,'mxGraphModel',grid='1',gridSize='20',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h),background=bg)
  self.r=E.SubElement(m,'root');E.SubElement(self.r,'mxCell',id='0');E.SubElement(self.r,'mxCell',id='1',parent='0')
  self.grid=grid
 def cell(self,value,style,x,y,w,h):
  self.n+=1;key=str(self.n);self.geometry[key]=(x,y,w,h)
  c=E.SubElement(self.r,'mxCell',id=key,value=clean_text(value),style=style,vertex='1',parent='1')
  E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
  return key
 def fitted(self,value,w,h,size,bold=False):
  for current in range(int(size),15,-1):
   f=ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSans-'+('Bold' if bold else 'Regular')+'.ttf',current)
   lines=[]
   for paragraph in value.split('\n'):
    line=''
    for word in paragraph.split():
     candidate=(line+' '+word).strip()
     if line and f.getlength(candidate)>w-16:lines.append(line);line=word
     else:line=candidate
    lines.append(line)
   if len(lines)*current*1.2<h-5 and all(f.getlength(line)<=w-16 for line in lines):return lines,current
  return lines,current
 def svgtext(self,lines,x,y,w,h,size,bold=False,align='center'):
  yy=y+h/2-(len(lines)-1)*size*.6
  for line in lines:
   xx=x+w/2 if align=='center' else (x+w-6 if align=='right' else x+6)
   anchor='middle' if align=='center' else ('end' if align=='right' else 'start')
   self.shapes.append(f'<text x="{xx}" y="{yy}" text-anchor="{anchor}" dominant-baseline="middle" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="#111">{html.escape(line)}</text>');yy+=size*1.2
 def text(self,value,x,y,w,h,size=28,bold=False,align='center'):
  lines,size=self.fitted(clean_text(value),w,h,size,bold)
  key=self.cell('\n'.join(lines),f'text;html=0;whiteSpace=wrap;align={align};verticalAlign=middle;fontFamily=Arial;fontSize={size};fontColor=#111111;strokeColor=none;fillColor=none;fontStyle={1 if bold else 0};',x,y,w,h)
  self.svgtext(lines,x,y,w,h,size,bold,align)
  return key
 def box(self,value,x,y,w,h,size=30,shape='rect',fill='white'):
  lines,size=self.fitted(clean_text(value),w-12,h-16,size)
  style=f'rounded=0;html=0;whiteSpace=wrap;align=center;verticalAlign=middle;fontSize={size};fontFamily=Arial;strokeWidth=1.5;strokeColor=#111111;fillColor={fill};'
  if shape=='ellipse':style+='ellipse;'
  if shape=='cylinder':style+='shape=cylinder;size=20;'
  key=self.cell('\n'.join(lines),style,x,y,w,h)
  if shape=='ellipse':self.shapes.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" stroke="#111" stroke-width="1.5" fill="{fill}"/>')
  elif shape=='cylinder':self.shapes.append(f'<path d="M{x} {y+22}C{x} {y-7},{x+w} {y-7},{x+w} {y+22}V{y+h-22}C{x+w} {y+h+7},{x} {y+h+7},{x} {y+h-22}Z M{x} {y+22}C{x} {y+51},{x+w} {y+51},{x+w} {y+22}" fill="{fill}" stroke="#111" stroke-width="1.5"/>')
  else:self.shapes.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke="#111" stroke-width="1.5" fill="{fill}"/>')
  self.svgtext(lines,x,y,w,h,size)
  return key
 def edge(self,points,source=None,target=None,dashed=False,arrow=True):
  self.n+=1
  style=f'edgeStyle=none;rounded=0;html=0;endArrow={"block" if arrow else "none"};endFill=1;strokeWidth=1.5;strokeColor=#111111;'+('dashed=1;' if dashed else '')
  for key,p,prefix in [(source,points[0],'exit'),(target,points[-1],'entry')]:
   if key:
    x,y,w,h=self.geometry[key];style+=f'{prefix}X={(p[0]-x)/w};{prefix}Y={(p[1]-y)/h};{prefix}Dx=0;{prefix}Dy=0;{prefix}Perimeter=0;'
  attrs={'id':str(self.n),'parent':'1','edge':'1','value':'','style':style}
  if source:attrs['source']=source
  if target:attrs['target']=target
  c=E.SubElement(self.r,'mxCell',**attrs);geo=E.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
  E.SubElement(geo,'mxPoint',x=str(points[0][0]),y=str(points[0][1]),**{'as':'sourcePoint'})
  E.SubElement(geo,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]),**{'as':'targetPoint'})
  if len(points)>2:
   arr=E.SubElement(geo,'Array',**{'as':'points'})
   for x,y in points[1:-1]:E.SubElement(arr,'mxPoint',x=str(x),y=str(y))
  dash='stroke-dasharray="9 6"' if dashed else '';marker='marker-end="url(#arrow)"' if arrow else ''
  self.shapes.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="#111" stroke-width="1.5" {dash} {marker}/>')
 def actor(self,name,x,y):
  key=self.cell('', 'shape=umlActor;html=0;fillColor=white;strokeColor=#111111;',x,y,80,130)
  self.shapes.append(f'<circle cx="{x+40}" cy="{y+18}" r="17" fill="white" stroke="#111" stroke-width="2"/><path d="M{x+40} {y+35}V{y+85} M{x+5} {y+52}H{x+75} M{x+40} {y+85}L{x+8} {y+128} M{x+40} {y+85}L{x+72} {y+128}" fill="none" stroke="#111" stroke-width="2"/>')
  self.text(name,x-70,y+140,220,65,27)
  return key
 def save(self,stem):
  E.indent(self.mx);E.ElementTree(self.mx).write(OUT/(stem+'.drawio'),encoding='utf-8',xml_declaration=True)
  defs='<marker id="arrow" markerWidth="12" markerHeight="10" refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0 L11 5 L0 10 Z" fill="#111"/></marker><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#e1e5e8" stroke-width=".7"/></pattern>'
  grid='<rect width="100%" height="100%" fill="url(#grid)"/>' if self.grid else ''
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"><defs>{defs}</defs><rect width="100%" height="100%" fill="{self.bg}"/>{grid}'+''.join(self.shapes)+'</svg>'
  (OUT/(stem+'.svg')).write_text(svg)

MODELS=[
 dict(key='vps',service='Аренда виртуальных серверов',name='Предоставить виртуальный сервер',
 inputs=['Заявка заказчика','Параметры ВМ','Данные доступа'],outputs=['Работающая ВМ','Данные подключения','Акт предоставления'],
 controls=['SLA','Каталог и тарифы','Требования ИБ','Регламент выдачи ВМ'],mechanisms=['VMware vSphere','Гипервизор и СХД','БД конфигураций','Инженер аренды'],
 stages=[
 dict(name='Согласовать заявку и ресурсы',inputs=['Заявка заказчика','Параметры ВМ'],outputs=['Согласованная спецификация'],controls=[0,1],mechanisms=[0,2,3],steps=['Проверить параметры заявки','Рассчитать ёмкость и тариф','Подтвердить спецификацию'],flows=['Полная заявка','Расчёт ресурсов и цены']),
 dict(name='Развернуть виртуальный сервер',inputs=['Согласованная спецификация'],outputs=['Созданная ВМ'],controls=[3],mechanisms=[0,1,2,3],steps=['Зарезервировать ресурсы кластера','Создать ВМ по шаблону','Настроить операционную систему'],flows=['Выделенный пул ресурсов','ВМ с базовой ОС']),
 dict(name='Настроить доступ и защиту',inputs=['Созданная ВМ','Данные доступа'],outputs=['Настроенная ВМ'],controls=[2,3],mechanisms=[0,2,3],steps=['Создать учётные записи','Настроить сеть и права доступа','Проверить изоляцию ВМ'],flows=['Учётные записи','Правила доступа']),
 dict(name='Проверить и передать сервер',inputs=['Настроенная ВМ'],outputs=['Работающая ВМ','Данные подключения','Акт предоставления'],controls=[0,3],mechanisms=[0,2,3],steps=['Проверить работоспособность ВМ','Подключить наблюдение','Передать доступ и оформить акт'],flows=['Протокол проверки','Профиль наблюдения'])]),
 dict(key='monitoring',service='Мониторинг и поддержка систем',name='Обеспечить мониторинг и поддержку',
 inputs=['Метрики агентов','Обращение заказчика','Сведения о ресурсах'],outputs=['Восстановленная услуга','Отчёт по SLA'],
 controls=['SLA','Пороги мониторинга','Регламент инцидентов','Регламент изменений'],mechanisms=['Zabbix / Prometheus','БД метрик и инцидентов','Инженер мониторинга','Системный администратор'],
 stages=[
 dict(name='Выявить и зарегистрировать инцидент',inputs=['Метрики агентов','Обращение заказчика'],outputs=['Зарегистрированный инцидент'],controls=[0,1,2],mechanisms=[0,1,2],steps=['Собрать метрики и обращения','Проверить событие и влияние','Зарегистрировать инцидент'],flows=['Событие наблюдения','Подтверждённый сбой']),
 dict(name='Диагностировать сбой и спланировать решение',inputs=['Зарегистрированный инцидент','Сведения о ресурсах'],outputs=['План восстановления'],controls=[0,2,3],mechanisms=[1,2,3],steps=['Назначить исполнителя','Установить причину отказа','Согласовать план восстановления'],flows=['Принятый инцидент','Диагноз и варианты действий']),
 dict(name='Восстановить работу услуги',inputs=['План восстановления'],outputs=['Восстановленная услуга и решение'],controls=[0,3],mechanisms=[0,1,3],steps=['Выполнить согласованные действия','Проверить затронутые ресурсы','Зафиксировать решение'],flows=['Изменённая конфигурация','Работоспособные ресурсы']),
 dict(name='Подтвердить результат и закрыть инцидент',inputs=['Восстановленная услуга и решение'],outputs=['Восстановленная услуга','Отчёт по SLA'],controls=[0,1,2],mechanisms=[0,1,2,3],steps=['Проверить контрольные метрики','Получить подтверждение заказчика','Закрыть инцидент и оценить SLA'],flows=['Протокол проверки','Подтверждённое решение'])])]

def frame(g,model,node,name,sheet):
 g.box('',25,25,1950,1350,fill='#ffffec')
 for x,y,w,h in [(25,25,300,150),(325,25,850,150),(1175,25,340,150),(1515,25,460,150),(25,1320,240,55),(265,1320,1420,55),(1685,1320,290,55)]:g.box('',x,y,w,h,fill='#ffffec')
 g.text('ИСПОЛЬЗУЕТСЯ В:\nУчебный проект\nООО «ТехноСервис»',35,35,280,130,24,align='left')
 g.text('АВТОРЫ: Тарасов А.М., Дементиевский Д.М., Тыцкий Б.М.\nПРОЕКТ: Управление ИТ-услугами\nДАТА: 22.10.2026     РЕДАКЦИЯ: 1.0',335,35,830,130,24,align='left')
 g.text('СТАТУС:\nРабочая модель\nСогласование SLA',1185,35,320,130,24,align='left')
 g.text('КОНТЕКСТ: '+('Внешняя среда' if node=='A-0' else ('A-0' if node=='A0' else 'A0'))+'\nУЗЕЛ: '+node+'\nГРУППА: ИКБО-74-23',1525,35,440,130,24,align='left')
 g.text('Узел: '+node,35,1325,220,45,27,align='left');g.text(name,275,1325,1400,45,27,align='left');g.text(f'Лист: {sheet} / 6',1695,1325,270,45,27)

def function(g,name,node,x,y,w,h):
 b=g.box('',x,y,w,h,32)
 label=g.text(name,x+8,y+4,w-16,h-38,32)
 code=g.text(node,x+w-82,y+h-37,70,30,25,align='right')
 for key,xx,yy in [(label,8,4),(code,w-82,h-37)]:
  cell=next(c for c in g.r if c.get('id')==key);cell.set('parent',b)
  geo=cell.find('mxGeometry');geo.set('x',str(xx));geo.set('y',str(yy))
 return b

def context(model):
 g=Graph(model['service']+' / A-0',bg='#ffffec');frame(g,model,'A-0',model['name'],1)
 b=function(g,model['name'],'A0',650,500,700,350)
 for i,label in enumerate(model['inputs']):
  y=560+i*115;g.edge([(25,y),(650,y)],target=b);g.text(label,45,y-77,530,66,29,align='left')
 for i,label in enumerate(model['outputs']):
  y=560+i*115;g.edge([(1350,y),(1975,y)],source=b);g.text(label,1395,y-77,540,66,29,align='left')
 for i,label in enumerate(model['controls']):
  x=720+i*185;g.edge([(x,175),(x,500)],target=b);g.text(label,x+7,215,175,115,27,align='left')
 for i,label in enumerate(model['mechanisms']):
  x=720+i*185;g.edge([(x,1320),(x,850)],target=b);g.text(label,x+7,1110,175,145,27,align='left')
 g.save(model['key']+'_Aminus0')
 return meta(model,'A-0',model['name'],model['inputs'],model['outputs'],model['controls'],model['mechanisms'])

def meta(model,node,name,inputs,outputs,controls,mechanisms):
 return dict(stem=model['key']+'_'+node.replace('-','minus'),node=node,name=name,inputs=inputs,outputs=outputs,controls=controls,mechanisms=mechanisms)

def decomposition(model,node,stage=None):
 first=stage is None
 names=[s['name'] for s in model['stages']] if first else stage['steps']
 inputs=model['inputs'] if first else stage['inputs'];outputs=model['outputs'] if first else stage['outputs']
 controls=model['controls'] if first else [model['controls'][i] for i in stage['controls']]
 mechanisms=model['mechanisms'] if first else [model['mechanisms'][i] for i in stage['mechanisms']]
 name=model['name'] if first else stage['name'];sheet=2 if first else int(node[1:])+2
 g=Graph(model['service']+' / '+node,bg='#ffffec');frame(g,model,node,name,sheet)
 xs=[210,620,1030,1440] if first else [230,790,1350]
 ys=[440,600,760,920] if first else [470,680,890];w=310 if first else 360;h=155
 blocks=[function(g,n,('A'+str(i+1) if first else node+str(i+1)),x,y,w,h) for i,(n,x,y) in enumerate(zip(names,xs,ys))]
 # Separate ICOM arrows and editable orthogonal branches keep the parent boundary.
 for j,label in enumerate(inputs):
  dest=(2 if model['key']=='vps' else 1) if first and j==2 else 0
  x,y=xs[dest],ys[dest]+(h/2 if dest else 40+j*80)
  if dest:
   lane=365;g.edge([(25,lane),(x-65,lane),(x-65,y),(x,y)],target=blocks[dest]);g.text(label,40,205,280,110,26,align='left')
  else:
   g.edge([(25,y),(x,y)],target=blocks[0]);g.text(label,35,y-65,xs[0]-50,58,22,align='left')
 for i in range(len(blocks)-1):
  x=xs[i]+w;y=ys[i]+h/2;nx=xs[i+1];ny=ys[i+1]+h/2
  g.edge([(x,y),(x+55,y),(x+55,ny),(nx,ny)],source=blocks[i],target=blocks[i+1])
  label=model['stages'][i]['outputs'][0] if first else stage['flows'][i]
  g.text(label,x+8,y-105,nx-x+180,90,26,align='left')
 for j,label in enumerate(outputs):
  y=ys[-1]+40+j*55;g.edge([(xs[-1]+w,y),(1975,y)],source=blocks[-1]);g.text(label,xs[-1]+w+8,y-53,1970-xs[-1]-w-12,50,24,align='left')
 for j,label in enumerate(controls):
  bx=400+j*400 if first else 400+j*470
  lane=295+j*20;g.edge([(bx,175),(bx,lane)],arrow=False);g.text(label,bx+5,185,360,85,27,align='left')
  indices=[i for i,s in enumerate(model['stages']) if j in s['controls']] if first else list(range(3))
  centers=[xs[i]+55+j*35 for i in indices]
  if centers:g.edge([(min([bx]+centers),lane),(max([bx]+centers),lane)],arrow=False)
  for i,x in zip(indices,centers):g.edge([(x,lane),(x,ys[i])],target=blocks[i])
 for j,label in enumerate(mechanisms):
  bx=390+j*400
  lane=1130+j*24;g.edge([(bx,1320),(bx,lane)],arrow=False);g.text(label,bx+6,1230,370,78,27,align='left')
  indices=[i for i,s in enumerate(model['stages']) if j in s['mechanisms']] if first else list(range(3))
  centers=[xs[i]+70+j*45 for i in indices]
  if centers:g.edge([(min([bx]+centers),lane),(max([bx]+centers),lane)],arrow=False)
  for i,x in zip(indices,centers):g.edge([(x,lane),(x,ys[i]+h)],target=blocks[i])
 g.save(model['key']+'_'+node)
 return meta(model,node,name,inputs,outputs,controls,mechanisms)

def make_idef():
 index=[]
 for model in MODELS:
  index.extend([context(model),decomposition(model,'A0')])
  index.extend(decomposition(model,'A'+str(i+1),stage) for i,stage in enumerate(model['stages']))
 (OUT/'idef0-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2))

def architecture():
 g=Graph('Концептуальная модель ITSM',1800,1200,grid=True)
 g.text('Концептуальная модель ITSM ООО «ТехноСервис»',40,18,1720,65,35,True)
 db=g.box('База данных\nMariaDB 11.8',720,100,360,160,31,'cylinder',fill='#edf0f2')
 g.box('',60,420,1680,270,fill='#e4e6e8');g.text('Сервер ITSM: Apache 2.4 + PHP 8.4',80,430,1640,60,35,True)
 xs=[90,515,940,1365];labels=['Аутентификация\nСессии и роли','Сообщения\nЛичная переписка','Каталог услуг\nРесурсы и связи','Service Desk\nИнциденты и SLA'];mods=[]
 for i,(x,label) in enumerate(zip(xs,labels)):
  mods.append(g.box(label,x,520,345,130,30,fill='#f3f3f3'))
  xx=x+172.5;port=760+i*90
  g.edge([(xx,520),(xx,315+i*20),(port,315+i*20),(port,260)],source=mods[-1],target=db,dashed=True)
  g.text('SQL',xx+10,365,90,40,25)
 actor=g.actor('Пользователь\nвеб-клиента',860,950)
 for i,x in enumerate(xs):
  xx=x+172.5;g.edge([(900,1002),(xx,760),(xx,650)],source=actor,target=mods[i])
  g.text('HTTP / JSON',xx-95,700,190,45,25)
 g.save('itsm_concept')

def use_case():
 g=Graph('UML Use Case',1100,1380,grid=True)
 g.box('',380,30,690,1320,fill='#ffffff')
 g.text('ITSM «ТехноСервис»',400,42,650,65,32,True)
 names=['UC1. Зарегистрироваться\nи войти','UC2. Просмотреть каталог\nи ресурсы','UC3. Создать и отследить\nобращение','UC4. Обменяться\nсообщениями','UC5. Обработать инцидент\nи проверить SLA','UC6. Изменить услуги\nи зависимости','UC7. Назначить права\nпользователей']
 cases=[]
 for i,name in enumerate(names):cases.append(g.box(name,470,135+i*170,510,105,29,'ellipse',fill='#dceef8'))
 actors=[g.actor('Сотрудник',105,230),g.actor('Поддержка',105,635),g.actor('Администратор',105,1040)]
 for a,indices in [(0,[0,1,2,3]),(1,[0,1,3,4]),(2,[0,1,3,4,5,6])]:
  for i in indices:g.edge([(180,282+a*405),(470,187.5+i*170)],source=actors[a],target=cases[i],arrow=False)
 g.save('itsm_use_case')

if __name__=='__main__':make_idef();architecture();use_case()
