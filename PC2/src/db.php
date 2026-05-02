<?php
// db.php — ligação central ao MySQL
// Usada pelos api_*.php (web) e pelo PHP do Android (maze_app_php/)
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

$host = 'mysql';       // nome do serviço no docker-compose
$db   = 'labirinto';
$user = 'root';
$pass = 'root';        // conforme MYSQL_ROOT_PASSWORD no docker-compose

try {
    $mysqli = new mysqli($host, $user, $pass, $db);
    $mysqli->set_charset("utf8mb4");
} catch (mysqli_sql_exception $e) {
    http_response_code(500);
    echo json_encode(["erro" => "Erro na ligação à Base de Dados: " . $e->getMessage()]);
    exit;
}
?>
