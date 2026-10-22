<?php
declare(strict_types=1);
ini_set('session.cookie_httponly','1'); ini_set('session.cookie_samesite','Strict');
session_save_path(dirname(__DIR__,2).'/.runtime/sessions'); session_start();
require dirname(__DIR__).'/bootstrap.php';
if(!isset($_GET['api'])) { readfile(__DIR__.'/shell.html'); exit; }
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
try {
 $api=$_GET['api']; $method=$_SERVER['REQUEST_METHOD']; $data=[];
 if($method==='POST') {
  if(!isset($_SESSION['csrf']) || !hash_equals($_SESSION['csrf'],$_SERVER['HTTP_X_CSRF_TOKEN']??'')) fail(403,'Недействительный CSRF-токен');
  $data=json_decode(file_get_contents('php://input'),true,512,JSON_THROW_ON_ERROR);
  if(!is_array($data)) fail(422,'Ожидается JSON-объект');
 } elseif($method!=='GET') fail(405,'Метод не поддерживается');
 if($api==='session') {
  $_SESSION['csrf']??=bin2hex(random_bytes(24));
  $out=['csrf'=>$_SESSION['csrf'],'user'=>empty($_SESSION['uid'])?null:user()];
 } elseif($api==='register' && $method==='POST') {
  $email=strtolower(required($data,'email',190)); $name=required($data,'name',120); $pw=required($data,'password',128);
  if(!filter_var($email,FILTER_VALIDATE_EMAIL)||preg_match_all('/./us',$pw)<10) fail(422,'Нужны корректная почта и пароль от 10 символов');
  if(query('SELECT id FROM users WHERE email=?',[$email])->fetch()) fail(409,'Этот адрес уже зарегистрирован');
  query('INSERT INTO users(name,email,password) VALUES(?,?,?)',[$name,$email,password_hash($pw,PASSWORD_DEFAULT)]);
  $out=['id'=>(int)db()->lastInsertId(),'message'=>'Регистрация завершена. Войдите в систему.'];
 } elseif($api==='login' && $method==='POST') {
  $r=query('SELECT * FROM users WHERE email=?',[strtolower(required($data,'email',190))])->fetch();
  if(!$r||!password_verify((string)($data['password']??''),$r['password'])) fail(401,'Неверная почта или пароль');
  session_regenerate_id(true); $_SESSION['uid']=$r['id']; $_SESSION['csrf']=bin2hex(random_bytes(24)); $out=['user'=>user(),'csrf'=>$_SESSION['csrf']];
 } else {
  $u=user();
  if($api==='logout' && $method==='POST') { $_SESSION=[]; session_regenerate_id(true); $out=['ok'=>true]; }
  elseif($api==='users') {
   if($method==='POST') { admin($u); $role=$data['role']??''; if(!in_array($role,['employee','support','admin'],true)) fail(422,'Неизвестная роль'); if((int)$data['id']===(int)$u['id']) fail(422,'Нельзя менять собственную роль'); query('UPDATE users SET role=? WHERE id=?',[$role,(int)$data['id']]); }
   $out=query('SELECT id,name,email,role FROM users ORDER BY name')->fetchAll();
  } elseif($api==='cis') $out=query('SELECT * FROM cis ORDER BY name')->fetchAll();
  elseif($api==='services') {
   if($method==='POST') {
    admin($u); $id=(int)($data['id']??0); $action=$data['action']??'save';
    if($id && !query('SELECT id FROM services WHERE id=?',[$id])->fetch()) fail(404,'Услуга не найдена');
    if($action==='delete') {
     if(query('SELECT id FROM incidents WHERE service_id=? LIMIT 1',[$id])->fetch()) fail(409,'У услуги есть обращения. Переведите её в архив.');
     query('DELETE FROM services WHERE id=?',[$id]);
    } else {
     $name=required($data,'name',190); $description=required($data,'description'); $price=required($data,'price',190);
     $line=$data['line']??''; $status=$data['status']??'';
     if(!in_array($line,['Доступ/аренда','Управление'],true)||!in_array($status,['Эксплуатируется','Готова к эксплуатации','Архив'],true)) fail(422,'Неверная линия или статус');
     $cis=ids($data['cis']??[]); $deps=ids($data['dependencies']??[]); ensure_ids($cis,'cis'); ensure_ids($deps,'services');
     if($id && in_array($id,$deps,true)) fail(422,'Услуга не может зависеть от себя');
     db()->beginTransaction();
     if($id) query('UPDATE services SET name=?,description=?,line=?,price=?,status=? WHERE id=?',[$name,$description,$line,$price,$status,$id]);
     else { query('INSERT INTO services(name,description,line,price,status) VALUES(?,?,?,?,?)',[$name,$description,$line,$price,$status]); $id=(int)db()->lastInsertId(); }
     query('DELETE FROM service_cis WHERE service_id=?',[$id]); foreach($cis as $ci) query('INSERT INTO service_cis VALUES(?,?)',[$id,$ci]);
     query('DELETE FROM service_links WHERE service_id=?',[$id]); foreach($deps as $dep) query('INSERT INTO service_links VALUES(?,?)',[$id,$dep]);
     db()->commit();
    }
   }
   $out=query('SELECT * FROM services ORDER BY id')->fetchAll();
   foreach($out as &$r) { $r['cis']=query('SELECT c.* FROM cis c JOIN service_cis s ON s.ci_id=c.id WHERE s.service_id=?',[$r['id']])->fetchAll(); $r['dependencies']=query('SELECT s.id,s.name FROM services s JOIN service_links l ON l.dependency_id=s.id WHERE l.service_id=?',[$r['id']])->fetchAll(); } unset($r);
  } elseif($api==='incidents') {
   if($method==='POST') {
    $service=(int)($data['service_id']??0); $p=$data['priority']??'';
    if(!priority_valid($p)) fail(422,'Неизвестный приоритет');
    if(!query("SELECT id FROM services WHERE id=? AND status='Эксплуатируется'",[$service])->fetch()) fail(422,'Выберите действующую услугу');
    $cis=ids($data['cis']??[]);
    foreach($cis as $ci) if(!query('SELECT ci_id FROM service_cis WHERE service_id=? AND ci_id=?',[$service,$ci])->fetch()) fail(422,'Конфигурационная единица не относится к услуге');
    $title=required($data,'title',190); $description=required($data,'description',5000); db()->beginTransaction();
    query('INSERT INTO incidents(title,description,service_id,author_id,priority,created_at) VALUES(?,?,?,?,?,UTC_TIMESTAMP())',[$title,$description,$service,$u['id'],$p]);
    $id=(int)db()->lastInsertId(); foreach($cis as $ci) query('INSERT INTO incident_cis VALUES(?,?)',[$id,$ci]);
    query('INSERT INTO history(incident_id,user_id,action,created_at) VALUES(?,?,?,UTC_TIMESTAMP())',[$id,$u['id'],'Создана заявка, приоритет '.$p]); db()->commit();
    $out=incident_output(incident($id,$u));
   } else {
    $sql='SELECT i.*,u.name author,s.name service,a.name assignee FROM incidents i JOIN users u ON u.id=i.author_id JOIN services s ON s.id=i.service_id LEFT JOIN users a ON a.id=i.assignee_id';
    $where=$u['role']==='employee'?' WHERE i.author_id=?':'';
    $out=array_map('incident_output',query($sql.$where.' ORDER BY i.priority,i.created_at,i.id',$where?[$u['id']]:[])->fetchAll());
   }
  } elseif($api==='incident') {
   $id=(int)($_GET['id']??$data['id']??0); $r=incident($id,$u);
   if($method==='POST') {
    $to=$data['status']??$r['status'];
    if($u['role']==='employee') {
     if($r['status']!=='Решена'||!in_array($to,['Закрыта','В работе'],true)) fail(403,'Автор может подтвердить решение или вернуть заявку');
    } else staff($u);
    if($to!==$r['status'] && !transition_valid($r['status'],$to)) fail(422,'Недопустимый переход статуса');
    $p=$u['role']==='employee'?$r['priority']:($data['priority']??$r['priority']); if(!priority_valid($p)) fail(422,'Неизвестный приоритет');
    $assignee=$u['role']==='employee'?$r['assignee_id']:($data['assignee_id']??$r['assignee_id']);
    if($assignee && !query("SELECT id FROM users WHERE id=? AND role IN ('admin','support')",[$assignee])->fetch()) fail(422,'Исполнитель должен относиться к поддержке');
    $resolution=trim((string)($data['resolution']??$r['resolution']??''));
    if($to==='Решена' && $resolution==='') fail(422,'Опишите выполненное решение');
    if($r['status']==='Закрыта') fail(422,'Закрытая заявка доступна только для чтения');
    $now=gmdate('Y-m-d H:i:s'); $responded=$r['responded_at']??($u['role']!=='employee'?$now:null);
    $resolved=$to==='Решена'?($r['resolved_at']??$now):($to==='Закрыта'?$r['resolved_at']:null);
    $comment=trim((string)($data['comment']??''));
    if($p!==$r['priority'] && $comment==='') fail(422,'Укажите причину изменения приоритета');
    db()->beginTransaction();
    query('UPDATE incidents SET priority=?,status=?,assignee_id=?,resolution=?,responded_at=?,resolved_at=? WHERE id=?',[$p,$to,$assignee?:null,$resolution,$responded,$resolved,$id]);
    $action=$r['status'].' → '.$to.'; '.$r['priority'].' → '.$p.($comment?'; '.$comment:'');
    query('INSERT INTO history(incident_id,user_id,action,created_at) VALUES(?,?,?,UTC_TIMESTAMP())',[$id,$u['id'],$action]); db()->commit(); $r=incident($id,$u);
   }
   $out=incident_output($r);
   $out['cis']=query('SELECT c.* FROM cis c JOIN incident_cis i ON i.ci_id=c.id WHERE i.incident_id=?',[$id])->fetchAll();
   $out['history']=query('SELECT h.*,u.name FROM history h JOIN users u ON u.id=h.user_id WHERE incident_id=? ORDER BY h.id',[$id])->fetchAll();
  } elseif($api==='messages') {
   if($method==='POST') {
    $to=(int)($data['recipient_id']??0); $body=required($data,'body',5000);
    if($to===(int)$u['id']||!query('SELECT id FROM users WHERE id=?',[$to])->fetch()) fail(422,'Выберите другого получателя');
    query('INSERT INTO messages(sender_id,recipient_id,body,created_at) VALUES(?,?,?,UTC_TIMESTAMP())',[$u['id'],$to,$body]);
   }
   $out=query('SELECT m.*,s.name sender,r.name recipient FROM messages m JOIN users s ON s.id=m.sender_id JOIN users r ON r.id=m.recipient_id WHERE sender_id=? OR recipient_id=? ORDER BY m.id',[$u['id'],$u['id']])->fetchAll();
  } else fail(404,'Метод API не найден');
 }
 echo json_encode($out,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
} catch(JsonException $e) { fail(400,'Некорректный JSON'); }
catch(PDOException $e) { if(db()->inTransaction()) db()->rollBack(); error_log('Database error: '.$e->getCode()); fail(500,'Не удалось выполнить операцию с базой данных'); }
