<?php
// api_simulacoes.php
header('Content-Type: application/json');
require 'db.php';

$method = $_SERVER['REQUEST_METHOD'];
$data = json_decode(file_get_contents("php://input"), true);

try {
    if ($method === 'GET') {
        $res = $mysqli->query("SELECT * FROM simulacao ORDER BY IDSimulacao DESC");
        echo json_encode($res->fetch_all(MYSQLI_ASSOC));

    } elseif ($method === 'POST') {
        $dataHoraInicio = date('Y-m-d H:i:s');
        $stmt = $mysqli->prepare("CALL Criar_jogo(?, ?, ?, ?)");
        $stmt->bind_param("iiss", $data['id_equipa'], $data['id_utilizador'], $data['descricao'], $dataHoraInicio);
        $stmt->execute();
        echo json_encode(["sucesso" => "Simulação criada! Podes iniciá-la agora."]);

    } elseif ($method === 'PUT') {
        $stmt = $mysqli->prepare("CALL Alterar_jogo(?, ?)");
        $stmt->bind_param("is", $data['id'], $data['descricao']);
        $stmt->execute();
        echo json_encode(["sucesso" => "Simulação atualizada!"]);
    }
} catch (Exception $e) {
    echo json_encode(["erro" => "Erro BD: " . $e->getMessage()]);
}
$mysqli->close();
?>