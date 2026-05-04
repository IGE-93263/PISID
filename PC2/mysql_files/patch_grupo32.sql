-- ============================================================
-- PATCH SQL — Grupo 32
-- Adiciona o que falta SEM apagar tabelas nem dados existentes.
-- Correr no phpMyAdmin: seleciona BD labirinto → SQL → colar → Executar
-- ============================================================

USE labirinto;

-- ── 1. TABELAS EM FALTA ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS configtemp (
   IDconfigtemp INT NOT NULL,
   maximo VARCHAR(50) NULL,
   minimo VARCHAR(50) NULL,
   CONSTRAINT PK_configtemp PRIMARY KEY (IDconfigtemp)
);

CREATE TABLE IF NOT EXISTS configsound (
   IDconfigsound INT NOT NULL,
   maximo VARCHAR(50) NULL,
   CONSTRAINT PK_configsound PRIMARY KEY (IDconfigsound)
);

-- ── 2. SEED — dados iniciais ─────────────────────────────────

-- Equipa 32
INSERT IGNORE INTO equipa (IDEquipa, NomeEquipa) VALUES (32, 'Grupo 32');

-- Salas do labirinto (0 a 10)
INSERT IGNORE INTO sala (IDSala) VALUES
  (0),(1),(2),(3),(4),(5),(6),(7),(8),(9),(10);

-- Utilizadores da app (para Android/Web)
INSERT IGNORE INTO utilizador (IDUtilizador, Equipa, Nome, Tipo, Email)
  VALUES (99, 32, 'Admin', 'Administrador', 'admin@iscte-ul.pt');

INSERT IGNORE INTO utilizador (IDUtilizador, Equipa, Nome, Tipo, Email)
  VALUES (1, 32, 'Jogador', 'Aluno', 'jogador@iscte-ul.pt');

-- Simulação inicial (IDSimulacao=1 é o FK usado nos scripts Python)
INSERT IGNORE INTO simulacao (IDSimulacao, IDEquipa, IDUtilizador, Descricao, DataHoraInicio)
  VALUES (1, 32, 1, 'Simulacao Grupo 32', NOW());

-- Limites dos sensores (usados pelos triggers de alerta)
INSERT IGNORE INTO configtemp  (IDconfigtemp, minimo, maximo) VALUES (1, '0', '60');
INSERT IGNORE INTO configsound (IDconfigsound, maximo)        VALUES (1, '36');

-- ── 3. STORED PROCEDURES ─────────────────────────────────────

DROP PROCEDURE IF EXISTS Criar_utilizador;
DROP PROCEDURE IF EXISTS Alterar_utilizador;
DROP PROCEDURE IF EXISTS Remover_utilizador;
DROP PROCEDURE IF EXISTS Criar_jogo;
DROP PROCEDURE IF EXISTS Alterar_jogo;

DELIMITER $$

CREATE PROCEDURE Criar_utilizador (
   IN p_Equipa INT, IN p_Nome VARCHAR(100), IN p_Telemovel VARCHAR(20),
   IN p_Tipo VARCHAR(50), IN p_Email VARCHAR(120), IN p_DataNascimento DATE
)
BEGIN
   DECLARE novo_id INT;
   SELECT IFNULL(MAX(IDUtilizador),0)+1 INTO novo_id FROM utilizador;
   INSERT INTO utilizador (IDUtilizador, Equipa, Nome, Telemovel, Tipo, Email, DataNascimento)
   VALUES (novo_id, p_Equipa, p_Nome, p_Telemovel, p_Tipo, p_Email, p_DataNascimento);
END$$

CREATE PROCEDURE Alterar_utilizador (
   IN p_IDUtilizador INT, IN p_Nome VARCHAR(100), IN p_Telemovel VARCHAR(20),
   IN p_Tipo VARCHAR(50), IN p_Email VARCHAR(120), IN p_DataNascimento DATE
)
BEGIN
   UPDATE utilizador
      SET Nome=p_Nome, Telemovel=p_Telemovel, Tipo=p_Tipo,
          Email=p_Email, DataNascimento=p_DataNascimento
    WHERE IDUtilizador = p_IDUtilizador;
END$$

CREATE PROCEDURE Remover_utilizador (IN p_IDUtilizador INT)
BEGIN
   DELETE FROM simulacao  WHERE IDUtilizador = p_IDUtilizador;
   DELETE FROM utilizador WHERE IDUtilizador = p_IDUtilizador;
END$$

