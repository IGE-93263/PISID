"""
PC2 — MQTT → MySQL (Grupo 32)
==============================
Subscreve os tópicos de migração publicados pelo PC1
e insere os dados nas tabelas MySQL.

Tópicos subscritos:
  pisid_mig_mov_32   — insere em medicoespassagens
  pisid_mig_temp_32  — insere em temperatura
  pisid_mig_sound_32 — insere em som

Uso: python mqtt_to_mysql.py [grupo]
"""

import json
import sys
import time
from datetime import datetime

import mysql.connector
import paho.mqtt.client as mqtt

try:
    from atuadores import Atuadores
    _TEM_ATUADORES = True
except ImportError:
    _TEM_ATUADORES = False

try:
    from gatilho_odd_even import GatilhoOddEven
    _TEM_GATILHO = True
except ImportError:
    _TEM_GATILHO = False

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

GRUPO        = 32
BROKER       = "broker.emqx.io"
PORT         = 1883
QOS          = 1
ID_SIMULACAO   = 1    # FK para a tabela simulacao
NUM_MARSAMIS   = 30   # total de marsamis por simulação (ver SetupMaze)

MYSQL_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "root",
    "database": "labirinto",
}

# ─── ESTADO GLOBAL ────────────────────────────────────────────────────────────

_conn_mysql = None
_total    = {"movimento": 0, "temperatura": 0, "som": 0}
_atuadores = None
_gatilho   = None

# Estado em memória do labirinto: {marsami_id: sala_atual}
# Necessário para validar se o marsami estava na sala de origem
_estado_labirinto: dict[int, int] = {}
_marsamis_cansados: set[int] = set()   # IDs dos marsamis com Status=2
_simulacao_terminada = False            # flag para guardar resultado só uma vez

# ─── LIGAÇÃO MYSQL ────────────────────────────────────────────────────────────

def _get_mysql():
    global _conn_mysql
    if _conn_mysql and _conn_mysql.is_connected():
        return _conn_mysql
    try:
        _conn_mysql = mysql.connector.connect(**MYSQL_CONFIG)
        print("[MySQL] Ligado.", flush=True)
        return _conn_mysql
    except mysql.connector.Error as e:
        print(f"[MySQL] Erro na ligação: {e}", flush=True)
        raise

# ─── INSERÇÃO ─────────────────────────────────────────────────────────────────

def _corredor_existe(cursor, origem: int, destino: int) -> bool:
    """
    Fase APRENDIZAGEM: insere o corredor automaticamente se for novo.
    Fase VALIDAÇÃO:    só aceita corredores já conhecidos.

    A transição acontece após CORRIDOR_MIN_MOVES corredores distintos vistos.
    Ao arrancar o script, a tabela é limpa — mapa fresh por simulação.
    """
    global _modo_aprendizagem, _corridors_vistos
    par = (origem, destino)

    try:
        if _modo_aprendizagem:
            if par not in _corridors_vistos:
                cursor.execute(
                    "INSERT IGNORE INTO corridor (IDSala1, IDSala2) VALUES (%s, %s)",
                    (origem, destino)
                )
                cursor.connection.commit()
                _corridors_vistos.add(par)
                print(f"[Corridor] Aprendido: {origem}→{destino} "
                      f"({len(_corridors_vistos)}/{CORRIDOR_MIN_MOVES})", flush=True)

                if len(_corridors_vistos) >= CORRIDOR_MIN_MOVES:
                    _modo_aprendizagem = False
                    print(f"[Corridor] Mapa aprendido ({len(_corridors_vistos)} corredores)"
                          f" — modo validação ativo.", flush=True)
            return True   # na aprendizagem, aceita sempre

        # Modo validação — verifica na BD
        cursor.execute(
            "SELECT 1 FROM corridor WHERE IDSala1=%s AND IDSala2=%s LIMIT 1",
            (origem, destino)
        )
        return cursor.fetchone() is not None

    except mysql.connector.Error:
        return True   # Se tabela não existir, não bloqueia

