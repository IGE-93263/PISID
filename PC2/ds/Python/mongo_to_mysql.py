"""
Migração incremental MongoDB → MySQL.
Lê novos documentos do Mongo e insere no MySQL.
Usa checkpoint por coleção para não reprocessar.

Uso: python mongo_to_mysql.py [grupo]
     (correr em paralelo com mqtt_to_db ou como cron a cada N seg)
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

from outlier_detector import validar_temperatura, validar_som

try:
    from db_mysql import get_connection, MYSQL_CONFIG
except ImportError:
    MYSQL_CONFIG = {"host": "localhost", "user": "root", "password": "", "database": "labirinto", "port": 3306}
    def get_connection():
        import mysql.connector
        return mysql.connector.connect(**MYSQL_CONFIG)

GRUPO = 19
ID_SIMULACAO = 1  # FK para simulacao (corresponde ao seed labirinto_seed.sql)
MONGO_PORTS = [27017, 27018, 27019]
CHECKPOINT_FILE = Path(__file__).parent / "migration_checkpoint.json"
INTERVALO_SEG = 5


def get_mongo_db(grupo):
    """Conecta a um MongoDB disponível."""
    for port in MONGO_PORTS:
        try:
            client = MongoClient("localhost", port, directConnection=True, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            return client[f"pisid_grupo{grupo}"]
        except Exception:
            pass
    raise ConnectionError("MongoDB indisponível")


def carregar_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"movimento": None, "temperatura": None, "som": None}


def guardar_checkpoint(cp):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(cp, f)


def hora_valida(hora):
    """Retorna hora válida para MySQL ou None (ex: 2025-05-32 é inválido)."""
    if not hora:
        return None
    s = str(hora).strip()[:19]
    if not re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", s):
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def migrar_movimento(conn_mysql, docs, grupo):
    """Schema labirinto: IDSimulacao, IDSalaOrigem, IDSalaDestino, Hora, Marsami, Status"""
    if not docs:
        return 0
    cursor = conn_mysql.cursor()
    n = 0
    for d in docs:
        try:
            sql = """
                INSERT INTO medicoespassagens (IDSimulacao, IDSalaOrigem, IDSalaDestino, Hora, Marsami, Status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            hora = hora_valida(d.get("Hora"))
            cursor.execute(sql, (
                ID_SIMULACAO,
                d.get("RoomOrigin", 0),
                d.get("RoomDestiny", 0),
                hora,
                d.get("Marsami"),
                d.get("Status"),
            ))
            n += 1
        except Exception as e:
            print(f"  Erro movimento: {e}")
    conn_mysql.commit()
    cursor.close()
    return n


def migrar_temperatura(conn_mysql, docs, grupo):
    """Schema labirinto: IDSimulacao, Hora, Temperatura (varchar)"""
    if not docs:
        return 0
    cursor = conn_mysql.cursor()
    n = n_rejeitados = 0
    for d in docs:
        try:
            raw = d.get("Temperature", d.get("temperatura"))
            valor, motivo = validar_temperatura(raw)
            if valor is None:
                n_rejeitados += 1
                print(f"  [OUTLIER temperatura] rejeitado — {motivo}")
                continue
            sql = "INSERT INTO temperatura (IDSimulacao, Hora, Temperatura) VALUES (%s, %s, %s)"
            hora = hora_valida(d.get("Hour", d.get("Hora")))
            cursor.execute(sql, (ID_SIMULACAO, hora, str(valor)))
            n += 1
        except Exception as e:
            print(f"  Erro temperatura: {e}")
    conn_mysql.commit()
    cursor.close()
    if n_rejeitados:
        print(f"  Temperatura: {n} inseridos, {n_rejeitados} rejeitados (outliers/dados sujos)")
    return n


def migrar_som(conn_mysql, docs, grupo):
    """Schema labirinto: IDSimulacao, Hora, Som (varchar)"""
    if not docs:
        return 0
    cursor = conn_mysql.cursor()
    n = n_rejeitados = 0
    for d in docs:
        try:
            raw = d.get("Sound", d.get("som"))
            valor, motivo = validar_som(raw)
            if valor is None:
                n_rejeitados += 1
                print(f"  [OUTLIER som] rejeitado — {motivo}")
                continue
            sql = "INSERT INTO som (IDSimulacao, Hora, Som) VALUES (%s, %s, %s)"
            hora = hora_valida(d.get("Hour", d.get("Hora")))
            cursor.execute(sql, (ID_SIMULACAO, hora, str(valor)))
            n += 1
        except Exception as e:
            print(f"  Erro som: {e}")
    conn_mysql.commit()
    cursor.close()
    if n_rejeitados:
        print(f"  Som: {n} inseridos, {n_rejeitados} rejeitados (outliers/dados sujos)")
    return n


def run_migracao(grupo):
    db = get_mongo_db(grupo)
    cp = carregar_checkpoint()
    conn_mysql = None

    try:
        conn_mysql = get_connection()
    except Exception as e:
        print(f"MySQL indisponível: {e}")
        return cp

    total = 0

    # Movimento
    q = {} if cp["movimento"] is None else {"_id": {"$gt": ObjectId(cp["movimento"])}}
    cursor = db["movimento"].find(q).sort("_id", 1).limit(500)
    docs = list(cursor)
    if docs:
        n = migrar_movimento(conn_mysql, docs, grupo)
        total += n
        cp["movimento"] = str(docs[-1]["_id"])

    # Temperatura
    q = {} if cp["temperatura"] is None else {"_id": {"$gt": ObjectId(cp["temperatura"])}}
    cursor = db["temperatura"].find(q).sort("_id", 1).limit(500)
    docs = list(cursor)
    if docs:
        n = migrar_temperatura(conn_mysql, docs, grupo)
        total += n
        cp["temperatura"] = str(docs[-1]["_id"])

    # Som
    q = {} if cp["som"] is None else {"_id": {"$gt": ObjectId(cp["som"])}}
    cursor = db["som"].find(q).sort("_id", 1).limit(500)
    docs = list(cursor)
    if docs:
        n = migrar_som(conn_mysql, docs, grupo)
        total += n
        cp["som"] = str(docs[-1]["_id"])

    if total > 0:
        guardar_checkpoint(cp)
        print(f"Migrados: {total} docs")

    if conn_mysql:
        conn_mysql.close()
    return cp


def main():
    grupo = int(sys.argv[1]) if len(sys.argv) > 1 else GRUPO
    print(f"Migração incremental MongoDB → MySQL (grupo {grupo})")
    print(f"Intervalo: {INTERVALO_SEG}s. Ctrl+C para parar.\n")

    while True:
        try:
            run_migracao(grupo)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Erro: {e}")
        time.sleep(INTERVALO_SEG)


if __name__ == "__main__":
    main()