CREATE PROCEDURE Criar_jogo (
   IN p_IDEquipa INT, IN p_IDUtilizador INT,
   IN p_Descricao TEXT, IN p_DataHoraInicio DATETIME
)
BEGIN
   DECLARE novo_id INT;
   SELECT IFNULL(MAX(IDSimulacao),0)+1 INTO novo_id FROM simulacao;
   INSERT INTO simulacao (IDSimulacao, IDEquipa, IDUtilizador, Descricao, DataHoraInicio)
   VALUES (novo_id, p_IDEquipa, p_IDUtilizador, p_Descricao, p_DataHoraInicio);
END$$

CREATE PROCEDURE Alterar_jogo (IN p_IDSimulacao INT, IN p_Descricao TEXT)
BEGIN
   UPDATE simulacao SET Descricao = p_Descricao WHERE IDSimulacao = p_IDSimulacao;
END$$

DELIMITER ;

-- ── 4. TRIGGERS ──────────────────────────────────────────────
-- ─────────────────────────────────────────────────────────────────────────────
-- TRIGGER 1: Alertas_Temp_Som
-- Tabela: mensagens | BEFORE INSERT
-- Antes de inserir em mensagens, verifica se é uma leitura de temp ou som
-- que ultrapassa o limiar de configtemp/configsound.
-- Se sim, e se não existir já alerta ativo do mesmo tipo, marca como alerta.
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS Alertas_Temp_Som;
DELIMITER $$
CREATE TRIGGER Alertas_Temp_Som
BEFORE INSERT ON mensagens
FOR EACH ROW
BEGIN
    DECLARE v_max_temp  DECIMAL(10,2) DEFAULT 60.0;
    DECLARE v_max_sound DECIMAL(10,2) DEFAULT 36.0;
    DECLARE v_existe    INT DEFAULT 0;

    -- Ler limites das tabelas de configuração
    SELECT CAST(maximo AS DECIMAL(10,2)) INTO v_max_temp
      FROM configtemp LIMIT 1;
    SELECT CAST(maximo AS DECIMAL(10,2)) INTO v_max_sound
      FROM configsound LIMIT 1;

    -- Temperatura acima do limite
    IF NEW.Sensor = 'Temperatura' AND NEW.Leitura > v_max_temp THEN
        SELECT COUNT(*) INTO v_existe
          FROM mensagens
         WHERE IDSimulacao = NEW.IDSimulacao
           AND Sensor = 'Temperatura'
           AND TipoAlerta = 'TEMP_ALTA';
        IF v_existe = 0 THEN
            SET NEW.TipoAlerta = 'TEMP_ALTA';
            SET NEW.Msg = CONCAT('Temperatura acima do limite (', v_max_temp, '): ', NEW.Leitura);
        END IF;
    END IF;

    -- Som acima do limite
    IF NEW.Sensor = 'Som' AND NEW.Leitura > v_max_sound THEN
        SELECT COUNT(*) INTO v_existe
          FROM mensagens
         WHERE IDSimulacao = NEW.IDSimulacao
           AND Sensor = 'Som'
           AND TipoAlerta = 'SOM_ALTO';
        IF v_existe = 0 THEN
            SET NEW.TipoAlerta = 'SOM_ALTO';
            SET NEW.Msg = CONCAT('Som acima do limite (', v_max_sound, '): ', NEW.Leitura);
        END IF;
    END IF;
END$$
DELIMITER ;


-- ─────────────────────────────────────────────────────────────────────────────
-- TRIGGER 2: Alerta_Cansados
-- Tabela: medicoespassagens | AFTER INSERT
-- Quando um marsami chega com Status=2 (cansado), cria alerta em mensagens.
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS Alerta_Cansados;
DELIMITER $$
CREATE TRIGGER Alerta_Cansados
AFTER INSERT ON medicoespassagens
FOR EACH ROW
BEGIN
    IF NEW.Status = 2 THEN
        INSERT INTO mensagens
            (IDSimulacao, IDSala, Sensor, Leitura, TipoAlerta, Msg, HoraEscrita, Hora)
        VALUES
            (NEW.IDSimulacao,
             NEW.IDSalaDestino,
             'Movimento',
             NEW.Marsami,
             'MARSAMI_CANSADO',
             CONCAT('Marsami ', NEW.Marsami, ' cansado na sala ', NEW.IDSalaDestino),
             NOW(),
             NEW.Hora);
    END IF;
END$$
DELIMITER ;


