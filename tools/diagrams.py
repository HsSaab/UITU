"""Generate matching editable diagrams.net, SVG and high-resolution PNG assets."""
from pathlib import Path
import json, html, textwrap
from PIL import ImageFont
from text_cleanup import clean_text
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagrams';OUT.mkdir(exist_ok=True)

class Graph:
    def __init__(self,name,w=1600,h=1040):
        self.name=name;self.w=w;self.h=h;self.shapes=[];self.n=1
        self.mx=E.Element('mxfile',host='app.diagrams.net',version='24.7.17',type='device')
        d=E.SubElement(self.mx,'diagram',id=name,name=name)
        m=E.SubElement(d,'mxGraphModel',dx=str(w),dy=str(h),grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h))
        self.r=E.SubElement(m,'root');E.SubElement(self.r,'mxCell',id='0');E.SubElement(self.r,'mxCell',id='1',parent='0')
    def cell(self,value,style,x,y,w,h):
        value=clean_text(value)
        self.n+=1;id=str(self.n)
        c=E.SubElement(self.r,'mxCell',id=id,value=value,style=style,vertex='1',parent='1');E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
        return id
    def fitted(self,value,w,h,size,bold=False):
        for current in range(int(size),15,-1):
            font=ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSans-'+('Bold' if bold else 'Regular')+'.ttf',current)
            lines=[]
            for paragraph in value.split('\n'):
                words=paragraph.split();line=''
                for word in words:
                    candidate=(line+' '+word).strip()
                    if line and font.getlength(candidate)>w-20:
                        lines.append(line);line=word
                    else:line=candidate
                lines.append(line)
            if len(lines)*current*1.2<=h-6:return lines,current
        return lines,current
    def text(self,value,x,y,w,h,size=30,bold=False,align='center'):
        value=clean_text(value)
        lines,size=self.fitted(value,w,h,size,bold);value='\n'.join(lines)
        self.cell(value,f'text;html=0;whiteSpace=wrap;align={align};verticalAlign=middle;fontFamily=Arial;fontSize={size};fontColor=#152e3b;strokeColor=none;fillColor=none;fontStyle={1 if bold else 0};',x,y,w,h)
        lines=value.split('\n');yy=y+h/2-(len(lines)-1)*size*.6
        for line in lines:
            xx=x+w/2 if align=='center' else x+6
            self.shapes.append(f'<text x="{xx}" y="{yy}" text-anchor="{"middle" if align=="center" else "start"}" dominant-baseline="middle" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="#152e3b">{html.escape(line)}</text>');yy+=size*1.2
    def box(self,value,x,y,w,h,size=31,shape='rect',fill='white'):
        value=clean_text(value)
        lines,size=self.fitted(value,w,h,size);value='\n'.join(lines)
        style=f'rounded=0;html=0;whiteSpace=wrap;align=center;verticalAlign=middle;fontSize={size};fontFamily=Arial;strokeWidth=2;fillColor={fill};'
        if shape=='ellipse':style+='ellipse;'
        id=self.cell(value,style,x,y,w,h)
        if shape=='ellipse':self.shapes.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" stroke="#183845" stroke-width="2" fill="{fill}"/>')
        else:self.shapes.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke="#183845" stroke-width="2" fill="{fill}"/>')
        # SVG text uses identical geometry, the draw.io cell retains its own label.
        lines=value.split('\n');yy=y+h/2-(len(lines)-1)*size*.6
        for line in lines:
            self.shapes.append(f'<text x="{x+w/2}" y="{yy}" text-anchor="middle" dominant-baseline="middle" font-family="Arial, sans-serif" font-size="{size}" fill="#152e3b">{html.escape(line)}</text>');yy+=size*1.2
        return id
    def edge(self,points,label='',source=None,target=None,dashed=False,arrow=True,labelbox=None):
        self.n+=1
        attrs={'id':str(self.n),'parent':'1','edge':'1','value':'','style':f'edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow={"block" if arrow else "none"};endFill=1;strokeWidth=2;fontFamily=Arial;fontSize=27;'+('dashed=1;' if dashed else '')}
        if source:attrs['source']=source
        if target:attrs['target']=target
        c=E.SubElement(self.r,'mxCell',**attrs);geo=E.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
        E.SubElement(geo,'mxPoint',x=str(points[0][0]),y=str(points[0][1]),**{'as':'sourcePoint'})
        E.SubElement(geo,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]),**{'as':'targetPoint'})
        if len(points)>2:
            arr=E.SubElement(geo,'Array',**{'as':'points'})
            for x,y in points[1:-1]:E.SubElement(arr,'mxPoint',x=str(x),y=str(y))
        self.shapes.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="#183845" stroke-width="2.3" {"stroke-dasharray=\"9 5\"" if dashed else ""} {"marker-end=\"url(#arrow)\"" if arrow else ""}/>')
        if label and labelbox:self.text(label,*labelbox,size=27)
    def save(self,stem):
        E.indent(self.mx);E.ElementTree(self.mx).write(OUT/(stem+'.drawio'),encoding='utf-8',xml_declaration=True)
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"><defs><marker id="arrow" markerWidth="11" markerHeight="9" refX="9" refY="4.5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0 L10 4.5 L0 9 Z" fill="#183845"/></marker></defs><rect width="100%" height="100%" fill="white"/>'+''.join(self.shapes)+'</svg>'
        (OUT/(stem+'.svg')).write_text(svg)

