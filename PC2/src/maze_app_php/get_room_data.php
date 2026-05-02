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
    $response['message'] = "Erro de conexão MySQL: " . $conn->connect_error;
    echo json_encode($response); exit;
}

// Filtra ocupações da simulação corrente da equipa, e dentro dela
// pega no estado mais recente de cada sala (último DataCriacao por sala)
$sql = "SELECT IDSala AS Sala,
               NumeroMarsamisEven,
               NumeroMarsamisOdd
        FROM ocupacaolabirinto o
        WHERE o.IDSimulacao = (
                SELECT MAX(IDSimulacao) FROM simulacao WHERE IDEquipa = ?
            )
          AND o.DataCriacao = (
                SELECT MAX(DataCriacao)
                FROM ocupacaolabirinto o2
                WHERE o2.IDSala = o.IDSala
                  AND o2.IDSimulacao = o.IDSimulacao
            )
        ORDER BY IDSala";
$stmt = $conn->prepare($sql);
$idGrupoInt = (int)$idGrupo;
$stmt->bind_param('i', $idGrupoInt);
$stmt->execute();
$result = $stmt->get_result();

if ($result) {
    $rooms = array();
    while ($row = $result->fetch_assoc()) {
        $rooms[] = $row;
    }
    $response['success'] = true;
    $response['data'] = $rooms;
    $response['message'] = 'Dados dos corredores carregados com sucesso.';
} else {
    $response['message'] = 'Erro ao executar consulta: ' . $conn->error;
}

$stmt->close();
$conn->close();
echo json_encode($response);
?>