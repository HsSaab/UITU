<?php
declare(strict_types=1);
const SLA = ['P1'=>[15,240], 'P2'=>[30,480], 'P3'=>[120,1440], 'P4'=>[240,4320]];
const TRANSITIONS = ['Новая'=>['В работе'], 'В работе'=>['Ожидание','Решена'], 'Ожидание'=>['В работе'], 'Решена'=>['Закрыта','В работе'], 'Закрыта'=>[]];
function priority_valid(string $p): bool { return isset(SLA[$p]); }
function transition_valid(string $from, string $to): bool { return in_array($to, TRANSITIONS[$from] ?? [], true); }
function elapsed_seconds(string $opened, ?string $resolved, ?int $now=null): int { return max(0, ($resolved ? strtotime($resolved.' UTC') : ($now ?? time())) - strtotime($opened.' UTC')); }
function deadline(string $opened, string $priority, int $index=1): string { return gmdate('Y-m-d H:i:s', strtotime($opened.' UTC') + SLA[$priority][$index]*60); }
