<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '', 'data' => array());

$username = $_REQUEST['username'] ?? '';
$password = $_REQUEST['password'] ?? '';
$database = $_REQUEST['database'] ?? '';

if (empty($username) || empty($password) || empty($database)) {
    $response['message'] = 'Preencha todos os campos.';
    echo json_encode($response);
    exit;
}

$conn = new mysqli('mysql', $username, $password, $database);

if ($conn->connect_error) {
    $response['message'] = "Erro de conexão: " . $conn->connect_error;
    echo json_encode($response);
    exit;
}

// CORRIGIDO: colunas Som e IDSom (maiúsculas conforme labirinto.sql)
// Aliases em minúsculas para compatibilidade com o Android
$sql = "SELECT Som AS som, IDSom AS idsom FROM som ORDER BY IDSom ASC";
$result = $conn->query($sql);

if ($result) {
    $soundData = array();
    while ($row = $result->fetch_assoc()) {
        $soundData[] = $row;
    }
    $response['success'] = true;
    $response['data']    = $soundData;
    $response['message'] = 'Dados de som carregados com sucesso.';
} else {
    $response['message'] = "Erro na query: " . $conn->error;
}

$conn->close();
echo json_encode($response);
?>