def _inserir_movimento(data: dict):
    """
    Insere movimento em medicoespassagens.
    Regras:
      - RoomOrigin=0, RoomDestiny=0 → marsami cansado/preso (ignora)
      - RoomOrigin=0, RoomDestiny>0 → largada inicial (insere sempre)
      - Caso geral                  → insere diretamente
    Odd/even tracker chamado após cada inserção válida.
    """
    try:
        marsami = int(data.get("Marsami", 0))
        origem  = int(data.get("RoomOrigin",  0))
        destino = int(data.get("RoomDestiny", 0))
        status  = data.get("Status")
        hora    = data.get("Hora")
    except (TypeError, ValueError) as e:
        print(f"[Anomalia mov] campos inválidos: {e}", flush=True)
        return

    # Marsami cansado/preso — não se move
    if origem == 0 and destino == 0:
        print(f"[Mov] Marsami {marsami} cansado/preso — ignorado", flush=True)
        _marsamis_cansados.add(marsami)
        if len(_marsamis_cansados) >= NUM_MARSAMIS and not _simulacao_terminada:
            print(f"[Sim] Todos os {NUM_MARSAMIS} marsamis cansados!", flush=True)
            _guardar_resultado_final()
        return

    conn   = _get_mysql()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO medicoespassagens
               (IDSimulacao, IDSalaOrigem, IDSalaDestino, Hora, Marsami, Status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (ID_SIMULACAO, origem, destino, hora, marsami, status),
        )
        conn.commit()
        _total["movimento"] += 1
        label = "largada" if origem == 0 else f"sala {origem}→{destino}"
        print(f"[MySQL ✓] Movimento #{_total['movimento']} | Marsami {marsami}: {label}", flush=True)

        # Odd/even tracker
        if _gatilho:
            try:
                _gatilho.processar_movimento(data)
            except Exception:
                pass

    except mysql.connector.Error as e:
        print(f"[MySQL ✗] Movimento: {e}", flush=True)
        conn.rollback()
    finally:
        cursor.close()

def _inserir_temperatura(data: dict):
    conn   = _get_mysql()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO temperatura (IDSimulacao, Hora, Temperatura) VALUES (%s, %s, %s)",
            (ID_SIMULACAO, data.get("Hour"), str(data.get("Temperature"))),
        )
        conn.commit()
        _total["temperatura"] += 1
        print(f"[MySQL ✓] Temperatura #{_total['temperatura']} | "
              f"{data.get('Temperature')}ºC", flush=True)
        # Atuador: AC automático
        if _atuadores:
            try:
                _atuadores.processar_temperatura(
                    sala=int(data.get("Room", 0)),
                    valor=float(data.get("Temperature", 0))
                )
            except Exception:
                pass
    except mysql.connector.Error as e:
        print(f"[MySQL ✗] Temperatura: {e}", flush=True)
        conn.rollback()
    finally:
        cursor.close()

def _inserir_som(data: dict):
    conn   = _get_mysql()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO som (IDSimulacao, Hora, Som) VALUES (%s, %s, %s)",
            (ID_SIMULACAO, data.get("Hour"), str(data.get("Sound"))),
        )
        conn.commit()
        _total["som"] += 1
        print(f"[MySQL ✓] Som #{_total['som']} | {data.get('Sound')}dB", flush=True)
        # Atuador: fechar corredor se som alto
        if _atuadores:
            try:
                raw_origem  = data.get("RoomOrigin")
                sala_origem = int(raw_origem) if raw_origem is not None else None
                _atuadores.processar_som(
                    sala=int(data.get("Room", 0)),
                    valor=float(data.get("Sound", 0)),
                    sala_origem=sala_origem
                )
            except Exception:
                pass
    except mysql.connector.Error as e:
        print(f"[MySQL ✗] Som: {e}", flush=True)
        conn.rollback()
    finally:
        cursor.close()


