"""
PONTE 1 — PC1: MQTT → MongoDB (Grupo 32)
=========================================
Subscreve os tópicos MQTT do grupo 32 e guarda os documentos
nas coleções MongoDB (labirinto_32).

Validações feitas ANTES de inserir no Mongo:
  - Dados anómalos: tipos errados, datas inválidas, campos nulos
  - Outliers de som/temperatura: valores acima de 36 dB/ºC de variação
    brusca ou fora de limites físicos

Tolerância a falhas:
  - Failover automático entre mongo1 (27017), mongo2 (27018), mongo3 (27019)
  - Buffer em ficheiro (mqtt_fallback.json) quando MongoDB indisponível
  - Reconexão automática ao broker MQTT

Uso: python ponte1_mqtt_to_mongo.py [grupo]
     (grupo por omissão: 32)
"""

import json
import math
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern


# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

BROKER = "broker.emqx.io"   # broker público MQTT
PORT   = 1883
GRUPO  = 32                  # número do grupo (pode ser passado como argumento)

MONGO_HOSTS = [              # PC1 — réplicas locais
    ("localhost", 27017),
    ("localhost", 27018),
    ("localhost", 27019),
]

FALLBACK_FILE = Path(__file__).parent / "mqtt_fallback.json"

# Limites físicos absolutos — rejeição imediata (dados anómalos, não outliers)
# Valores fisicamente impossíveis para um labirinto interior
TEMP_MIN, TEMP_MAX = -10.0, 80.0   # ºC
SOM_MIN,  SOM_MAX  =   0.0, 200.0  # dB

# Outlier estatístico — Z-score: se |valor - média| / desvio_padrão > Z_THRESHOLD → outlier
# Não usamos valor fixo: o critério adapta-se ao desvio real dos dados
# Z=2.5 significa: rejeita valores a mais de 2.5 desvios padrão da média
Z_THRESHOLD    = 2.5
JANELA_TAMANHO = 20         # últimas N leituras para calcular média e desvio

# ─── ESTADO GLOBAL ────────────────────────────────────────────────────────────

_client_mongo  = None        # cliente MongoClient ativo
_porta_atual   = None
_fila_fallback = []          # msgs em espera quando Mongo indisponível
_write_concern = WriteConcern(w="majority")

# janelas deslizantes independentes por sensor
_janela_som  = deque(maxlen=JANELA_TAMANHO)
_janela_temp = deque(maxlen=JANELA_TAMANHO)


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


# ─── VALIDAÇÃO DE DADOS ANÓMALOS ──────────────────────────────────────────────

def _parse_float(v):
    """Tenta converter para float; devolve None se impossível."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _data_valida(s: str) -> bool:
    """Verifica se uma string de data/hora é plausível."""
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


def _stats_janela(janela: deque) -> tuple[float, float] | None:
    """Devolve (média, desvio_padrão) ou None se janela insuficiente."""
    n = len(janela)
    if n < 5:
        return None   # amostras insuficientes para estatística fiável
    media = sum(janela) / n
    variancia = sum((x - media) ** 2 for x in janela) / n
    std = math.sqrt(variancia)
    return media, std if std > 0 else 0.1  # evita divisão por zero


def _validar_som(valor_raw) -> tuple:
    """
    1. Rejeita dados anómalos (tipo errado ou fora de limites físicos).
    2. Rejeita outliers estatísticos via Z-score (|z| > Z_THRESHOLD).
    Retorna (valor_float, True) se válido, ou (None, False) caso contrário.
    """
    v = _parse_float(valor_raw)
    if v is None:
        print(f"[Anomalia som] valor não numérico: {valor_raw!r}")
        return None, False
    if not (SOM_MIN <= v <= SOM_MAX):
        print(f"[Anomalia som] fora de limites físicos [{SOM_MIN}, {SOM_MAX}]: {v}")
        return None, False

    # Outlier estatístico — Z-score
    stats = _stats_janela(_janela_som)
    if stats is not None:
        media, std = stats
        z = abs(v - media) / std
        if z > Z_THRESHOLD:
            print(f"[Outlier som] z={z:.1f} > {Z_THRESHOLD} | valor={v} média={media:.1f} std={std:.2f}")
            _janela_som.append(v)
            return None, False

    _janela_som.append(v)
    return v, True


def _validar_temperatura(valor_raw) -> tuple:
    """
    1. Rejeita dados anómalos (tipo errado ou fora de limites físicos).
    2. Rejeita outliers estatísticos via Z-score (|z| > Z_THRESHOLD).
    Retorna (valor_float, True) se válido, ou (None, False) caso contrário.
    """
    v = _parse_float(valor_raw)
    if v is None:
        print(f"[Anomalia temp] valor não numérico: {valor_raw!r}")
        return None, False
    if not (TEMP_MIN <= v <= TEMP_MAX):
        print(f"[Anomalia temp] fora de limites físicos [{TEMP_MIN}, {TEMP_MAX}]: {v}")
        return None, False

    # Outlier estatístico — Z-score
    stats = _stats_janela(_janela_temp)
    if stats is not None:
        media, std = stats
        z = abs(v - media) / std
        if z > Z_THRESHOLD:
            print(f"[Outlier temp] z={z:.1f} > {Z_THRESHOLD} | valor={v} média={media:.1f} std={std:.2f}")
            _janela_temp.append(v)
            return None, False

    _janela_temp.append(v)
    return v, True


# ─── INSERÇÃO NAS COLEÇÕES MONGO ──────────────────────────────────────────────

def _inserir(db, topic: str, data: dict):
    """Valida e insere o documento na coleção correta do MongoDB."""
    wc = _write_concern

    if "mazemov" in topic:
        # Validação básica de tipos
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


    elif "mazetemp" in topic:
        player = data.get("Player")
        hora   = data.get("Hour", data.get("Hora", datetime.now().isoformat()))
        valor, ok = _validar_temperatura(data.get("Temperature", data.get("temperatura")))

        if not ok:
            return  # rejeitado (anomalia ou outlier) — não guarda no Mongo

        if not _data_valida(hora):
            hora = datetime.now().isoformat()

        doc = {
            "Player":      player,
            "Hour":        hora,
            "Temperature": valor,
        }
        db["temperatura"].with_options(write_concern=wc).insert_one(doc)


    elif "mazesound" in topic:
        player = data.get("Player")
        hora   = data.get("Hour", data.get("Hora", datetime.now().isoformat()))
        valor, ok = _validar_som(data.get("Sound", data.get("som")))

        if not ok:
            return

        if not _data_valida(hora):
            hora = datetime.now().isoformat()

        doc = {
            "Player": player,
            "Hour":   hora,
            "Sound":  valor,
        }
        db["Som"].with_options(write_concern=wc).insert_one(doc)



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

    # Verificar ligação inicial ao Mongo
    try:
        _get_db(grupo)
        print(f"[Mongo] Ligado a porta {_porta_atual}")
    except ConnectionError as e:
        print(f"[Mongo] ERRO: {e}")
        print("Verifique se o Docker está a correr (docker-compose up -d)")
        sys.exit(1)

    _processar_fila(grupo)  # recupera fila de execução anterior

    c = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata={"topics": topics, "grupo": grupo},
    )
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
