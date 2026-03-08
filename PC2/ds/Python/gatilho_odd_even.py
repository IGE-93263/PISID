"""
Lógica dos gatilhos odd/even.

Regras do enunciado:
  - Marsami odd  = ID ímpar  (ex: 1, 3, 5, ...)
  - Marsami even = ID par    (ex: 2, 4, 6, ...)
  - Quando numa sala o nº de odds == nº de evens (e ambos > 0) → acionar gatilho
  - Gatilho enviado via MQTT: {Type: Score, Player: <grupo>, Room: <sala>}
  - Máximo 3 gatilhos por sala por simulação
  - Após acionar, não aciona de novo para a mesma sala até o equilíbrio se desfazer
    e voltar a verificar-se (evita spam de gatilhos)

Uso:
    from gatilho_odd_even import GatilhoOddEven

    tracker = GatilhoOddEven(grupo=19, mqtt_client=c)
    tracker.processar_movimento(msg_dict)
"""

import json


MAX_GATILHOS_POR_SALA = 3


class GatilhoOddEven:

    def __init__(self, grupo: int, mqtt_client):
        self.grupo       = grupo
        self.mqtt        = mqtt_client

        # Estado: {sala_id: {"odd": int, "even": int}}
        self._salas: dict = {}

        # Contagem de gatilhos disparados por sala: {sala_id: int}
        self._gatilhos_disparados: dict = {}

        # Controlo de equilíbrio: evita disparar múltiplos gatilhos
        # enquanto o equilíbrio se mantém. Só dispara novamente após
        # o equilíbrio se desfazer e reaparecer.
        # {sala_id: bool}  True = estava em equilíbrio no ciclo anterior
        self._em_equilibrio: dict = {}

    def _sala(self, sala_id: int) -> dict:
        if sala_id not in self._salas:
            self._salas[sala_id] = {"odd": 0, "even": 0}
        return self._salas[sala_id]

    def _is_odd(self, marsami_id: int) -> bool:
        return marsami_id % 2 != 0

    def processar_movimento(self, msg: dict):
        """
        Processa uma mensagem de movimento do MongoDB/MQTT.

        Formato esperado:
          {Player, Marsami, RoomOrigin, RoomDestiny, Status}

        RoomOrigin == 0  → largada inicial (marsami colocado em RoomDestiny)
        RoomOrigin == 0 e RoomDestiny == 0 → marsami preso/cansado (ignorar)
        Status == 2      → cansaço (marsami para, mas já está na última sala)
        """
        marsami_id  = msg.get("Marsami")
        origem      = msg.get("RoomOrigin", 0)
        destino     = msg.get("RoomDestiny", 0)
        status      = msg.get("Status", 1)

        if marsami_id is None:
            return

        tipo = "odd" if self._is_odd(marsami_id) else "even"

        # Caso: marsami preso (ambos 0) — sem movimento real
        if origem == 0 and destino == 0:
            return

        # Caso: largada inicial — marsami colocado em destino
        if origem == 0:
            self._sala(destino)[tipo] += 1
            self._verificar_gatilho(destino)
            return

        # Caso: movimento normal — sai de origem, entra em destino
        sala_orig = self._sala(origem)
        sala_orig[tipo] = max(0, sala_orig[tipo] - 1)
        self._verificar_equilibrio_quebrado(origem)

        self._sala(destino)[tipo] += 1
        # Ao entrar num destino, se havia equilíbrio registado mas os números
        # entretanto mudaram (ex: outro marsami saiu), reseta o flag
        sala_dest = self._sala(destino)
        if self._em_equilibrio.get(destino, False):
            if sala_dest["odd"] != sala_dest["even"]:
                self._em_equilibrio[destino] = False
        self._verificar_gatilho(destino)

    def _verificar_equilibrio_quebrado(self, sala_id: int):
        """Marca que o equilíbrio se desfez nesta sala (permite novo gatilho)."""
        sala = self._sala(sala_id)
        # Após qualquer saída de marsami, re-avalia o estado de equilíbrio.
        # Se odd != even, o equilíbrio quebrou → permite disparar novamente.
        # Se odd == even ainda, mantém o estado atual (não reseta desnecessariamente).
        if sala["odd"] != sala["even"]:
            if self._em_equilibrio.get(sala_id, False):
                print(f"  [DEBUG odd/even] Sala {sala_id}: equilíbrio desfeito ({sala['odd']} odd vs {sala['even']} even)")
            self._em_equilibrio[sala_id] = False

    def _verificar_gatilho(self, sala_id: int):
        """Verifica se deve acionar o gatilho nesta sala."""
        sala = self._sala(sala_id)
        odd  = sala["odd"]
        even = sala["even"]

        # Condição: odd == even e ambos > 0
        if odd != even or odd == 0:
            self._em_equilibrio[sala_id] = False
            return

        # Já estava em equilíbrio? Não disparar de novo
        if self._em_equilibrio.get(sala_id, False):
            return

        # Verificar limite de 3 gatilhos por sala
        disparados = self._gatilhos_disparados.get(sala_id, 0)
        if disparados >= MAX_GATILHOS_POR_SALA:
            print(f"  [GATILHO] Sala {sala_id}: limite de {MAX_GATILHOS_POR_SALA} atingido, ignorado.")
            return

        # Disparar gatilho
        self._acionar_gatilho(sala_id, odd)
        self._gatilhos_disparados[sala_id] = disparados + 1
        self._em_equilibrio[sala_id] = True

    def _acionar_gatilho(self, sala_id: int, contagem: int):
        """Envia mensagem MQTT de Score."""
        payload = json.dumps({
            "Type":   "Score",
            "Player": self.grupo,
            "Room":   sala_id,
        })
        try:
            self.mqtt.publish("pisid_mazeact", payload)
            disparados = self._gatilhos_disparados.get(sala_id, 0) + 1
            print(
                f"  [GATILHO] Sala {sala_id}: odd={contagem} == even={contagem} "
                f"→ Score enviado! ({disparados}/{MAX_GATILHOS_POR_SALA})"
            )
        except Exception as e:
            print(f"  [GATILHO] Erro ao enviar Score para sala {sala_id}: {e}")

    def estado(self) -> dict:
        """Devolve o estado atual de todas as salas (útil para debug)."""
        return {
            sala: {
                **contagens,
                "gatilhos": self._gatilhos_disparados.get(sala, 0),
            }
            for sala, contagens in self._salas.items()
        }

    def imprimir_estado(self):
        """Imprime o estado atual de todas as salas no terminal."""
        if not self._salas:
            print("  [DEBUG odd/even] Nenhum movimento processado ainda.")
            return
        print("  [DEBUG odd/even] Estado das salas:")
        for sala_id in sorted(self._salas):
            s = self._salas[sala_id]
            odd, even = s["odd"], s["even"]
            gatilhos = self._gatilhos_disparados.get(sala_id, 0)
            equilibrio = "⚖ EQUILIBRIO!" if odd == even and odd > 0 else ""
            print(f"    Sala {sala_id:>2}: odd={odd:>3}  even={even:>3}  gatilhos={gatilhos}/{MAX_GATILHOS_POR_SALA}  {equilibrio}")
