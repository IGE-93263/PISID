-- Dados mínimos para a migração funcionar (FKs)
-- Executar DEPOIS de labirinto.sql
-- Grupo 19 = Player 19 no mazerun

USE labirinto;

INSERT IGNORE INTO equipa (IDEquipa, NomeEquipa) VALUES (19, 'Grupo 19');

INSERT IGNORE INTO sala (IDSala) VALUES 
  (0),(1),(2),(3),(4),(5),(6),(7),(8),(9),(10);

INSERT IGNORE INTO utilizador (IDUtilizador, Equipa, Nome) 
  VALUES (1, 19, 'Jogador');

INSERT IGNORE INTO simulacao (IDSimulacao, IDEquipa, IDUtilizador, Descricao, DataHoraInicio) 
  VALUES (1, 19, 1, 'Migração Mongo', NOW());
