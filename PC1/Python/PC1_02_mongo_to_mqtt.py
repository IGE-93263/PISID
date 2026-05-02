"""
PC1 — MongoDB → MQTT (Grupo 32)
================================
Lê incrementalmente as coleções MongoDB e publica no broker MQTT.
Usa checkpoint por _id para nunca reenviar o mesmo documento.

Tópicos publicados:
  pisid_mig_mov_32   — movimentos
  pisid_mig_temp_32  — temperaturas
  pisid_mig_sound_32 — som

Uso: python mongo_to_mqtt.py [grupo]
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from bson import ObjectId
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

GRUPO        = 32
BROKER       = "broker.emqx.io"
PORT         = 1883
INTERVALO_SEG = 0.1        # periodicidade de leitura do Mongo
LOTE_MAX_NORMAL   = 20    # regime normal (ciclos rápidos de 0.1s)
LOTE_MAX_ARRANQUE = 50    # arranque: quando há muitos docs acumulados
QOS          = 1

# Nome da BD MongoDB (igual ao PC1_01)
DB_NAME = "labirinto_{grupo}"

MONGO_HOSTS = [
    ("localhost", 27017),
    ("localhost", 27018),
    ("localhost", 27019),
]

CHECKPOINT_FILE = Path(__file__).parent / "mongo_mqtt_checkpoint.json"

# ─── ESTADO GLOBAL ────────────────────────────────────────────────────────────

_mqtt_client   = None
_mongo_client  = None
_porta_mongo   = None

# contadores para log
_total = {"Movimento": 0, "temperatura": 0, "Som": 0}


# ─── CHECKPOINT ───────────────────────────────────────────────────────────────

def _carregar_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"Movimento": None, "temperatura": None, "Som": None}


def _guardar_checkpoint(cp: dict):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(cp, f)


# ─── LIGAÇÃO MONGODB ──────────────────────────────────────────────────────────

def _get_mongo_db(grupo: int):
    global _mongo_client, _porta_mongo
    # reutiliza ligação existente
    if _mongo_client:
        try:
            _mongo_client.admin.command("ping")
            return _mongo_client[f"labirinto_{grupo}"]
        except Exception:
            print(f"[Mongo] Porta {_porta_mongo} caiu — failover...", flush=True)
            _mongo_client = None

    for host, port in MONGO_HOSTS:
        try:
            c = MongoClient(host, port, directConnection=True,
                            serverSelectionTimeoutMS=2000)
            c.admin.command("ping")
            _mongo_client = c
            _porta_mongo  = port
            print(f"[Mongo] Ligado a {host}:{port}", flush=True)
            return c[f"labirinto_{grupo}"]
        except Exception:
            pass
    raise ConnectionError("MongoDB indisponível.")


# ─── PUBLICAÇÃO MQTT ──────────────────────────────────────────────────────────

def _publicar(topic: str, payload: dict):
    """Publica um documento como JSON no broker."""
    msg = json.dumps(payload, default=str, ensure_ascii=False)
    result = _mqtt_client.publish(topic, msg, qos=QOS)
    result.wait_for_publish(timeout=5)


# ─── VALIDAÇÃO (DADOS ANÓMALOS) ───────────────────────────────────────────────

def _hora_valida(hora) -> str | None:
    """Converte para string MySQL-compatível ou devolve None se inválida."""
    if not hora:
        return None
    s = str(hora).strip()[:19].replace("T", " ")
    try:
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return s
    except ValueError:
        return None


def _validar_movimento(doc: dict) -> dict | None:
    """Valida campos obrigatórios. Devolve dict limpo ou None se inválido."""
    try:
        player  = int(doc["Player"])
        marsami = int(doc["Marsami"])
        origem  = int(doc["RoomOrigin"])
        destino = int(doc["RoomDestiny"])
        status  = doc.get("Status")
        hora    = _hora_valida(doc.get("Hora"))
    except (KeyError, TypeError, ValueError) as e:
        print(f"[Anomalia mov] campos inválidos: {e} | doc={doc}", flush=True)
        return None

    return {
        "Player": player, "Marsami": marsami,
        "RoomOrigin": origem, "RoomDestiny": destino,
        "Status": status, "Hora": hora or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _validar_temperatura(doc: dict) -> dict | None:
    try:
        valor = float(doc.get("Temperature", doc.get("temperatura")))
        if not (-50 <= valor <= 150):
            print(f"[Anomalia temp] fora de limites: {valor}", flush=True)
            return None
        hora = _hora_valida(doc.get("Hour", doc.get("Hora")))
        return {
            "Player": doc.get("Player"),
            "Hour": hora or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Temperature": valor,
        }
    except (TypeError, ValueError) as e:
        print(f"[Anomalia temp] {e}", flush=True)
        return None


def _validar_som(doc: dict) -> dict | None:
    try:
        valor = float(doc.get("Sound", doc.get("som")))
        if not (0 <= valor <= 200):
            print(f"[Anomalia som] fora de limites: {valor}", flush=True)
            return None
        hora = _hora_valida(doc.get("Hour", doc.get("Hora")))
        return {
            "Player": doc.get("Player"),
            "Hour": hora or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Sound": valor,
        }
    except (TypeError, ValueError) as e:
        print(f"[Anomalia som] {e}", flush=True)
        return None


# ─── CICLO DE MIGRAÇÃO ────────────────────────────────────────────────────────

def _run_ciclo(grupo: int):
    db = _get_mongo_db(grupo)
    cp = _carregar_checkpoint()
    alterou = False

    # Lote adaptativo: no arranque pode haver muitos docs acumulados
    # mas limitamos para não exceder o rate limit do broker (~10 msg/s)
    lote = LOTE_MAX_ARRANQUE if cp["Movimento"] is None else LOTE_MAX_NORMAL

    # ── Movimento ──
    topic_mov = f"pisid_mig_mov_{grupo}"
    filtro = {} if cp["Movimento"] is None else {"_id": {"$gt": ObjectId(cp["Movimento"])}}
    docs = list(db["Movimento"].find(filtro).sort("_id", 1).limit(lote))
    n = 0
    for doc in docs:
        payload = _validar_movimento(doc)
        if payload:
            _publicar(topic_mov, payload)
            n += 1
    if docs:
        cp["Movimento"] = str(docs[-1]["_id"])
        alterou = True
    if n:
        _total["Movimento"] += n
        print(f"[→ MQTT] Movimento: {n} docs (total={_total['Movimento']})", flush=True)

    # ── Temperatura ──
    topic_temp = f"pisid_mig_temp_{grupo}"
    filtro = {} if cp["temperatura"] is None else {"_id": {"$gt": ObjectId(cp["temperatura"])}}
    docs = list(db["temperatura"].find(filtro).sort("_id", 1).limit(lote))
    n = 0
    for doc in docs:
        payload = _validar_temperatura(doc)
        if payload:
            _publicar(topic_temp, payload)
            n += 1
    if docs:
        cp["temperatura"] = str(docs[-1]["_id"])
        alterou = True
    if n:
        _total["temperatura"] += n
        print(f"[→ MQTT] Temperatura: {n} docs (total={_total['temperatura']})", flush=True)

    # ── Som ──
    topic_som = f"pisid_mig_sound_{grupo}"
    filtro = {} if cp["Som"] is None else {"_id": {"$gt": ObjectId(cp["Som"])}}
    docs = list(db["Som"].find(filtro).sort("_id", 1).limit(lote))
    n = 0
    for doc in docs:
        payload = _validar_som(doc)
        if payload:
            _publicar(topic_som, payload)
            n += 1
    if docs:
        cp["Som"] = str(docs[-1]["_id"])
        alterou = True
    if n:
        _total["Som"] += n
        print(f"[→ MQTT] Som: {n} docs (total={_total['Som']})", flush=True)

    if alterou:
        _guardar_checkpoint(cp)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    global _mqtt_client
    grupo = int(sys.argv[1]) if len(sys.argv) > 1 else GRUPO

    print("=" * 55, flush=True)
    print(f" PC1 — MongoDB → MQTT  (Grupo {grupo})", flush=True)
    print(f" BD: labirinto_{grupo}  |  Broker: {BROKER}", flush=True)
    print(f" Tópicos: pisid_mig_mov/temp/sound_{grupo}", flush=True)
    print(f" Intervalo: {INTERVALO_SEG}s", flush=True)
    print("=" * 55, flush=True)

    # Verificar MongoDB
    try:
        _get_mongo_db(grupo)
    except ConnectionError as e:
        print(f"[ERRO] {e}", flush=True)
        sys.exit(1)

    # Ligar ao MQTT
    _mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    _mqtt_client.on_connect = lambda c, u, f, rc, p=None: print(
        f"[MQTT] Ligado a {BROKER} (rc={rc})", flush=True)
    _mqtt_client.on_disconnect = lambda c, u, df, rc, p=None: print(
        f"[MQTT] Desconectado (rc={rc})", flush=True) if rc != 0 else None
    _mqtt_client.reconnect_delay_set(min_delay=2, max_delay=30)
    _mqtt_client.connect(BROKER, PORT, keepalive=60)
    _mqtt_client.loop_start()  # thread em background — não bloqueia

    print(f"[MQTT] A ligar a {BROKER}:{PORT}...", flush=True)
    time.sleep(2)  # aguarda ligação inicial

    print("A iniciar ciclo de migração. Ctrl+C para parar.\n", flush=True)
    while True:
        try:
            _run_ciclo(grupo)
        except ConnectionError as e:
            print(f"[Mongo] {e} — a tentar novamente...", flush=True)
        except Exception as e:
            print(f"[Erro] {e}", flush=True)
        try:
            time.sleep(INTERVALO_SEG)
        except KeyboardInterrupt:
            break

    print("\n[Ctrl+C] A encerrar...", flush=True)
    _mqtt_client.loop_stop()
    _mqtt_client.disconnect()


if __name__ == "__main__":
    main()
