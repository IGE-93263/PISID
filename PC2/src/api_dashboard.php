<?php
// api_dashboard.php
header('Content-Type: application/json');
require 'db.php';

// Lê o ID da simulação passada pelo Javascript
$id_sim = isset($_GET['id']) ? intval($_GET['id']) : 0;

if ($id_sim === 0) {
    echo json_encode(["erro" => "ID de simulação inválido."]);
    exit;
}

try {
    // 1. Temperaturas dessa simulação
    $resTemp = $mysqli->query("SELECT Hora, Temperatura FROM temperatura WHERE IDSimulacao = $id_sim ORDER BY Hora DESC LIMIT 10");
    $temps = $resTemp->fetch_all(MYSQLI_ASSOC);

    // 2. Som dessa simulação
    $resSom = $mysqli->query("SELECT Hora, Som FROM som WHERE IDSimulacao = $id_sim ORDER BY Hora DESC LIMIT 10");
    $sons = $resSom->fetch_all(MYSQLI_ASSOC);

    // 3. Ocupação (Agrupada pelas salas mais recentes)
    $resOcupacao = $mysqli->query("SELECT IDSala, NumeroMarsamisEven, NumeroMarsamisOdd FROM ocupacaolabirinto WHERE IDSimulacao = $id_sim ORDER BY DataCriacao DESC LIMIT 10");
    $ocupacao = $resOcupacao->fetch_all(MYSQLI_ASSOC);

    // O array_reverse é usado para o gráfico ficar da esquerda (mais antigo) para a direita (mais recente)
    echo json_encode([
        "temperaturas" => array_reverse($temps),
        "sons" => array_reverse($sons),
        "ocupacao" => $ocupacao
    ]);
} catch (Exception $e) {
    echo json_encode(["erro" => "Erro no Dashboard: " . $e->getMessage()]);
}
$mysqli->close();
?>