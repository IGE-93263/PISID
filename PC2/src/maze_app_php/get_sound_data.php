<?php
ini_set('display_errors', 0);
error_reporting(0);
mysqli_report(MYSQLI_REPORT_OFF);
header('Content-Type: application/json');

$response = array('success' => false, 'message' => '', 'data' => array());

$database = $_REQUEST['database'] ?? '';
$idGrupo  = $_REQUEST['idGrupo']  ?? '';

if ($database === '' || $idGrupo === '') {
    $response['message'] = 'database e idGrupo são obrigatórios.';
    echo json_encode($response); exit;
}

$conn = new mysqli('mysql', 'user_app', 'user_pw', $database);
if ($conn->connect_error) {
    $response['message'] = "Erro de conexão: " . $conn->connect_error;
    echo json_encode($response); exit;
}

$sql = "SELECT som, idsom
        FROM som
        WHERE IDSimulacao = (
            SELECT MAX(IDSimulacao) FROM simulacao WHERE IDEquipa = ?
        )
        ORDER BY idsom ASC";
$stmt = $conn->prepare($sql);
$idGrupoInt = (int)$idGrupo;
$stmt->bind_param('i', $idGrupoInt);
$stmt->execute();
$result = $stmt->get_result();

if ($result) {
    $soundData = array();
    while ($row = $result->fetch_assoc()) {
        $soundData[] = $row;
    }
    $response['success'] = true;
    $response['data'] = $soundData;
    $response['message'] = 'Dados de som carregados com sucesso.';
} else {
    $response['message'] = "Erro na query: " . $conn->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
?>