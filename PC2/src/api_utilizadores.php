<?php
// api_utilizadores.php
header('Content-Type: application/json');
require 'db.php';

$method = $_SERVER['REQUEST_METHOD'];
$data = json_decode(file_get_contents("php://input"), true);

try {
    if ($method === 'GET') {
        $res = $mysqli->query("SELECT * FROM utilizador ORDER BY IDUtilizador DESC");
        echo json_encode($res->fetch_all(MYSQLI_ASSOC));

    } elseif ($method === 'POST') {
        $stmt = $mysqli->prepare("CALL Criar_utilizador(?, ?, ?, ?, ?, ?)");
        $stmt->bind_param("isssss", $data['equipa'], $data['nome'], $data['telemovel'], $data['tipo'], $data['email'], $data['data_nascimento']);
        $stmt->execute();
        echo json_encode(["sucesso" => "Utilizador criado com sucesso!"]);

    } elseif ($method === 'PUT') {
        $stmt = $mysqli->prepare("CALL Alterar_utilizador(?, ?, ?, ?, ?, ?)");
        $stmt->bind_param("isssss", $data['id'], $data['nome'], $data['telemovel'], $data['tipo'], $data['email'], $data['data_nascimento']);
        $stmt->execute();
        echo json_encode(["sucesso" => "Utilizador atualizado!"]);

    } elseif ($method === 'DELETE') {
        $stmt = $mysqli->prepare("CALL Remover_utilizador(?)");
        $stmt->bind_param("i", $data['id']);
        $stmt->execute();
        echo json_encode(["sucesso" => "Utilizador apagado com sucesso!"]);
    }
} catch (Exception $e) {
    echo json_encode(["erro" => "Erro BD: " . $e->getMessage()]);
}
$mysqli->close();
?>