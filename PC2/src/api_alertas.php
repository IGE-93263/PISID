<?php
// api_alertas.php
header('Content-Type: application/json');
require 'db.php';

try {
    $res = $mysqli->query("SELECT Hora, IDSala, TipoAlerta, Msg, Leitura FROM mensagens ORDER BY Hora DESC LIMIT 50");
    echo json_encode($res->fetch_all(MYSQLI_ASSOC));
} catch (Exception $e) {
    echo json_encode(["erro" => "Erro nos alertas: " . $e->getMessage()]);
}
$mysqli->close();
?>