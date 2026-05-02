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

// SELECT-only → user_app
$conn = new mysqli('mysql', 'user_app', 'user_pw', $database);
if ($conn->connect_error) {
    $response['message'] = "Erro de conexão: " . $conn->connect_error;
    echo json_encode($response); exit;
}

// Filtro pela simulação corrente da equipa
$sql = "SELECT temperatura, idtemperatura
        FROM temperatura
        WHERE IDSimulacao = (
            SELECT MAX(IDSimulacao) FROM simulacao WHERE IDEquipa = ?
        )
        ORDER BY idtemperatura ASC";
$stmt = $conn->prepare($sql);
$idGrupoInt = (int)$idGrupo;
$stmt->bind_param('i', $idGrupoInt);
$stmt->execute();
$result = $stmt->get_result();

if ($result) {
    $tempData = array();
    while ($row = $result->fetch_assoc()) {
        $tempData[] = $row;
    }
    $response['success'] = true;
    $response['data'] = $tempData;
    $response['message'] = 'Dados de temperatura carregados com sucesso.';
} else {
    $response['message'] = "Erro na query: " . $conn->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
?>