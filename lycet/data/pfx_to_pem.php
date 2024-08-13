<?php

use Greenter\XMLSecLibs\Certificate\X509Certificate;
use Greenter\XMLSecLibs\Certificate\X509ContentType;

require '../vendor/autoload.php';

$pfx = file_get_contents('ism.pfx');
$password = 'yU6F75x9wM477PdS';

$certificate = new X509Certificate($pfx, $password);
$pem = $certificate->export(X509ContentType::PEM);
    
file_put_contents('20604454558-cert.pem', $pem);