MODELS=[
 {'key':'vps','service':'Аренда виртуальных серверов','name':'Предоставить виртуальный сервер','input':'Заявка и параметры ВМ','output':'Работающая ВМ и акт','control':'SLA; каталог; политика ИБ','mechanism':'Инженер аренды; vSphere; БД; гипервизор',
  'stages':[
   ('Согласовать заявку\nи ресурсы','Согласованная\nспецификация',['Проверить параметры\nзаявки','Рассчитать ёмкость\nи тариф','Подтвердить\nспецификацию'],['Полная заявка','Расчёт ресурсов']),
   ('Развернуть\nвиртуальный сервер','Настроенная ВМ',['Зарезервировать\nресурсы кластера','Создать ВМ\nпо шаблону','Настроить ОС\nи сетевой доступ'],['Выделенный пул','Созданная ВМ']),
   ('Проверить и\nпередать сервер','Работающая ВМ и акт',['Проверить работу\nи изоляцию ВМ','Включить ВМ\nв мониторинг','Передать доступ\nи оформить акт'],['Протокол проверки','Профиль наблюдения'])]},
 {'key':'monitoring','service':'Мониторинг и поддержка систем','name':'Обеспечить мониторинг и поддержку','input':'Метрики и обращения','output':'Восстановленная услуга; отчёт','control':'SLA; пороги; регламент изменений','mechanism':'Инженер мониторинга; администратор; Zabbix; БД',
  'stages':[
   ('Выявить и\nзарегистрировать сбой','Зарегистрированный\nинцидент',['Собрать метрики\nи обращения','Проверить событие\nи влияние','Зарегистрировать\nинцидент в ITSM'],['Событие наблюдения','Подтверждённый сбой']),
   ('Диагностировать\nи восстановить услугу','Решение и\nвосстановленная услуга',['Назначить\nисполнителя','Определить причину\nи план действий','Выполнить\nвосстановление'],['Принятая заявка','План восстановления']),
   ('Подтвердить результат\nи закрыть инцидент','Восстановленная услуга; отчёт',['Проверить метрики\nпосле исправления','Получить подтверждение\nзаказчика','Закрыть инцидент\nи оценить SLA'],['Протокол проверки','Подтверждённое решение'])]}
]

