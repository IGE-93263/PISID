<?php
// Não cuspir HTML em caso de erro — sempre JSON limpo.
ini_set('display_errors', 0);
error_reporting(0);
mysqli_report(MYSQLI_REPORT_OFF);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '');

$username = $_REQUEST['username'] ?? '';
$password = $_REQUEST['password'] ?? '';
$database = $_REQUEST['database'] ?? '';

$equipa         = $_REQUEST['equipa']         ?? '';
$nome           = $_REQUEST['nome']           ?? '';
$telemovel      = $_REQUEST['telemovel']      ?? '';
$tipo           = $_REQUEST['tipo']           ?? '';
$email          = $_REQUEST['email']          ?? '';
$dataNascimento = $_REQUEST['dataNascimento'] ?? '';

if ($username === '' || $password === '' || $database === '') {
    $response['message'] = 'Credenciais (username/password/database) em falta.';
    echo json_encode($response); exit;
}
if ($equipa === '' || $nome === '' || $email === '') {
    $response['message'] = 'Equipa, nome e email são obrigatórios.';
    echo json_encode($response); exit;
}

// Dispatch pelo Tipo do utilizador AUTENTICADO (vem em caller_tipo).
// O campo 'tipo' é o Tipo do utilizador que está a ser CRIADO.
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

$stmt = $conn->prepare('CALL Criar_utilizador(?, ?, ?, ?, ?, ?)');
if (!$stmt) {
    $response['message'] = 'Erro a preparar CALL: ' . $conn->error;
    $conn->close(); echo json_encode($response); exit;
}

$equipaInt = (int)$equipa;
$stmt->bind_param('isssss', $equipaInt, $nome, $telemovel, $tipo, $email, $dataNascimento);

if ($stmt->execute()) {
    $response['success'] = true;
    $response['message'] = 'Utilizador criado.';
} else {
    $response['message'] = 'Erro a executar SP: ' . $stmt->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