-- ─────────────────────────────────────────────────────────────────────────────
-- TRIGGER 3: Conversao_Mensagem
-- Tabela: mensagens | AFTER INSERT
-- Ao inserir uma mensagem de leitura de sensor, regista automaticamente
-- o valor na tabela Temperatura ou Som conforme o tipo.
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS Conversao_Mensagem;
DELIMITER $$
CREATE TRIGGER Conversao_Mensagem
AFTER INSERT ON mensagens
FOR EACH ROW
BEGIN
    IF NEW.Sensor = 'Temperatura' AND NEW.Leitura IS NOT NULL THEN
        INSERT INTO temperatura (IDSimulacao, Hora, Temperatura)
        VALUES (NEW.IDSimulacao, IFNULL(NEW.Hora, NOW()), NEW.Leitura);
    ELSEIF NEW.Sensor = 'Som' AND NEW.Leitura IS NOT NULL THEN
        INSERT INTO som (IDSimulacao, Hora, Som)
        VALUES (NEW.IDSimulacao, IFNULL(NEW.Hora, NOW()), NEW.Leitura);
    END IF;
END$$
DELIMITER ;


-- ─────────────────────────────────────────────────────────────────────────────
-- TRIGGER 4: Atualizar_Ocupacao_Labirinto
-- Tabela: medicoespassagens | AFTER INSERT
-- Cada vez que é inserida uma medição de passagem, atualiza a contagem
-- de marsamis odd e even nas salas afetadas (origem e destino).
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS Atualizar_Ocupacao_Labirinto;
DELIMITER $$
CREATE TRIGGER Atualizar_Ocupacao_Labirinto
AFTER INSERT ON medicoespassagens
FOR EACH ROW
BEGIN
    -- Atualiza sala de DESTINO: adiciona marsami
    INSERT INTO ocupacaolabirinto (IDSimulacao, IDSala, DataCriacao, NumeroMarsamisEven, NumeroMarsamisOdd)
    SELECT
        NEW.IDSimulacao,
        NEW.IDSalaDestino,
        NOW(),
        SUM(CASE WHEN m.Marsami % 2 = 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN m.Marsami % 2 != 0 THEN 1 ELSE 0 END)
    FROM (
        -- Marsamis que chegaram ao destino (incluindo o novo)
        SELECT Marsami FROM medicoespassagens
         WHERE IDSimulacao = NEW.IDSimulacao
           AND IDSalaDestino = NEW.IDSalaDestino
           AND IDMedicao <= NEW.IDMedicao
        -- Menos os que saíram desta sala
        UNION ALL
        SELECT -Marsami FROM medicoespassagens
         WHERE IDSimulacao = NEW.IDSimulacao
           AND IDSalaOrigem = NEW.IDSalaDestino
           AND IDMedicao <= NEW.IDMedicao
           AND IDSalaOrigem > 0
    ) base
    -- Conta só os que ainda estão (chegaram mais vezes do que saíram)
    GROUP BY 1
    HAVING COUNT(*) > 0;

    -- Atualiza sala de ORIGEM: remove marsami (só se não for largada inicial)
    IF NEW.IDSalaOrigem > 0 THEN
        INSERT INTO ocupacaolabirinto (IDSimulacao, IDSala, DataCriacao, NumeroMarsamisEven, NumeroMarsamisOdd)
        SELECT
            NEW.IDSimulacao,
            NEW.IDSalaOrigem,
            NOW(),
            SUM(CASE WHEN m2.Marsami % 2 = 0 THEN 1 ELSE 0 END),
            SUM(CASE WHEN m2.Marsami % 2 != 0 THEN 1 ELSE 0 END)
        FROM medicoespassagens m2
        WHERE m2.IDSimulacao = NEW.IDSimulacao
          AND m2.IDSalaDestino = NEW.IDSalaOrigem
          AND m2.IDMedicao < NEW.IDMedicao
          AND m2.Marsami NOT IN (
              SELECT Marsami FROM medicoespassagens
               WHERE IDSimulacao = NEW.IDSimulacao
                 AND IDSalaOrigem = NEW.IDSalaOrigem
                 AND IDMedicao <= NEW.IDMedicao
                 AND IDSalaOrigem > 0
          );
    END IF;
END$$
DELIMITER ;



-- ── 5. UTILIZADORES MYSQL ────────────────────────────────────

DROP USER IF EXISTS 'admin_app'@'%';
DROP USER IF EXISTS 'user_app'@'%';

