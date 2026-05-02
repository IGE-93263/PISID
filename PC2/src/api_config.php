<?php
// api_config.php
header('Content-Type: application/json');
require 'db.php';
$method = $_SERVER['REQUEST_METHOD'];

try {
    if ($method === 'GET') {
        // Busca o limite atual
        $temp = $mysqli->query("SELECT maximo, minimo FROM configtemp LIMIT 1")->fetch_assoc();
        $som = $mysqli->query("SELECT maximo FROM configsound LIMIT 1")->fetch_assoc();
        echo json_encode(["temp" => $temp, "som" => $som]);

    } elseif ($method === 'POST') {
        $data = json_decode(file_get_contents("php://input"), true);

        $stmtT = $mysqli->prepare("UPDATE configtemp SET maximo=?, minimo=? LIMIT 1");
        $stmtT->bind_param("ss", $data['temp_max'], $data['temp_min']);
        $stmtT->execute();

        $stmtS = $mysqli->prepare("UPDATE configsound SET maximo=? LIMIT 1");
        $stmtS->bind_param("s", $data['som_max']);
        $stmtS->execute();

        echo json_encode(["sucesso" => "Limites dos Sensores atualizados na BD! Os Triggers vão usar as novas regras."]);
    }
} catch (Exception $e) {
    echo json_encode(["erro" => "Erro de Configuração: " . $e->getMessage()]);
}
$mysqli->close();
?>