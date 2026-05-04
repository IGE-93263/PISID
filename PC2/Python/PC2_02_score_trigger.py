import time
import json
import mysql.connector
import paho.mqtt.client as mqtt

# ── Configuração ──────────────────────────────────────────
BROKER        = "broker.emqx.io"   # mesmo broker que o mazerun
PORT          = 1883
PLAYER        = 32
SIMULACAO_ID  = 1
MAX_TRIGGERS  = 3
INTERVALO     = 0.5

DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "root",
    "database": "labirinto",
}
# ─────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] Ligado a {BROKER}:{PORT}")
    else:
        print(f"[MQTT] Falha na ligação: reason_code={reason_code}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"[MQTT] Mensagem entregue (mid={mid})")

def conectar_mysql():
    return mysql.connector.connect(**DB_CONFIG)

def main():
    triggers_fired = {}   # {IDSala: count}

    # Ligação MQTT persistente (evita conflitos de client ID com publish.single)
    mqtt_client = mqtt.Client(
        client_id=f"grupo32_score_{PLAYER}",
        clean_session=True,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish  = on_publish
    mqtt_client.connect(BROKER, PORT, keepalive=60)
    mqtt_client.loop_start()

    time.sleep(1)  # aguarda ligação MQTT estabelecer

    print(f"[INFO] A monitorizar ocupacaolabirinto (IDSimulacao={SIMULACAO_ID}, Player={PLAYER})")
    print(f"[INFO] tópico destino: pisid_mazeact")
    print("-" * 60)

    conn = conectar_mysql()

    while True:
        try:
            if not conn.is_connected():
                print("[WARN] MySQL desligado, a reconectar...")
                conn = conectar_mysql()

            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT IDSala,
                       COALESCE(NumeroMarsamisOdd,  0) AS odd,
                       COALESCE(NumeroMarsamisEven, 0) AS even
                FROM ocupacaolabirinto
                WHERE IDSimulacao = %s
                """,
                (SIMULACAO_ID,)
            )
            rows = cursor.fetchall()
            cursor.close()

            for row in rows:
                sala = row["IDSala"]
                odd  = row["odd"]
                even = row["even"]

                count = triggers_fired.get(sala, 0)

                if odd > 0 and odd == even and count < MAX_TRIGGERS:
                    payload = json.dumps({
                        "Type":   "Score",
                        "Player": PLAYER,
                        "Room":   sala
                    })
                    mqtt_client.publish("pisid_mazeact", payload=payload, qos=1)
                    triggers_fired[sala] = count + 1
                    print(f"[GATILHO] Sala {sala}: odd={odd} even={even} "
                          f"→ tentativa {count + 1}/{MAX_TRIGGERS} | payload: {payload}")

            time.sleep(INTERVALO)

        except mysql.connector.Error as e:
            print(f"[ERRO MySQL] {e}")
            time.sleep(2)
            conn = conectar_mysql()

        except Exception as e:
            print(f"[ERRO] {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
