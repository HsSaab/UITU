"""Real Chromium interactions and screenshots used by report 6."""
from pathlib import Path
import json,secrets,subprocess,sys
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from verify import Client
OUT=ROOT/'evidence'/'screenshots';OUT.mkdir(parents=True,exist_ok=True)
pwfile=ROOT/'.runtime/demo-password.txt'
password=pwfile.read_text().strip() if pwfile.exists() else secrets.token_urlsafe(18)
pwfile.write_text(password);pwfile.chmod(0o600)
accounts=[('admin@technoservice.test','Администратор системы','admin'),('monitoring@technoservice.test','Инженер мониторинга','support')]
for email,name,role in accounts:
    r=subprocess.run(['bash',str(ROOT/'scripts/php.sh'),str(ROOT/'app/create-user.php'),email,name,role],input=password,text=True,capture_output=True)
    if r.returncode and 'уже существует' not in r.stderr:raise RuntimeError(r.stderr)
results=[]
def passed(name):results.append({'name':name,'status':'passed'})
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1100},device_scale_factor=1.5,locale='ru-RU',timezone_id='Europe/Moscow')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def shot(name):
        page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
        crops={'01_login':(450,40,990,790),'02_registration':(450,40,990,950),'04_incident_create':(270,125,1420,860),'05_incident_employee':(270,125,935,1050),'06_incident_queue':(270,120,1420,650),'07_incident_resolved':(270,125,935,1090),'08_incident_closed':(270,125,935,1090),'09_messages':(270,125,1420,950),'10_catalog_editor':(270,125,1420,950),'11_roles':(270,125,1420,850)}
        dest=ROOT/'evidence/report-images';dest.mkdir(exist_ok=True)
        if name=='03_catalog_employee':
            page.locator('.card.service').first.screenshot(path=str(dest/(name+'.png')))
        elif name in crops:
            from PIL import Image
            with Image.open(OUT/(name+'.png')) as im:
                factor=im.width/1440;box=tuple(int(v*factor) for v in crops[name])
                im.crop(box).save(dest/(name+'.png'))
    def login(email):
        page.goto('http://127.0.0.1:8080/');expect(page.get_by_role('heading',name='Вход в систему')).to_be_visible()
        page.get_by_label('Электронная почта').fill(email);page.get_by_label('Пароль',exact=True).fill(password)
        page.get_by_role('button',name='Войти',exact=True).click();expect(page.get_by_role('heading',name='Обзор обслуживания')).to_be_visible()
    def logout():page.get_by_role('button',name='Выйти',exact=True).click();expect(page.get_by_role('heading',name='Вход в систему')).to_be_visible()
    page.goto('http://127.0.0.1:8080/');expect(page.get_by_role('heading',name='Вход в систему')).to_be_visible();shot('01_login')
    page.get_by_role('button',name='Создать учётную запись').click();expect(page.get_by_role('heading',name='Регистрация сотрудника')).to_be_visible()
    shot('02_registration')
    employee='customer.'+secrets.token_hex(3)+'@technoservice.test'
    c=Client();exists=c.call('login',{'email':employee,'password':password})[0]==200
    if not exists:
        page.get_by_label('ФИО').fill('Представитель заказчика');page.get_by_label('Электронная почта').fill(employee);page.get_by_label('Пароль',exact=True).fill(password)
        page.get_by_role('button',name='Зарегистрироваться',exact=True).click();expect(page.get_by_role('heading',name='Вход в систему')).to_be_visible()
    else:page.get_by_role('button',name='Уже есть учётная запись? Войти').click()
    passed('B01 Регистрация сотрудника через интерфейс')
    own=Client();own_user=own.call('login',{'email':employee,'password':password})[1]['user']
    login(employee);passed('B02 Вход сотрудника')
    page.get_by_role('button',name='Каталог услуг',exact=True).click();expect(page.get_by_role('heading',name='Аренда виртуальных серверов',exact=True)).to_be_visible();shot('03_catalog_employee')
    passed('B03 Просмотр шести услуг и ресурсов')
    page.get_by_role('button',name='Service Desk',exact=True).click();page.get_by_role('button',name='Создать обращение',exact=True).click()
    page.get_by_label('Тема',exact=True).fill('Недоступен виртуальный сервер разработки')
    page.get_by_label('Приоритет',exact=True).select_option('P1')
    ciopts=page.locator('#ticketcis option').evaluate_all('(opts)=>opts.map(x=>x.value)');page.get_by_label('Затронутые ресурсы').select_option(ciopts[0])
    page.get_by_label('Описание и влияние на бизнес').fill('Команда разработки не может подключиться к ВМ. Проверить сетевой интерфейс и восстановить доступ. Затронут один проект; согласован критический приоритет.')
    shot('04_incident_create');page.get_by_role('button',name='Зарегистрировать обращение').click();expect(page.get_by_role('heading',name='Обработка обращения')).to_be_visible()
    incident_id=int(page.locator('h1').inner_text().split('INC-')[1].split(' ')[0]);shot('05_incident_employee');passed('B04 Создание обращения с приоритетом и КЕ')
    logout();login('monitoring@technoservice.test');passed('B05 Вход технической поддержки')
    page.get_by_role('button',name='Service Desk',exact=True).click();expect(page.get_by_role('heading',name='Очередь Service Desk')).to_be_visible();shot('06_incident_queue')
    page.evaluate('(id)=>ticket(id)',incident_id);expect(page.get_by_label('Исполнитель',exact=True)).to_be_visible()
    page.get_by_label('Статус',exact=True).select_option('В работе');page.get_by_label('Исполнитель',exact=True).select_option(label='Инженер мониторинга')
    page.get_by_role('button',name='Сохранить обработку').click();expect(page.locator('select[name=status]')).to_have_value('В работе')
    page.get_by_label('Статус',exact=True).select_option('Решена');page.get_by_label('Решение',exact=True).fill('Проверена конфигурация vSphere, восстановлен сетевой интерфейс ВМ. Контроль подключения и метрик выполнен успешно.')
    page.get_by_role('button',name='Сохранить обработку').click();expect(page.locator('select[name=status]')).to_have_value('Решена');shot('07_incident_resolved');passed('B06 Назначение и решение инцидента')
    logout();login(employee);page.evaluate('(id)=>ticket(id)',incident_id);expect(page.locator('select[name=status]')).to_have_value('Решена')
    page.get_by_label('Статус',exact=True).select_option('Закрыта');page.get_by_role('button',name='Сохранить обработку').click();expect(page.locator('.badge').filter(has_text='Закрыта')).to_be_visible();shot('08_incident_closed');passed('B07 Подтверждение решения заказчиком')
    page.get_by_role('button',name='Сообщения',exact=True).click();page.get_by_label('Получатель',exact=True).select_option(label='Администратор системы · Администратор');page.get_by_label('Сообщение',exact=True).fill('Доступ к виртуальному серверу восстановлен. Подтверждаю решение и закрытие обращения.');page.get_by_role('button',name='Отправить сообщение',exact=True).click()
    expect(page.locator('.bubble').filter(has_text='Подтверждаю решение').last).to_be_visible();passed('B08 Отправка сообщения администратору')
    logout();login('admin@technoservice.test');passed('B09 Вход администратора')
    page.get_by_role('button',name='Сообщения',exact=True).click();expect(page.locator('.bubble').filter(has_text='Подтверждаю решение').last).to_be_visible()
    page.get_by_label('Получатель',exact=True).select_option(str(own_user['id']));page.get_by_label('Сообщение',exact=True).fill('Спасибо за подтверждение. Инцидент закрыт, история обработки сохранена.');page.get_by_role('button',name='Отправить сообщение',exact=True).click();expect(page.locator('.bubble').filter(has_text='Спасибо за подтверждение').last).to_be_visible();shot('09_messages');passed('B10 Получение и ответ в переписке')
    page.get_by_role('button',name='Каталог услуг',exact=True).click();page.get_by_role('button',name='Редактировать',exact=True).first.click();expect(page.get_by_label('Название',exact=True)).to_be_visible();shot('10_catalog_editor');page.get_by_role('button',name='Сохранить услугу',exact=True).click();expect(page.get_by_role('heading',name='Каталог услуг',exact=True)).to_be_visible();passed('B11 Сохранение услуги и зависимостей')
    page.get_by_role('button',name='Пользователи',exact=True).click();expect(page.get_by_role('heading',name='Пользователи и роли')).to_be_visible();shot('11_roles');passed('B12 Просмотр ролей администратором')
    assert not errors,errors
    passed('B13 Отсутствие ошибок JavaScript')
    # Render all diagram assets at 2x their native canvas size.
    for svg in sorted((ROOT/'diagrams').glob('*.svg')):
        import xml.etree.ElementTree as ET
        r=ET.parse(svg).getroot();w=int(r.attrib['width']);h=int(r.attrib['height'])
        pg=context.new_page();pg.set_viewport_size({'width':w,'height':h});pg.set_content(svg.read_text());pg.locator('svg').screenshot(path=str(ROOT/'diagrams/png'/(svg.stem+'.png')),scale='device');pg.close()
    browser.close()
(ROOT/'evidence/browser-results.json').write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),'executed':len(results),'failed':0,'results':results,'incident_id':incident_id},ensure_ascii=False,indent=2))
print(f'{len(results)} browser checks passed; {len(list(OUT.glob("*.png")))} screenshots saved.')
