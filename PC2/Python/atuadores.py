"""
atuadores.py — Lógica de atuadores automáticos (corre no PC2).

Publica comandos no tópico pisid_mazeact_<grupo> quando:
  - Temperatura acima do máximo → liga AC na sala  (TurnOnAC)
  - Temperatura volta ao normal → desliga AC        (TurnOffAC)
  - Som acima do máximo        → fecha corredor     (CloseGate)

Limites lidos do MySQL local (configtemp / configsound).
"""

import json
import threading
from db_mysql import get_connection

_DEFAULT_TEMP_MAX = 60.0
_DEFAULT_SOM_MAX  = 36.0
_RELOAD_INTERVALO = 30   # segundos entre recargas dos limites


class Atuadores:

    def __init__(self, grupo: int, mqtt_client):
        self._grupo   = grupo
        self._mqtt    = mqtt_client
        self._topic   = f"pisid_mazeact_{grupo}"
        self._ac_ligado: set[int]    = set()
        self._corredores_fechados: set[tuple] = set()
        self._temp_max = _DEFAULT_TEMP_MAX
        self._som_max  = _DEFAULT_SOM_MAX
        self._carregar_limites()
        self._agendar_reload()
        print(f"[atuadores] ativo | temp max={self._temp_max} | som max={self._som_max}", flush=True)

    def _carregar_limites(self):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT maximo FROM configtemp LIMIT 1")
            row = cur.fetchone()
            if row:
                self._temp_max = float(row[0])
            cur.execute("SELECT maximo FROM configsound LIMIT 1")
            row = cur.fetchone()
            if row:
                self._som_max = float(row[0])
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[atuadores] aviso: não consegui ler limites do MySQL ({e}). A usar defaults.", flush=True)

    def _agendar_reload(self):
        t = threading.Timer(_RELOAD_INTERVALO, self._reload_periodico)
        t.daemon = True
        t.start()

    def _reload_periodico(self):
        self._carregar_limites()
        self._agendar_reload()

    def _publicar(self, payload: dict):
        try:
            self._mqtt.publish(self._topic, json.dumps(payload), qos=1)
            print(f"[atuadores] → {payload}", flush=True)
        except Exception as e:
            print(f"[atuadores] erro ao publicar: {e}", flush=True)

    def processar_temperatura(self, sala: int, valor: float):
        ac_on = sala in self._ac_ligado
        if valor > self._temp_max and not ac_on:
            self._ac_ligado.add(sala)
            self._publicar({"Type": "TurnOnAC",  "Player": self._grupo, "Room": sala})
        elif valor <= self._temp_max and ac_on:
            self._ac_ligado.discard(sala)
            self._publicar({"Type": "TurnOffAC", "Player": self._grupo, "Room": sala})

    def processar_som(self, sala: int, valor: float, sala_origem: int | None):
        if valor <= self._som_max:
            return
        par = (sala_origem, sala) if sala_origem is not None else (sala, 0)
        if par not in self._corredores_fechados:
            self._corredores_fechados.add(par)
            self._publicar({"Type": "CloseGate", "Player": self._grupo, "Room1": par[0], "Room2": par[1]})

    def imprimir_estado(self):
        ac   = ", ".join(str(s) for s in sorted(self._ac_ligado)) or "nenhuma"
        corr = ", ".join(f"{a}→{b}" for a, b in sorted(self._corredores_fechados)) or "nenhum"
        print(f"[atuadores] AC ligado: {ac} | Corredores fechados: {corr}", flush=True)
