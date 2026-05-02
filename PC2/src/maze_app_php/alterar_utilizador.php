<?php
ini_set('display_errors', 0);
error_reporting(0);
mysqli_report(MYSQLI_REPORT_OFF);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '');

$username = $_REQUEST['username'] ?? '';
$password = $_REQUEST['password'] ?? '';
$database = $_REQUEST['database'] ?? '';

$idUtilizador   = $_REQUEST['idUtilizador']   ?? '';
$nome           = $_REQUEST['nome']           ?? '';
$telemovel      = $_REQUEST['telemovel']      ?? '';
$tipo           = $_REQUEST['tipo']           ?? '';
$email          = $_REQUEST['email']          ?? '';
$dataNascimento = $_REQUEST['dataNascimento'] ?? '';

if ($username === '' || $password === '' || $database === '') {
    $response['message'] = 'Credenciais em falta.';
    echo json_encode($response); exit;
}
if ($idUtilizador === '') {
    $response['message'] = 'IDUtilizador é obrigatório.';
    echo json_encode($response); exit;
}

// Dispatch pelo Tipo do utilizador AUTENTICADO (vem em caller_tipo).
// O campo 'tipo' é o Tipo do utilizador alvo da edição.
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

$stmt = $conn->prepare('CALL Alterar_utilizador(?, ?, ?, ?, ?, ?)');
if (!$stmt) {
    $response['message'] = 'Erro a preparar CALL: ' . $conn->error;
    $conn->close(); echo json_encode($response); exit;
}

$idInt = (int)$idUtilizador;
$stmt->bind_param('isssss', $idInt, $nome, $telemovel, $tipo, $email, $dataNascimento);

if ($stmt->execute()) {
    $response['success'] = true;
    $response['message'] = 'Utilizador atualizado.';
} else {
    $response['message'] = 'Erro a executar SP: ' . $stmt->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
