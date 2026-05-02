<?php
ini_set('display_errors', 0);
error_reporting(0);
mysqli_report(MYSQLI_REPORT_OFF);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '');

$username = $_REQUEST['username'] ?? '';
$password = $_REQUEST['password'] ?? '';
$database = $_REQUEST['database'] ?? '';
$idUtilizador = $_REQUEST['idUtilizador'] ?? '';

if ($username === '' || $password === '' || $database === '' || $idUtilizador === '') {
    $response['message'] = 'Credenciais e idUtilizador são obrigatórios.';
    echo json_encode($response); exit;
}

$callerTipo = $_REQUEST['caller_tipo'] ?? '';
if ($callerTipo === 'Admin') {
    $db_user = 'admin_app'; $db_pass = 'admin_pw';
} else {
    $db_user = 'user_app';  $db_pass = 'user_pw';
}
$conn = new mysqli('mysql', $db_user, $db_pass, $database);
if ($conn->connect_error) {
    $response['message'] = 'Erro de conexão: ' . $conn->connect_error;
    echo json_encode($response); exit;
}

$stmt = $conn->prepare('CALL Remover_utilizador(?)');
if (!$stmt) {
    $response['message'] = 'Erro a preparar CALL: ' . $conn->error;
    $conn->close(); echo json_encode($response); exit;
}

$idInt = (int)$idUtilizador;
$stmt->bind_param('i', $idInt);

if ($stmt->execute()) {
    $response['success'] = true;
    $response['message'] = 'Utilizador removido.';
} else {
    // Caso típico: FK constraint (utilizador tem simulações associadas)
    $response['message'] = 'Erro a executar SP: ' . $stmt->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