def wrap(s,width=25):return '\n'.join(textwrap.wrap(s,width,break_long_words=False))
def idef(model,node,name,input,output,children=None,intermediate=None):
    g=Graph(f'{model["service"]} / {node}')
    g.text(f'{node} · {model["service"]}',60,20,1480,60,35,True)
    g.text(wrap(name,70),70,86,1460,65,30)
    g.shapes.append('<rect x="20" y="170" width="1560" height="790" fill="none" stroke="#8ba2ab" stroke-width="1"/>')
    if children is None:
        b=g.box(wrap(name,29)+'\nA0',510,390,580,240,37)
        g.edge([(60,510),(510,510)],source=None,target=b)
        g.text('I1 · '+wrap(input,23),45,370,430,110,30)
        g.edge([(1090,510),(1535,510)],source=b)
        g.text('O1 · '+wrap(output,23),1120,370,430,110,30)
        g.text('C1 · '+wrap(model['control'],46),355,185,890,100,30)
        g.edge([(800,290),(800,390)],target=b)
        g.edge([(800,850),(800,630)],target=b)
        g.text('M1 · '+wrap(model['mechanism'],55),230,855,1140,90,30)
    else:
        xs=[230,650,1070];ys=[340,490,640];w=300;h=160
        blocks=[g.box(c+'\n'+(f'A{i+1}' if node=='A0' else node+str(i+1)),x,y,w,h,32) for i,(c,x,y) in enumerate(zip(children,xs,ys))]
        g.text('C1 · '+model['control'],200,185,1200,55,29)
        g.edge([(380,280),(1220,280)],arrow=False)
        for x,y,b in zip(xs,ys,blocks):g.edge([(x+w/2,280),(x+w/2,y)],target=b)
        g.text('I1 · '+wrap(input,23),28,220,300,105,28)
        g.edge([(45,ys[0]+h/2),(xs[0],ys[0]+h/2)],target=blocks[0])
        for i in range(2):
            # Output on right becomes input on left of the next block.
            px=xs[i]+w;py=ys[i]+h/2;nx=xs[i+1];ny=ys[i+1]+h/2
            g.edge([(px,py),(px+55,py),(px+55,ny),(nx,ny)],source=blocks[i],target=blocks[i+1])
            g.text(wrap(intermediate[i],18),px+28,py-88,245,80,27)
        g.edge([(1370,720),(1545,720)],source=blocks[-1])
        g.text('O1 · '+wrap(output,22),1250,810,315,100,28)
        g.edge([(380,900),(1220,900)],arrow=False)
        for x,y,b in zip(xs,ys,blocks):g.edge([(x+w/2,900),(x+w/2,y+h)],target=b)
        g.text('M1 · '+model['mechanism'],80,967,1440,50,28)
    g.text('ООО «ТехноСервис» · IDEF0 · I — вход; C — управление; O — выход; M — механизм',30,1012,1540,24,20)
    stem=model['key']+'_'+node.replace('-','minus');g.save(stem)
    return {'stem':stem,'node':node,'name':name,'input':input,'output':output,'control':model['control'],'mechanism':model['mechanism']}

