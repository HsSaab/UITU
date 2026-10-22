<?php
require dirname(__DIR__).'/app/domain.php';
$checks=[
 'U01 Приоритет P1'=>fn()=>priority_valid('P1'),
 'U02 Неизвестный приоритет'=>fn()=>!priority_valid('P0'),
 'U03 Новая → В работе'=>fn()=>transition_valid('Новая','В работе'),
 'U04 Запрет закрытия новой'=>fn()=>!transition_valid('Новая','Закрыта'),
 'U05 Закрытая неизменяема'=>fn()=>!transition_valid('Закрыта','В работе'),
 'U06 SLA P1 4 часа'=>fn()=>deadline('2026-10-22 00:00:00','P1')==='2026-10-22 04:00:00',
 'U07 SLA P2 реакция 30 минут'=>fn()=>deadline('2026-10-22 23:50:00','P2',0)==='2026-10-23 00:20:00',
 'U08 SLA P4 72 часа'=>fn()=>deadline('2026-10-22 00:00:00','P4')==='2026-10-25 00:00:00',
 'U09 Фиксация длительности'=>fn()=>elapsed_seconds('2026-10-22 00:00:00','2026-10-22 01:02:03')===3723,
 'U10 Открытая длительность'=>fn()=>elapsed_seconds('2026-10-22 00:00:00',null,strtotime('2026-10-22 01:00:00 UTC'))===3600,
];
$results=[];$failed=0;
foreach($checks as $name=>$check){$ok=$check();$results[]=['name'=>$name,'status'=>$ok?'passed':'failed'];if(!$ok)$failed++;}
echo json_encode($results,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT)."\n";exit($failed?1:0);
