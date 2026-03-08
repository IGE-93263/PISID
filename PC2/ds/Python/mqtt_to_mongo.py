"""
MQTT -> MongoDB. Tolerância a falhas (crash DB/PC/software).
- Prioridade: 27017, 27018, 27019
- Write concern majority (sem perda de dados)
- Retry com failover quando insert falha
- Buffer em ficheiro quando MongoDB indisponível
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

BROKER = "broker.emqx.io"
PORT = 1883
GRUPO = 19

clients = [
    (27017, MongoClient("localhost", 27017, directConnection=True, serverSelectionTimeoutMS=3000, socketTimeoutMS=5000)),
    (27018, MongoClient("localhost", 27018, directConnection=True, serverSelectionTimeoutMS=3000, socketTimeoutMS=5000)),
    (27019, MongoClient("localhost", 27019, directConnection=True, serverSelectionTimeoutMS=3000, socketTimeoutMS=5000)),
]
client_atual = None
porta_atual = None
fila_fallback = []  # mensagens em espera quando MongoDB indisponível
FALLBACK_FILE = Path(__file__).parent / "mqtt_fallback.json"
wc = WriteConcern(w="majority")


def carregar_fila():
    global fila_fallback
    if FALLBACK_FILE.exists():
        try:
            with open(FALLBACK_FILE, encoding="utf-8") as f:
                fila_fallback = json.load(f)
        except Exception:
            fila_fallback = []


def guardar_fila():
    try:
        with open(FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(fila_fallback, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def get_db(grupo):
    global client_atual, porta_atual
    if client_atual:
        try:
            client_atual.admin.command("ping")
            return client_atual[f"pisid_grupo{grupo}"]
        except Exception:
            client_atual = None
            print(f"MongoDB {porta_atual} caiu. Failover...")
    for porta, client in clients:
        try:
            client.admin.command("ping")
            is_primary = client.admin.command("ismaster").get("ismaster")
            client_atual = client
            porta_atual = porta
            if porta != 27017:
                print(f"Failover OK: ligado à porta {porta}" + ("" if is_primary else " (secundário)"))
            if not is_primary:
                print("Aviso: nó secundário, writes podem falhar (falta quorum)")
            return client[f"pisid_grupo{grupo}"]
        except Exception as e:
            print(f"Porta {porta}: {e}")
    raise ConnectionError("MongoDB indisponível")


def inserir(db, topic, data, grupo):
    if "mazemov" in topic:
        db["movimento"].with_options(write_concern=wc).insert_one({**data, "Hora": datetime.now().isoformat()})
    elif "mazetemp" in topic:
        db["temperatura"].with_options(write_concern=wc).insert_one(data)
    elif "mazesound" in topic:
        db["som"].with_options(write_concern=wc).insert_one(data)


def processar_fila(grupo):
    """Reenvia mensagens em fila quando MongoDB volta."""
    global fila_fallback
    if not fila_fallback:
        return
    try:
        db = get_db(grupo)
    except ConnectionError:
        return
    restantes = []
    for item in fila_fallback:
        try:
            inserir(db, item["topic"], item["data"], grupo)
        except Exception:
            restantes.append(item)
    n_recuperados = len(fila_fallback) - len(restantes)
    fila_fallback = restantes
    guardar_fila()
    if n_recuperados:
        print(f"Fila: {n_recuperados} msgs recuperadas" + (f", {len(restantes)} pendentes" if restantes else ""))


def on_connect(c, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        for t in userdata["topics"]:
            c.subscribe(t)
        print(f"OK | MQTT:{BROKER} | Mongo:{porta_atual}")


def on_disconnect(c, userdata, disconnect_flags, reason_code, properties=None):
    if reason_code != 0:
        print(f"MQTT desconectado (código {reason_code}). Reconexão automática...")


def on_message(c, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    grupo = userdata["grupo"]
    topic = msg.topic

    for tentativa in range(2):
        try:
            db = get_db(grupo)
        except ConnectionError as e:
            print(e)
            fila_fallback.append({"topic": topic, "data": data})
            guardar_fila()
            print(f"Mensagem em fila ({len(fila_fallback)} pendentes)")
            return
        try:
            inserir(db, topic, data, grupo)
            processar_fila(grupo)
            break
        except Exception:
            global client_atual
            client_atual = None
            if tentativa == 0:
                continue

    else:
        fila_fallback.append({"topic": topic, "data": data})
        guardar_fila()
        print(f"Insert falhou 2x. Mensagem em fila ({len(fila_fallback)} pendentes)")


def main():
    global fila_fallback
    grupo = int(sys.argv[1]) if len(sys.argv) > 1 else GRUPO
    topics = [f"pisid_mazemov_{grupo}", f"pisid_mazetemp_{grupo}", f"pisid_mazesound_{grupo}"]

    carregar_fila()
    if fila_fallback:
        print(f"Início: {len(fila_fallback)} msgs em fila")

    try:
        get_db(grupo)
    except ConnectionError as e:
        print(e)
        sys.exit(1)

    processar_fila(grupo)  # recupera fila de execução anterior (se MongoDB esteve em baixo)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata={"topics": topics, "grupo": grupo})
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.on_message = on_message
    c.reconnect_delay_set(min_delay=1, max_delay=120)
    c.connect(BROKER, PORT, 60)
    try:
        c.loop_forever()
    finally:
        for _, client in clients:
            try:
                client.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
