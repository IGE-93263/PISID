<?php
// api_procedures.php
header('Content-Type: application/json');
require 'db.php';

$data = json_decode(file_get_contents("php://input"), true);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $sql = $data['sql_code'];

    // Em PHP não podemos usar os comandos "DELIMITER $$".
    // O código enviado pelo Frontend já não deve conter esses delimitadores.

    try {
        // multi_query permite executar o DROP e depois o CREATE na mesma chamada
        if ($mysqli->multi_query($sql)) {
            // Limpar os resultados pendentes da multi_query para evitar erros subsequentes
            do {
                if ($res = $mysqli->store_result()) {
                    $res->free();
                }
            } while ($mysqli->more_results() && $mysqli->next_result());

            echo json_encode(["sucesso" => "Stored Procedure atualizada com sucesso na Base de Dados!"]);
        } else {
            throw new Exception($mysqli->error);
        }
    } catch (Exception $e) {
        echo json_encode(["erro" => "Erro de sintaxe SQL: " . $e->getMessage()]);
    }
}
$mysqli->close();
?>