CREATE USER 'admin_app'@'%' IDENTIFIED BY 'admin_pw';
CREATE USER 'user_app'@'%'  IDENTIFIED BY 'user_pw';

-- admin_app: leitura + escrita + SPs
GRANT SELECT, INSERT, UPDATE, DELETE ON labirinto.utilizador      TO 'admin_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON labirinto.equipa          TO 'admin_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON labirinto.simulacao       TO 'admin_app'@'%';
GRANT SELECT ON labirinto.sala                TO 'admin_app'@'%';
GRANT SELECT ON labirinto.ocupacaolabirinto   TO 'admin_app'@'%';
GRANT SELECT ON labirinto.medicoespassagens   TO 'admin_app'@'%';
GRANT SELECT ON labirinto.som                 TO 'admin_app'@'%';
GRANT SELECT ON labirinto.temperatura         TO 'admin_app'@'%';
GRANT SELECT ON labirinto.mensagens           TO 'admin_app'@'%';
GRANT SELECT ON labirinto.configtemp          TO 'admin_app'@'%';
GRANT SELECT ON labirinto.configsound         TO 'admin_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Criar_utilizador   TO 'admin_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Remover_utilizador TO 'admin_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Alterar_utilizador TO 'admin_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Criar_jogo         TO 'admin_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Alterar_jogo       TO 'admin_app'@'%';

-- user_app: só leitura + SPs permitidas
GRANT SELECT ON labirinto.utilizador          TO 'user_app'@'%';
GRANT SELECT ON labirinto.equipa              TO 'user_app'@'%';
GRANT SELECT, INSERT, UPDATE ON labirinto.simulacao TO 'user_app'@'%';
GRANT SELECT ON labirinto.sala                TO 'user_app'@'%';
GRANT SELECT ON labirinto.ocupacaolabirinto   TO 'user_app'@'%';
GRANT SELECT ON labirinto.medicoespassagens   TO 'user_app'@'%';
GRANT SELECT ON labirinto.som                 TO 'user_app'@'%';
GRANT SELECT ON labirinto.temperatura         TO 'user_app'@'%';
GRANT SELECT ON labirinto.mensagens           TO 'user_app'@'%';
GRANT SELECT ON labirinto.configtemp          TO 'user_app'@'%';
GRANT SELECT ON labirinto.configsound         TO 'user_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Alterar_utilizador TO 'user_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Criar_jogo         TO 'user_app'@'%';
GRANT EXECUTE ON PROCEDURE labirinto.Alterar_jogo       TO 'user_app'@'%';

FLUSH PRIVILEGES;


-- ── 7. TABELA CORRIDOR (passagens válidas entre salas) ──────────────────────
-- Consultada pelo PC2_01 para validar movimentos dos marsamis.
-- Preenche com o mapa real do teu labirinto (bidirecional).

CREATE TABLE IF NOT EXISTS corridor (
    IDSala1 INTEGER NOT NULL,
    IDSala2 INTEGER NOT NULL,
    PRIMARY KEY (IDSala1, IDSala2),
    CONSTRAINT fk_cor_s1 FOREIGN KEY (IDSala1) REFERENCES sala(IDSala),
    CONSTRAINT fk_cor_s2 FOREIGN KEY (IDSala2) REFERENCES sala(IDSala)
);

-- Corredores do labirinto do Grupo 32 — 10 salas (ajustar ao mapa real)
INSERT IGNORE INTO corridor (IDSala1, IDSala2) VALUES
  (1,2),(2,1),(2,3),(3,2),(3,4),(4,3),
  (4,5),(5,4),(5,6),(6,5),(6,7),(7,6),
  (7,8),(8,7),(8,9),(9,8),(9,10),(10,9),
  (1,5),(5,1),(2,6),(6,2),(3,7),(7,3),
  (4,8),(8,4),(5,9),(9,5),(6,10),(10,6);

-- ── 6. VERIFICAÇÃO ───────────────────────────────────────────
SELECT 'tabelas'     AS tipo, COUNT(*) AS total FROM information_schema.tables
  WHERE table_schema='labirinto'
UNION ALL
SELECT 'procedures', COUNT(*) FROM information_schema.routines
  WHERE routine_schema='labirinto'
UNION ALL
SELECT 'triggers',   COUNT(*) FROM information_schema.triggers
  WHERE trigger_schema='labirinto'  -- esperado: 4
UNION ALL
SELECT 'users',      COUNT(*) FROM mysql.user
  WHERE user IN ('admin_app','user_app');
