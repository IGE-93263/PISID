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

$host   = 'mysql';
$conn   = new mysqli($host, $username, $password, $database);

if ($conn->connect_error) {
    $response['message'] = "Erro de conexão MySQL: " . $conn->connect_error;
    echo json_encode($response);
    exit;
}

// CORRIGIDO: coluna chama-se IDSala (não Sala) — retornamos como "Sala"
// para manter compatibilidade com o Android que espera "Sala"
$sql = "SELECT IDSala AS Sala, NumeroMarsamisEven, NumeroMarsamisOdd
        FROM ocupacaolabirinto
        ORDER BY IDSala ASC";
$result = $conn->query($sql);

if ($result) {
    $rooms = array();
    while ($row = $result->fetch_assoc()) {
        $rooms[] = $row;
    }
    $response['success'] = true;
    $response['data']    = $rooms;
    $response['message'] = 'Dados das salas carregados com sucesso.';
} else {
    $response['message'] = 'Erro ao executar consulta: ' . $conn->error;
}

$conn->close();
echo json_encode($response);
?>