def _guardar_resultado_final():
    """
    Chamado quando todos os marsamis estão cansados (fim de simulação).
    Guarda o snapshot de ocupacaolabirinto em resultados_finais.
    Pontuação tipo a) do enunciado — contagem final por sala.
    """
    global _simulacao_terminada
    if _simulacao_terminada:
        return
    _simulacao_terminada = True

    print("\n" + "=" * 55, flush=True)
    print(" FIM DE SIMULAÇÃO — A guardar resultado final...", flush=True)
    print("=" * 55, flush=True)

    conn   = _get_mysql()
    cursor = conn.cursor()
    try:
        # Cria tabela se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resultados_finais (
                IDResultado        INT NOT NULL AUTO_INCREMENT,
                IDSimulacao        INT NOT NULL,
                IDSala             INT NOT NULL,
                NumMarsamisOdd     INT NOT NULL DEFAULT 0,
                NumMarsamisEven    INT NOT NULL DEFAULT 0,
                TotalMarsamis      INT NOT NULL DEFAULT 0,
                DataFim            DATETIME(6) NOT NULL DEFAULT NOW(6),
                PRIMARY KEY (IDResultado)
            )
        """)
        conn.commit()

        # Lê a ocupação actual por sala (último registo de cada sala)
        cursor.execute("""
            SELECT o.IDSala, o.NumeroMarsamisOdd, o.NumeroMarsamisEven
            FROM ocupacaolabirinto o
            INNER JOIN (
                SELECT IDSala, MAX(DataCriacao) AS ultima
                FROM ocupacaolabirinto
                WHERE IDSimulacao = %s
                GROUP BY IDSala
            ) ult ON o.IDSala = ult.IDSala AND o.DataCriacao = ult.ultima
            WHERE o.IDSimulacao = %s
            ORDER BY o.IDSala
        """, (ID_SIMULACAO, ID_SIMULACAO))
        salas = cursor.fetchall()

        total_salas = 0
        for sala_id, odd, even in salas:
            total = (odd or 0) + (even or 0)
            cursor.execute("""
                INSERT INTO resultados_finais
                    (IDSimulacao, IDSala, NumMarsamisOdd, NumMarsamisEven, TotalMarsamis, DataFim)
                VALUES (%s, %s, %s, %s, %s, NOW(6))
            """, (ID_SIMULACAO, sala_id, odd or 0, even or 0, total))
            total_salas += total
            print(f"  Sala {sala_id:2d}: odd={odd or 0:3d}  even={even or 0:3d}  total={total}", flush=True)

        conn.commit()
        print(f"\n  Total marsamis contabilizados: {total_salas}", flush=True)
        print(f"  Resultado guardado em 'resultados_finais'.", flush=True)
        print("=" * 55 + "\n", flush=True)

    except mysql.connector.Error as e:
        print(f"[ERRO] Ao guardar resultado final: {e}", flush=True)
        conn.rollback()
    finally:
        cursor.close()


# ─── CALLBACKS MQTT ───────────────────────────────────────────────────────────

def on_connect(c, userdata, flags, reason_code, properties=None):
    grupo = userdata["grupo"]
    if reason_code == 0:
        topics = [
            (f"pisid_mig_mov_{grupo}",   QOS),
            (f"pisid_mig_temp_{grupo}",  QOS),
            (f"pisid_mig_sound_{grupo}", QOS),
        ]
        c.subscribe(topics)
        print(f"[MQTT] Ligado a {BROKER}", flush=True)
        print(f"[MQTT] Subscrito a: {[t for t,_ in topics]}", flush=True)
    else:
        print(f"[MQTT] Falha na ligação (rc={reason_code})", flush=True)

def on_disconnect(c, userdata, disconnect_flags, reason_code, properties=None):
    if reason_code != 0:
        print(f"[MQTT] Desconectado (rc={reason_code}) — reconexão automática...", flush=True)

def on_message(c, userdata, msg):
    topic = msg.topic
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[MQTT] Payload inválido em {topic}: {e}", flush=True)
        return

    try:
        if "mig_mov"   in topic:
            _inserir_movimento(data)
        elif "mig_temp" in topic:
            _inserir_temperatura(data)
        elif "mig_sound" in topic:
            _inserir_som(data)
    except Exception as e:
        print(f"[Erro] {topic}: {e}", flush=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    grupo = int(sys.argv[1]) if len(sys.argv) > 1 else GRUPO

    print("=" * 55, flush=True)
    print(f" PC2 — MQTT → MySQL  (Grupo {grupo})", flush=True)
    print(f" Broker: {BROKER}", flush=True)
    print(f" MySQL: {MYSQL_CONFIG['host']} / {MYSQL_CONFIG['database']}", flush=True)
    print(f" IDSimulacao: {ID_SIMULACAO}", flush=True)
    print("=" * 55, flush=True)

    # Verificar MySQL antes de começar
    try:
        _get_mysql()
    except mysql.connector.Error:
        print("[ERRO] Não foi possível ligar ao MySQL. Verifica as credenciais.", flush=True)
        sys.exit(1)

    c = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata={"grupo": grupo},
    )
    c.on_connect    = on_connect
    c.on_disconnect = on_disconnect
    c.on_message    = on_message
    c.reconnect_delay_set(min_delay=2, max_delay=60)

    print(f"[MQTT] A ligar a {BROKER}:{PORT}...", flush=True)
    c.connect(BROKER, PORT, keepalive=60)

    # Inicializar atuadores e tracker odd/even
    global _atuadores, _gatilho
    if _TEM_ATUADORES:
        _atuadores = Atuadores(grupo=grupo, mqtt_client=c)
    else:
        print("[atuadores] módulo não encontrado — desativado", flush=True)

    if _TEM_GATILHO:
        _gatilho = GatilhoOddEven(grupo=grupo, mqtt_client=c, db_conn=_get_mysql(), id_simulacao=ID_SIMULACAO)
    else:
        print("[odd/even] módulo não encontrado — desativado", flush=True)

    try:
        c.loop_forever()
    except KeyboardInterrupt:
        print("\n[Ctrl+C] A encerrar...", flush=True)
    finally:
        c.disconnect()
        if _conn_mysql and _conn_mysql.is_connected():
            _conn_mysql.close()
        print(f"Total inserido — Movimento:{_total['movimento']} "
              f"Temp:{_total['temperatura']} Som:{_total['som']}", flush=True)

if __name__ == "__main__":
    main()
