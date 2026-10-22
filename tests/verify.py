"""Isolated module/API checks against the running development server.
All test users and test objects use an explicit isolated suffix.
Run only on a development database, never on production.
"""
import json, secrets, subprocess, urllib.request, urllib.error, http.cookiejar, unittest
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8080/index.php?api='
class Client:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf=''
        self.csrf=self.call('session',csrf=False)[1]['csrf']
    def call(self, api, data=None, csrf=True):
        headers={'Content-Type':'application/json'}
        if csrf: headers['X-CSRF-Token']=self.csrf
        request=urllib.request.Request(BASE+api,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try: r=self.opener.open(request)
        except urllib.error.HTTPError as e: r=e
        code=r.code
        result=json.load(r)
        if isinstance(result,dict) and 'csrf' in result: self.csrf=result['csrf']
        return code,result

class Modules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suffix=secrets.token_hex(4);cls.pw=secrets.token_urlsafe(18)
        cls.clients={};cls.ids={}
        for r,n in [('admin','Администратор тестирования'),('support','Инженер мониторинга'),('employee','Сотрудник заказчика'),('other','Другой сотрудник')]:
            email=f'{r}.{cls.suffix}@example.test'
            subprocess.run(['bash',str(ROOT/'scripts/php.sh'),str(ROOT/'app/create-user.php'),email,n,r if r!='other' else 'employee'],input=cls.pw,text=True,capture_output=True,check=True)
            c=Client();code,result=c.call('login',{'email':email,'password':cls.pw});assert code==200
            cls.clients[r]=c;cls.ids[r]=result['user']['id']
        cls.admin=cls.clients['admin'];cls.support=cls.clients['support'];cls.employee=cls.clients['employee'];cls.other=cls.clients['other']
        _,cls.services=cls.admin.call('services'); cls.service=cls.services[0]
        cls.draft={'name':'Тестовая услуга '+cls.suffix,'description':'Проверка CRUD','line':'Управление','price':'Учебный тариф','status':'Готова к эксплуатации','cis':[cls.service['cis'][0]['id']],'dependencies':[cls.service['id']]}
    @classmethod
    def tearDownClass(cls):
        subprocess.run(['bash',str(ROOT/'scripts/php.sh'),str(ROOT/'tests/cleanup.php'),cls.suffix],capture_output=True,text=True,check=True)
    def make_ticket(self,client=None):
        return (client or self.employee).call('incidents',{'title':'Потеря доступа к ВМ','description':'Виртуальный сервер недоступен; остановлено тестирование.','service_id':self.service['id'],'priority':'P1','cis':[self.service['cis'][0]['id']]})
    def test_01_catalog_seed(self):
        self.assertEqual(len(self.services),6);self.assertIn('500 ₽',self.service['price']);self.assertTrue(all(s['cis'] for s in self.services))
    def test_02_catalog_crud(self):
        code,rows=self.admin.call('services',self.draft);self.assertEqual(code,200)
        s=next(r for r in rows if r['name']==self.draft['name'])
        code,rows=self.admin.call('services',{**self.draft,'id':s['id'],'name':self.draft['name']+' изменена','status':'Эксплуатируется'});self.assertEqual(code,200)
        edited=next(r for r in rows if r['id']==s['id']);self.assertEqual(edited['status'],'Эксплуатируется');self.assertEqual(len(edited['cis']),1);self.assertEqual(len(edited['dependencies']),1)
        code,rows=self.admin.call('services',{'id':s['id'],'action':'delete'});self.assertEqual(code,200);self.assertNotIn(s['id'],[r['id'] for r in rows])
    def test_03_catalog_acl(self):
        self.assertEqual(self.employee.call('services',self.draft)[0],403)
    def test_04_catalog_validation(self):
        self.assertEqual(self.admin.call('services',{**self.draft,'cis':[9999999]})[0],422)
    def test_05_incident_registration(self):
        code,r=self.make_ticket();self.assertEqual(code,200);self.assertEqual(r['status'],'Новая');self.assertEqual(r['priority'],'P1')
        self.assertEqual(self.employee.call('incident&id='+str(r['id']))[1]['cis'][0]['id'],self.service['cis'][0]['id'])
    def test_06_incident_isolation(self):
        _,r=self.make_ticket();self.assertEqual(self.other.call('incident&id='+str(r['id']))[0],403)
        rows=self.other.call('incidents')[1];self.assertNotIn(r['id'],[x['id'] for x in rows])
    def test_07_incident_lifecycle(self):
        _,r=self.make_ticket();id=r['id']
        code,r=self.support.call('incident',{'id':id,'status':'В работе','assignee_id':self.ids['support']});self.assertEqual(code,200);self.assertTrue(r['responded_at'])
        code,r=self.support.call('incident',{'id':id,'status':'Ожидание'});self.assertEqual(code,200);self.assertFalse(r['resolved_at'])
        self.assertEqual(self.support.call('incident',{'id':id,'status':'В работе'})[0],200)
        code,r=self.support.call('incident',{'id':id,'status':'Решена','resolution':'Восстановлена конфигурация сетевого интерфейса ВМ'});self.assertEqual(code,200);self.assertTrue(r['resolved_at']);self.assertGreaterEqual(r['elapsed_seconds'],0)
        code,r=self.employee.call('incident',{'id':id,'status':'Закрыта'});self.assertEqual(code,200);self.assertEqual(r['status'],'Закрыта');self.assertGreaterEqual(len(r['history']),6)
    def test_08_incident_invalid_transition(self):
        _,r=self.make_ticket();self.assertEqual(self.support.call('incident',{'id':r['id'],'status':'Закрыта'})[0],422)
    def test_09_incident_priority_audit(self):
        _,r=self.make_ticket();self.assertEqual(self.support.call('incident',{'id':r['id'],'priority':'P2'})[0],422)
        code,r=self.support.call('incident',{'id':r['id'],'priority':'P2','comment':'Подтверждён обходной путь'});self.assertEqual(code,200);self.assertEqual(r['priority'],'P2');self.assertIn('Подтверждён',r['history'][-1]['action'])
    def test_10_incident_permissions(self):
        _,r=self.make_ticket();self.assertEqual(self.employee.call('incident',{'id':r['id'],'status':'В работе'})[0],403)
    def test_11_incident_invalid_ci(self):
        self.assertEqual(self.employee.call('incidents',{'title':'Тест','description':'Неверный CI','service_id':self.service['id'],'priority':'P1','cis':[9999999]})[0],422)
    def test_12_messages_exchange(self):
        marker='Проверка переписки '+self.suffix
        code,rows=self.employee.call('messages',{'recipient_id':self.ids['admin'],'body':marker});self.assertEqual(code,200)
        self.assertTrue(any(x['body']==marker for x in self.admin.call('messages')[1]))
        self.assertEqual(self.admin.call('messages',{'recipient_id':self.ids['employee'],'body':'Заявка принята'})[0],200)
    def test_13_messages_isolation(self):
        marker='Личное '+self.suffix;self.employee.call('messages',{'recipient_id':self.ids['admin'],'body':marker})
        self.assertFalse(any(x['body']==marker for x in self.other.call('messages')[1]))
    def test_14_messages_empty(self):
        self.assertEqual(self.employee.call('messages',{'recipient_id':self.ids['admin'],'body':' '})[0],422)
    def test_15_auth_registration(self):
        c=Client();email=f'new.{self.suffix}@example.test'
        self.assertEqual(c.call('register',{'name':'Новый сотрудник','email':email,'password':self.pw,'role':'admin'})[0],200)
        code,r=c.call('login',{'email':email,'password':self.pw});self.assertEqual(code,200);self.assertEqual(r['user']['role'],'employee')
    def test_16_auth_wrong_password(self):
        self.assertEqual(Client().call('login',{'email':f'employee.{self.suffix}@example.test','password':'wrong'})[0],401)
    def test_17_auth_unauthorized(self):
        self.assertEqual(Client().call('incidents')[0],401)
    def test_18_auth_csrf(self):
        self.assertEqual(self.employee.call('messages',{'recipient_id':self.ids['admin'],'body':'test'},csrf=False)[0],403)
    def test_19_auth_role_protection(self):
        self.assertEqual(self.employee.call('users',{'id':self.ids['employee'],'role':'admin'})[0],403)
    def test_20_catalog_referenced_delete(self):
        self.make_ticket();self.assertEqual(self.admin.call('services',{'id':self.service['id'],'action':'delete'})[0],409)

if __name__=='__main__':
    class Results(unittest.TextTestResult):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.items=[]
        def addSuccess(self,test):super().addSuccess(test);self.items.append({'name':test._testMethodName,'status':'passed'})
        def addFailure(self,test,err):super().addFailure(test,err);self.items.append({'name':test._testMethodName,'status':'failed'})
        def addError(self,test,err):super().addError(test,err);self.items.append({'name':getattr(test,'_testMethodName',str(test)),'status':'error'})
    r=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(unittest.defaultTestLoader.loadTestsFromTestCase(Modules))
    out={'timestamp':datetime.now(timezone.utc).isoformat(),'executed':r.testsRun,'failed':len(r.failures),'errors':len(r.errors),'results':r.items}
    dest=ROOT/'evidence';dest.mkdir(exist_ok=True);(dest/'api-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(not r.wasSuccessful())
