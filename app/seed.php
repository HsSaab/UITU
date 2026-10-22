<?php
require __DIR__.'/bootstrap.php';
db()->exec(file_get_contents(__DIR__.'/schema.sql'));
if(!query('SELECT id FROM services LIMIT 1')->fetch()) {
 $data=json_decode(file_get_contents(dirname(__DIR__).'/data/services.json'),true,512,JSON_THROW_ON_ERROR);
 foreach($data as $s) {
  query('INSERT INTO services(name,description,line,price) VALUES(?,?,?,?)',[$s['name'],$s['description'],$s['line'],$s['price']]);
  $id=(int)db()->lastInsertId();
  foreach($s['cis'] as $name) {
   query('INSERT IGNORE INTO cis(name,kind) VALUES(?,?)',[$name,str_contains($name,'БД')?'База данных':'Ресурс']);
   $ci=query('SELECT id FROM cis WHERE name=?',[$name])->fetchColumn(); query('INSERT INTO service_cis VALUES(?,?)',[$id,$ci]);
  }
 }
 foreach([[1,5],[3,5],[4,5],[6,4]] as $link) query('INSERT INTO service_links VALUES(?,?)',$link);
}
echo "Каталог: ".query('SELECT COUNT(*) FROM services')->fetchColumn()." услуг\n";
