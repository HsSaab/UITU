<?php
declare(strict_types=1);
require_once __DIR__.'/domain.php';
function db(): PDO {
 static $db;
 if (!$db) {
   $socket=getenv('UITU_DB_SOCKET') ?: dirname(__DIR__).'/.runtime/mysql.sock';
   $db=new PDO('mysql:unix_socket='.$socket.';dbname=uitu;charset=utf8mb4', 'uitu', '', [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,PDO::ATTR_EMULATE_PREPARES=>false]);
 }
 return $db;
}
function query(string $sql,array $args=[]): PDOStatement { $s=db()->prepare($sql); $s->execute($args); return $s; }
function fail(int $code,string $message): never { http_response_code($code); echo json_encode(['error'=>$message],JSON_UNESCAPED_UNICODE); exit; }
function user(): array { if(empty($_SESSION['uid'])) fail(401,'Войдите в систему'); $u=query('SELECT id,name,email,role FROM users WHERE id=?',[$_SESSION['uid']])->fetch(); if(!$u) fail(401,'Сессия недействительна'); return $u; }
function staff(array $u): void { if(!in_array($u['role'],['admin','support'],true)) fail(403,'Недостаточно прав'); }
function admin(array $u): void { if($u['role']!=='admin') fail(403,'Требуются права администратора'); }
function required(array $data,string $key,int $limit=2000): string { $v=trim((string)($data[$key]??'')); $length=preg_match_all('/./us',$v); if($v==='' || $length===false || $length>$limit) fail(422,'Проверьте поле: '.$key); return $v; }
function ids(mixed $v): array { if(!is_array($v)) fail(422,'Ожидается список идентификаторов'); return array_values(array_unique(array_map('intval',$v))); }
function ensure_ids(array $values,string $table): void { foreach($values as $v) if(!query("SELECT id FROM $table WHERE id=?",[$v])->fetch()) fail(422,'Неизвестный объект'); }
function incident(int $id,array $u): array { $r=query('SELECT i.*,u.name author,s.name service,a.name assignee FROM incidents i JOIN users u ON i.author_id=u.id JOIN services s ON i.service_id=s.id LEFT JOIN users a ON a.id=i.assignee_id WHERE i.id=?',[$id])->fetch(); if(!$r) fail(404,'Заявка не найдена'); if($u['role']==='employee' && (int)$r['author_id']!==(int)$u['id']) fail(403,'Нет доступа к заявке'); return $r; }
function incident_output(array $r): array { $r['deadline']=deadline($r['created_at'],$r['priority']); $r['response_deadline']=deadline($r['created_at'],$r['priority'],0); $r['elapsed_seconds']=elapsed_seconds($r['created_at'],$r['resolved_at']); $r['overdue']=($r['resolved_at']??gmdate('Y-m-d H:i:s'))>$r['deadline']; return $r; }
