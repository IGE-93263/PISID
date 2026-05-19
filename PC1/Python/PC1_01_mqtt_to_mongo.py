"""
PONTE 1 — PC1: MQTT → MongoDB (Grupo 32)
=========================================
Subscreve os tópicos MQTT do grupo 32 e guarda os documentos
nas coleções MongoDB (labirinto_32).

Validações feitas ANTES de inserir no Mongo:
  - Dados anómalos: tipos errados, datas inválidas, campos nulos

Tolerância a falhas:
  - Failover automático entre mongo1 (27017), mongo2 (27018), mongo3 (27019)
  - Buffer em ficheiro (mqtt_fallback.json) quando MongoDB indisponível
  - Reconexão automática ao broker MQTT

NOTA: A deteção de outliers foi movida para o PC1_02 (MongoDB→MQTT).
      O MongoDB fica como arquivo raw completo — útil para auditoria.
      A lógica de Score (odd=even) corre no PC2_02.

Uso: python PC1_01_mqtt_to_mongo.py [grupo]
     (grupo por omissão: 32)
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

BROKER = "broker.mqtt-dashboard.com"
PORT   = 1883
GRUPO  = 32

MONGO_HOSTS = [
    ("localhost", 27017),
    ("localhost", 27018),
    ("localhost", 27019),
]

FALLBACK_FILE = Path(__file__).parent / "mqtt_fallback.json"

# ─── ESTADO GLOBAL ────────────────────────────────────────────────────────────

_client_mongo  = None
_porta_atual   = None
_fila_fallback = []

_total = {"movimento": 0, "temperatura": 0, "som": 0}

_write_concern = WriteConcern(w="majority")

# Sem outlier state aqui — deteção movida para PC1_02

# ─── FALLBACK EM FICHEIRO ──────────────────────────────────────────────────────

def _carregar_fila():
    global _fila_fallback
    if FALLBACK_FILE.exists():
        try:
            with open(FALLBACK_FILE, encoding="utf-8") as f:
                _fila_fallback = json.load(f)
            if _fila_fallback:
                print(f"[Fallback] {len(_fila_fallback)} msgs pendentes carregadas do disco.")
        except Exception:
            _fila_fallback = []

def _guardar_fila():
    try:
        with open(FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(_fila_fallback, f, ensure_ascii=False, indent=0)
    except Exception:
        pass

# ─── LIGAÇÃO MONGODB COM FAILOVER ─────────────────────────────────────────────

def _get_db(grupo: int):
    """Devolve a base de dados MongoDB do grupo, com failover automático."""
    global _client_mongo, _porta_atual

    if _client_mongo:
        try:
            _client_mongo.admin.command("ping")
            return _client_mongo[f"labirinto_{grupo}"]
        except Exception:
            print(f"[Mongo] Porta {_porta_atual} caiu — a tentar failover...")
            _client_mongo = None

    for host, port in MONGO_HOSTS:
        try:
            c = MongoClient(
                host, port,
                directConnection=True,
                serverSelectionTimeoutMS=3000,
                socketTimeoutMS=5000,
            )
            c.admin.command("ping")
            _client_mongo = c
            _porta_atual  = port
            if port != MONGO_HOSTS[0][1]:
                print(f"[Mongo] Failover OK — ligado a {host}:{port}")
            return c[f"labirinto_{grupo}"]
        except Exception as e:
            print(f"[Mongo] {host}:{port} indisponível: {e}")

    raise ConnectionError("MongoDB completamente indisponível.")

# ─── INSERÇÃO NAS COLEÇÕES MONGO ──────────────────────────────────────────────

def _data_valida(s: str) -> bool:
    if not s:
        return False
    s = str(s).strip()[:19]
    try:
        datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        return True
    except ValueError:
        pass
    try:
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def _inserir(db, topic: str, data: dict):
    """
    Guarda o documento no MongoDB sem filtrar outliers.
    Os outliers são detetados no PC1_02 antes de publicar no MQTT de migração.
    Apenas validações estruturais são feitas aqui (campos obrigatórios, tipos).
    """
    wc = _write_concern

    if "mazemov" in topic:
        player  = data.get("Player")
        marsami = data.get("Marsami")
        origem  = data.get("RoomOrigin")
        destino = data.get("RoomDestiny")
        status  = data.get("Status")
        hora    = data.get("Hora", datetime.now().isoformat())

        if not all(isinstance(x, (int, float)) for x in [player, marsami, origem, destino] if x is not None):
            print(f"[Anomalia movimento] campos numéricos inválidos: {data}")
            return

        if not _data_valida(hora):
            print(f"[Anomalia movimento] data inválida: {hora!r} — a usar hora atual")
            hora = datetime.now().isoformat()

        doc = {
            "Player":      int(player),
            "Marsami":     int(marsami),
            "RoomOrigin":  int(origem),
            "RoomDestiny": int(destino),
            "Status":      status,
            "Hora":        hora,
        }
        db["Movimento"].with_options(write_concern=wc).insert_one(doc)
        _total["movimento"] += 1
        if int(origem) == 0 and int(destino) == 0:
            print(f"[Mongo ✓] Mov #{_total['movimento']} | Marsami {int(marsami)} CANSADO (Status {status})", flush=True)
        elif int(origem) == 0:
            print(f"[Mongo ✓] Mov #{_total['movimento']} | Marsami {int(marsami)} largado na Sala {int(destino)}", flush=True)
        else:
            print(f"[Mongo ✓] Mov #{_total['movimento']} | Marsami {int(marsami)} Sala {int(origem)} → Sala {int(destino)}", flush=True)

    elif "mazetemp" in topic:
        player = data.get("Player")
        hora   = data.get("Hour", data.get("Hora", datetime.now().isoformat()))
        valor  = data.get("Temperature", data.get("temperatura"))

        try:
            valor = float(valor)
        except (TypeError, ValueError):
            print(f"[Anomalia temp] valor não numérico: {valor!r}")
            return

        if not _data_valida(hora):
            hora = datetime.now().isoformat()

        # Guarda RAW — outlier é detetado no PC1_02
        db["temperatura"].with_options(write_concern=wc).insert_one({
            "Player": player, "Hour": hora, "Temperature": valor,
        })
        _total["temperatura"] += 1
        print(f"[Mongo ✓] Temp #{_total['temperatura']} | {valor}ºC", flush=True)

    elif "mazesound" in topic:
        player = data.get("Player")
        hora   = data.get("Hour", data.get("Hora", datetime.now().isoformat()))
        valor  = data.get("Sound", data.get("Som"))

        try:
            valor = float(valor)
        except (TypeError, ValueError):
            print(f"[Anomalia som] valor não numérico: {valor!r}")
            return

        if not _data_valida(hora):
            hora = datetime.now().isoformat()

        # Guarda RAW — outlier é detetado no PC1_02
        db["Som"].with_options(write_concern=wc).insert_one({
            "Player": player, "Hour": hora, "Sound": valor,
        })
        _total["som"] += 1
        print(f"[Mongo ✓] Som #{_total['som']} | {valor}dB", flush=True)

# ─── PROCESSAMENTO DA FILA DE FALLBACK ────────────────────────────────────────

def _processar_fila(grupo: int):
    global _fila_fallback
    if not _fila_fallback:
        return
    try:
        db = _get_db(grupo)
    except ConnectionError:
        return

    restantes = []
    for item in _fila_fallback:
        try:
            _inserir(db, item["topic"], item["data"])
        except Exception:
            restantes.append(item)

    recuperados = len(_fila_fallback) - len(restantes)
    _fila_fallback = restantes
    _guardar_fila()
    if recuperados:
        print(f"[Fallback] {recuperados} msgs recuperadas" +
              (f", {len(restantes)} ainda pendentes" if restantes else "."))

# ─── CALLBACKS MQTT ───────────────────────────────────────────────────────────

def on_connect(c, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        for t in userdata["topics"]:
            c.subscribe(t, qos=1)
        print(f"[MQTT] Ligado a {BROKER} | MongoDB:{_porta_atual}")
        print(f"[MQTT] Tópicos: {userdata['topics']}")
    else:
        print(f"[MQTT] Falha na ligação (código {reason_code})")

def on_disconnect(c, userdata, disconnect_flags, reason_code, properties=None):
    if reason_code != 0:
        print(f"[MQTT] Desconectado (código {reason_code}) — reconexão automática...")

def on_message(c, userdata, msg):
    grupo = userdata["grupo"]
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"[MQTT] Payload inválido (não JSON): {msg.payload!r}")
        return

    for tentativa in range(2):
        try:
            db = _get_db(grupo)
        except ConnectionError as e:
            print(e)
            _fila_fallback.append({"topic": msg.topic, "data": data})
            _guardar_fila()
            print(f"[Fallback] {len(_fila_fallback)} msgs em fila.")
            return
        try:
            _inserir(db, msg.topic, data)
            _processar_fila(grupo)
            return
        except Exception as ex:
            global _client_mongo
            _client_mongo = None
            if tentativa == 0:
                continue
            print(f"[Mongo] Insert falhou 2x: {ex}")

    _fila_fallback.append({"topic": msg.topic, "data": data})
    _guardar_fila()
    print(f"[Fallback] {len(_fila_fallback)} msgs em fila (insert falhou).")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    grupo = int(sys.argv[1]) if len(sys.argv) > 1 else GRUPO

    topics = [
        f"pisid_mazemov_{grupo}",
        f"pisid_mazetemp_{grupo}",
        f"pisid_mazesound_{grupo}",
    ]

    print("=" * 55)
    print(f" PONTE 1 — MQTT → MongoDB  (Grupo {grupo})")
    print("=" * 55)

    _carregar_fila()

    try:
        _get_db(grupo)
        print(f"[Mongo] Ligado a porta {_porta_atual}")
    except ConnectionError as e:
        print(f"[Mongo] ERRO: {e}")
        print("Verifique se o Docker está a correr (docker-compose up -d)")
        sys.exit(1)

    _processar_fila(grupo)

    uid = f"pisid_g32_pc1_{grupo}_{int(time.time())}"
    c = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=uid,
        clean_session=True,
        userdata={"topics": topics, "grupo": grupo},
    )
    print(f"[MQTT] Client ID: {uid}", flush=True)
    c.on_connect    = on_connect
    c.on_disconnect = on_disconnect
    c.on_message    = on_message
    c.reconnect_delay_set(min_delay=2, max_delay=60)

    print(f"[MQTT] A ligar a {BROKER}:{PORT}...")
    c.connect(BROKER, PORT, keepalive=60)

    try:
        c.loop_forever()
    except KeyboardInterrupt:
        print("\n[Ctrl+C] A encerrar...")
    finally:
        c.disconnect()
        print("[MQTT] Desligado.")

if __name__ == "__main__":
    main()
