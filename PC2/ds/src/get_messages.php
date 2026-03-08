<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '', 'data' => array());

$username = $_REQUEST['username'] ?? '';
$password = $_REQUEST['password'] ?? '';
$database = $_REQUEST['database'] ?? '';

if (empty($username) || empty($password) || empty($database)) {
    $response['message'] = 'Preencha todos os campos (username, password, database).';
    echo json_encode($response);
    exit;
}

$conn = new mysqli('mysql', $username, $password, $database);

if ($conn->connect_error) {
    $response['message'] = "Erro de conexão MySQL: " . $conn->connect_error;
    echo json_encode($response);
    exit;
}

// CORRIGIDO: nomes reais das colunas (maiúsculas conforme labirinto.sql)
// Retornamos aliases em minúsculas para compatibilidade com o Android
$sql = "SELECT IDMensagem AS id,
               TipoAlerta AS tipoalerta,
               HoraEscrita AS hora,
               Msg AS msg,
               Leitura AS leitura,
               Sensor AS sensor
        FROM mensagens
        ORDER BY IDMensagem DESC";

$result = $conn->query($sql);

if ($result) {
    $messages = array();
    while ($row = $result->fetch_assoc()) {
        $messages[] = $row;
    }
    $response['success'] = true;
    $response['data']    = $messages;
    $response['message'] = 'Mensagens carregadas com sucesso.';
} else {
    $response['message'] = 'Erro ao executar consulta: ' . $conn->error;
}

$conn->close();
echo json_encode($response);
?>