def make_idef():
    metadata=[]
    for m in MODELS:
        metadata.append(idef(m,'A-0',m['name'],m['input'],m['output']))
        metadata.append(idef(m,'A0',m['name'],m['input'],m['output'],[s[0] for s in m['stages']],[s[1] for s in m['stages'][:2]]))
        for i,stage in enumerate(m['stages']):
            metadata.append(idef(m,f'A{i+1}',stage[0].replace('\n',' '),m['input'] if i==0 else m['stages'][i-1][1].replace('\n',' '),stage[1].replace('\n',' '),stage[2],stage[3]))
    (OUT/'idef0-index.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))

def architecture():
    g=Graph('Концептуальная модель ITSM',1600,1120)
    g.text('ITSM ООО «ТехноСервис» · концептуальная модель',30,18,1540,65,35,True)
    roles=g.box('Заказчик / сотрудник\nПоддержка · Администратор',440,115,720,100,33)
    ui=g.box('Веб-клиент · HTML / CSS / JavaScript\nФормы, каталог, очередь, переписка',330,300,940,110,32)
    web=g.box('Apache 2.4 → FastCGI → PHP 8.4\nСессии, роли, проверка данных, API',330,505,940,120,32)
    msg=g.box('Модуль\nсообщений',75,725,410,105,32);cat=g.box('Каталог услуг\nи связи с КЕ',595,725,410,105,32);sd=g.box('Service Desk\nи расчёт SLA',1115,725,410,105,32)
    db=g.box('MariaDB 11.8 · пользователи, услуги, КЕ, связи,\nинциденты, история, сообщения',280,940,1040,110,30,fill='#f0f7f7')
    g.edge([(800,215),(800,300)],source=roles,target=ui,label='Заявки, сообщения, параметры услуг',labelbox=(850,220,650,65))
    g.edge([(800,410),(800,505)],source=ui,target=web,label='HTTP / JSON; ответы и статусы',labelbox=(850,420,630,60))
    for x,b in [(280,msg),(800,cat),(1320,sd)]:
        g.edge([(800,625),(800,665),(x,665),(x,725)],source=web,target=b)
        g.edge([(x,830),(x,880),(800,880),(800,940)],source=b,target=db)
    g.text('Вход: обращения, метрики, сведения об услугах · Выход: решения, каталог, история, показатели',30,1065,1540,35,25)
    g.text('Ресурсы: Linux, CPU / RAM / диск · Документы: SLA №4, модели IDEF0 №5, регламент и тесты',30,1100,1540,25,22)
    g.save('itsm_concept')

def use_case():
    g=Graph('UML Use Case',1600,1140)
    g.text('UML · варианты использования ITSM',30,18,1540,65,36,True)
    g.shapes.append('<rect x="315" y="95" width="1120" height="960" fill="none" stroke="#183845" stroke-width="2"/>')
    g.text('ITSM «ТехноСервис»',700,110,500,50,30,True)
    # Actors retain editable UML actor shapes in diagrams.net.
    def actor(name,x,y):
        id=g.cell(name,'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=0;fontFamily=Arial;fontSize=27;',x,y,85,135)
        g.shapes.append(f'<circle cx="{x+42}" cy="{y+20}" r="18" fill="white" stroke="#183845" stroke-width="2"/><path d="M{x+42} {y+38}V{y+90} M{x+8} {y+55}H{x+76} M{x+42} {y+90}L{x+10} {y+130} M{x+42} {y+90}L{x+74} {y+130}" fill="none" stroke="#183845" stroke-width="2"/>')
        g.text(name,x-90,y+145,270,65,27)
        return id
    actors=[actor('Сотрудник',95,230),actor('Поддержка',95,520),actor('Администратор',95,850)]
    specs=[('UC1 · Зарегистрироваться\nи войти',600,205),('UC2 · Просмотреть\nкаталог и ресурсы',600,365),('UC3 · Создать и\nотследить обращение',600,525),('UC4 · Обменяться\nсообщениями',600,685),('UC5 · Обработать инцидент\nи проверить SLA',1100,525),('UC6 · Изменить услуги\nи зависимости',1100,845),('UC7 · Назначить\nправа пользователей',600,885)]
    cases=[]
    for name,x,y in specs:cases.append(g.box(name,x-175,y-48,350,100,29,'ellipse'))
    links=[(0,[0,1,2,3]),(1,[0,1,3,4]),(2,[0,1,3,4,5,6])]
    for a,indices in links:
        ay=[300,590,920][a]
        for i in indices:
            x,y=specs[i][1:]
            lane=285+a*10
            if i in [4,5]:
                corridor=750 if i==4 else 1015
                points=[(180,ay),(lane,ay),(lane,corridor),(900,corridor),(900,y),(x-175,y)]
            else:points=[(180,ay),(lane,ay),(lane,y),(x-175,y)]
            g.edge(points,source=actors[a],target=cases[i],arrow=False)
    g.text('UC5: принять → назначить → восстановить → подтвердить → закрыть; история и сроки сохраняются',30,1082,1540,48,26)
    g.save('itsm_use_case')

if __name__=='__main__':make_idef();architecture();use_case()
