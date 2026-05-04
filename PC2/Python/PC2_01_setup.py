"""
pc2_setup.py — Setup inicial antes de arrancar o PC2_01.

Lê a BD cloud do professor (maze @ 194.210.86.10) e:
  1. Popula a tabela corridor local com os corredores reais do labirinto
  2. Actualiza configtemp e configsound com os limites reais do SetupMaze
  3. Cria a tabela pontuacoes (histórico de Scores odd/even)

Corre UMA VEZ antes do PC2_01_mqtt_to_mysql.py.
"""

import sys
import mysql.connector

# ── BD Cloud do Professor ─────────────────────────────────────────────────────
CLOUD_CONFIG = {
    "host":     "194.210.86.10",
    "user":     "aluno",
    "password": "aluno",
    "database": "maze",
    "connection_timeout": 10,
}

# ── BD Local ──────────────────────────────────────────────────────────────────
LOCAL_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "root",
    "database": "labirinto",
}

# ─────────────────────────────────────────────────────────────────────────────

def ler_cloud():
    """Lê os corredores e limites de temperatura/som da BD cloud."""
    print("[Cloud] A ligar a 194.210.86.10 / maze ...", flush=True)
    try:
        conn = mysql.connector.connect(**CLOUD_CONFIG)
    except mysql.connector.Error as e:
        print(f"[ERRO] Não foi possível ligar à BD cloud: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # Corredores
    cur.execute("SELECT RoomA, RoomB FROM Corridor")
    corredores = cur.fetchall()
    print(f"[Cloud] {len(corredores)} corredores lidos.", flush=True)

    # SetupMaze — limites de temperatura e som
    cur.execute("""
        SELECT normaltemperature, temperaturevarhightoleration,
               normalnoise, noisevartoleration
        FROM SetupMaze
        LIMIT 1
    """)
    row = cur.fetchone()
    if row:
        temp_normal, temp_var_high, noise_normal, noise_var = row
        temp_max  = float(temp_normal) + float(temp_var_high)
        temp_min  = float(temp_normal)   # temperatura base como mínimo
        sound_max = float(noise_normal) + float(noise_var)
        print(f"[Cloud] SetupMaze: temp_max={temp_max} | sound_max={sound_max}", flush=True)
    else:
        print("[Cloud] SetupMaze sem dados — a usar defaults.", flush=True)
        temp_max, temp_min, sound_max = 60.0, 0.0, 36.0

    cur.close()
    conn.close()
    return corredores, temp_max, temp_min, sound_max


def aplicar_local(corredores, temp_max, temp_min, sound_max):
    """Aplica os dados lidos na BD local."""
    print("[Local] A ligar a localhost / labirinto ...", flush=True)
    conn = mysql.connector.connect(**LOCAL_CONFIG)
    cur  = conn.cursor()

    # ── 1. Criar tabela corridor se não existir ──────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corridor (
            IDSala1 INTEGER NOT NULL,
            IDSala2 INTEGER NOT NULL,
            PRIMARY KEY (IDSala1, IDSala2)
        )
    """)
    conn.commit()

    # ── 2. Limpar e popular corridor ─────────────────────────────────────────
    cur.execute("DELETE FROM corridor")
    inseridos = 0
    for room_a, room_b in corredores:
        cur.execute(
            "INSERT IGNORE INTO corridor (IDSala1, IDSala2) VALUES (%s, %s)",
            (room_a, room_b)
        )
        inseridos += cur.rowcount
    conn.commit()
    print(f"[Local] corridor: {inseridos} corredores inseridos.", flush=True)

    # ── 3. Actualizar configtemp ──────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM configtemp")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO configtemp (IDconfigtemp, minimo, maximo) VALUES (1, %s, %s)",
            (str(temp_min), str(temp_max))
        )
    else:
        cur.execute(
            "UPDATE configtemp SET minimo=%s, maximo=%s WHERE IDconfigtemp=1",
            (str(temp_min), str(temp_max))
        )
    conn.commit()
    print(f"[Local] configtemp actualizado: min={temp_min} max={temp_max}", flush=True)

    # ── 4. Actualizar configsound ─────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM configsound")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO configsound (IDconfigsound, maximo) VALUES (1, %s)",
            (str(sound_max),)
        )
    else:
        cur.execute(
            "UPDATE configsound SET maximo=%s WHERE IDconfigsound=1",
            (str(sound_max),)
        )
    conn.commit()
    print(f"[Local] configsound actualizado: max={sound_max}", flush=True)

    # ── 5. Criar tabela pontuacoes ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pontuacoes (
            IDPontuacao  INT NOT NULL AUTO_INCREMENT,
            IDSimulacao  INT NOT NULL,
            IDSala       INT NOT NULL,
            Hora         DATETIME(6) NOT NULL DEFAULT NOW(6),
            PRIMARY KEY (IDPontuacao),
            CONSTRAINT fk_pont_sim FOREIGN KEY (IDSimulacao) REFERENCES simulacao(IDSimulacao),
            CONSTRAINT fk_pont_sala FOREIGN KEY (IDSala) REFERENCES sala(IDSala)
        )
    """)
    conn.commit()
    print("[Local] Tabela pontuacoes pronta.", flush=True)

    cur.close()
    conn.close()


def main():
    print("=" * 55)
    print(" PC2 Setup — Grupo 32")
    print("=" * 55)

    corredores, temp_max, temp_min, sound_max = ler_cloud()
    aplicar_local(corredores, temp_max, temp_min, sound_max)

    print()
    print("=" * 55)
    print(" Setup concluído. Pode agora arrancar o PC2_02.")
    print("=" * 55)


if __name__ == "__main__":
    main()
