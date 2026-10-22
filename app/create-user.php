<?php
require __DIR__.'/bootstrap.php';
[$script,$email,$name,$role]=array_pad($argv,4,'');
if(!filter_var($email,FILTER_VALIDATE_EMAIL)||!in_array($role,['employee','support','admin'],true)||!$name) {fwrite(STDERR,"Usage: php create-user.php EMAIL NAME employee|support|admin (password via stdin)\n");exit(1);}
$password=rtrim(stream_get_contents(STDIN),"\r\n");
if(strlen($password)<10){fwrite(STDERR,"Пароль должен содержать не менее 10 символов\n");exit(1);}
if(query('SELECT id FROM users WHERE email=?',[$email])->fetch()){fwrite(STDERR,"Пользователь уже существует\n");exit(1);}
query('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',[$name,$email,password_hash($password,PASSWORD_DEFAULT),$role]);
echo "Создан пользователь: $email ($role)\n";
