<?php
require dirname(__DIR__).'/app/bootstrap.php';
$suffix=$argv[1]??'';
if(!preg_match('/^[a-f0-9]{8}$/',$suffix)){fwrite(STDERR,"Expected an isolated 8-character test suffix\n");exit(1);}
$userIds=query('SELECT id FROM users WHERE email LIKE ?',['%.'.$suffix.'@example.test'])->fetchAll(PDO::FETCH_COLUMN);
if(!$userIds)exit;
$placeholders=implode(',',array_fill(0,count($userIds),'?'));
db()->beginTransaction();
query("DELETE h FROM history h JOIN incidents i ON h.incident_id=i.id WHERE i.author_id IN ($placeholders)",$userIds);
query("DELETE FROM incidents WHERE author_id IN ($placeholders)",$userIds);
query("DELETE FROM messages WHERE sender_id IN ($placeholders) OR recipient_id IN ($placeholders)",array_merge($userIds,$userIds));
query("DELETE FROM users WHERE id IN ($placeholders)",$userIds);db()->commit();
