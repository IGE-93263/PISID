"""
gatilho_odd_even.py — Lógica dos gatilhos odd/even (corre no PC2).

  - Marsami odd  = ID ímpar | Marsami even = ID par
  - Quando odd == even > 0 numa sala → envia Score via MQTT
  - Máximo 3 gatilhos por sala por simulação
  - Não repete enquanto equilíbrio não se desfizer
"""

import json

MAX_GATILHOS_POR_SALA = 3


class GatilhoOddEven:

    def __init__(self, grupo: int, mqtt_client, db_conn=None, id_simulacao=1):
        self._grupo        = grupo
        self._mqtt         = mqtt_client
        self._db_conn      = db_conn
        self._id_simulacao = id_simulacao
        self._salas: dict[int, dict] = {}
        print(f"[odd/even] Tracker ativo (max {MAX_GATILHOS_POR_SALA} gatilhos/sala)", flush=True)

    def _sala(self, sala_id: int) -> dict:
        if sala_id not in self._salas:
            self._salas[sala_id] = {"odd": 0, "even": 0, "gatilhos": 0, "em_equilibrio": False}
        return self._salas[sala_id]

    def _is_odd(self, marsami_id: int) -> bool:
        return marsami_id % 2 != 0

    def processar_movimento(self, msg: dict):
        try:
            marsami_id = int(msg.get("Marsami", 0))
            origem     = int(msg.get("RoomOrigin",  0))
            destino    = int(msg.get("RoomDestiny", 0))
        except (TypeError, ValueError):
            return

        tipo = "odd" if self._is_odd(marsami_id) else "even"

        # Marsami cansado/preso
        if origem == 0 and destino == 0:
            return

        # Largada inicial
        if origem == 0 and destino > 0:
            self._sala(destino)[tipo] += 1
            self._verificar_gatilho(destino)
            return

        # Movimento normal
        if origem > 0:
            s = self._sala(origem)
            s[tipo] = max(0, s[tipo] - 1)
            self._verificar_equilibrio_quebrado(origem)

        if destino > 0:
            self._sala(destino)[tipo] += 1
            self._verificar_gatilho(destino)

    def _verificar_equilibrio_quebrado(self, sala_id: int):
        s = self._sala(sala_id)
        if s["em_equilibrio"] and s["odd"] != s["even"]:
            s["em_equilibrio"] = False
            print(f"  [odd/even] Sala {sala_id}: equilíbrio desfeito ({s['odd']} odd vs {s['even']} even)", flush=True)

    def _verificar_gatilho(self, sala_id: int):
        s   = self._sala(sala_id)
        odd = s["odd"]
        even = s["even"]

        if odd <= 0 or even <= 0 or odd != even:
            return
        if s["em_equilibrio"]:
            return
        if s["gatilhos"] >= MAX_GATILHOS_POR_SALA:
            print(f"  [odd/even] Sala {sala_id}: limite de {MAX_GATILHOS_POR_SALA} gatilhos atingido.", flush=True)
            return

        s["em_equilibrio"] = True
        s["gatilhos"] += 1
        payload = {"Type": "Score", "Player": self._grupo, "Room": sala_id}
        try:
            self._mqtt.publish("pisid_mazeact", json.dumps(payload), qos=1)
            print(f"  [odd/even] Sala {sala_id}: odd={odd} == even={even} → Score! ({s['gatilhos']}/{MAX_GATILHOS_POR_SALA})", flush=True)
        except Exception as e:
            print(f"  [odd/even] Erro ao enviar Score sala {sala_id}: {e}", flush=True)

        # Guardar pontuação no histórico local
        if self._db_conn:
            try:
                cur = self._db_conn.cursor()
                cur.execute(
                    "INSERT INTO pontuacoes (IDSimulacao, IDSala, Hora) VALUES (%s, %s, NOW(6))",
                    (self._id_simulacao, sala_id)
                )
                self._db_conn.commit()
                cur.close()
                print(f"  [odd/even] Pontuação guardada — Sala {sala_id}", flush=True)
            except Exception as e:
                print(f"  [odd/even] Erro ao guardar pontuação: {e}", flush=True)

    def imprimir_estado(self):
        if not self._salas:
            print("  [odd/even] Sem movimentos ainda.", flush=True)
            return
        print("  [odd/even] Estado das salas:", flush=True)
        for sid, s in sorted(self._salas.items()):
            eq = "⚖ EQUILÍBRIO!" if s["em_equilibrio"] else ""
            print(f"    Sala {sid:2d}: odd={s['odd']:3d}  even={s['even']:3d}  gatilhos={s['gatilhos']}/{MAX_GATILHOS_POR_SALA}  {eq}", flush=True)
