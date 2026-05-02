<?php
ini_set('display_errors', 0);
error_reporting(0);
mysqli_report(MYSQLI_REPORT_OFF);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '');

$username = $_REQUEST['username'] ?? '';
$password = $_REQUEST['password'] ?? '';
$database = $_REQUEST['database'] ?? '';

$idEquipa       = $_REQUEST['idEquipa']       ?? '';
$idUtilizador   = $_REQUEST['idUtilizador']   ?? '';
$descricao      = $_REQUEST['descricao']      ?? '';
$dataHoraInicio = $_REQUEST['dataHoraInicio'] ?? '';

if ($username === '' || $password === '' || $database === '') {
    $response['message'] = 'Credenciais em falta.';
    echo json_encode($response); exit;
}
if ($idEquipa === '' || $idUtilizador === '') {
    $response['message'] = 'IDEquipa e IDUtilizador são obrigatórios.';
    echo json_encode($response); exit;
}

// Default sensato: agora
if ($dataHoraInicio === '') {
    $dataHoraInicio = date('Y-m-d H:i:s');
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

$stmt = $conn->prepare('CALL Criar_jogo(?, ?, ?, ?)');
if (!$stmt) {
    $response['message'] = 'Erro a preparar CALL: ' . $conn->error;
    $conn->close(); echo json_encode($response); exit;
}

$idEquipaInt     = (int)$idEquipa;
$idUtilizadorInt = (int)$idUtilizador;
$stmt->bind_param('iiss', $idEquipaInt, $idUtilizadorInt, $descricao, $dataHoraInicio);

if ($stmt->execute()) {
    $response['success'] = true;
    $response['message'] = 'Jogo criado.';
} else {
    $response['message'] = 'Erro a executar SP: ' . $stmt->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
