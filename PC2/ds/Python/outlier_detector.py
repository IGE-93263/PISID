"""
Deteção de outliers e dados "sujos" para sensores de temperatura e som.

Estratégia em duas camadas:
  1. Validação básica      — valores nulos, tipo errado, fora de intervalo físico absoluto
  2. Deteção estatística   — z-score numa janela deslizante dos últimos N valores,
                             só ativa após JANELA_MIN leituras (evita falsos positivos no arranque)

Os limites físicos e parâmetros estatísticos estão na secção CONFIGURAÇÃO abaixo.
"""

from collections import deque
import math

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

# Limites físicos absolutos — valores fora destes são sempre rejeitados
TEMP_MIN    = -50.0   # temperatura mínima admissível
TEMP_MAX    =  150.0  # temperatura máxima admissível
SOM_MIN     =   0.0   # som mínimo admissível
SOM_MAX     = 200.0   # som máximo admissível

# Parâmetros do z-score
JANELA      = 50      # tamanho da janela deslizante (últimas N leituras)
JANELA_MIN  = 20      # só começa a rejeitar após ter pelo menos N leituras acumuladas
                      # (evita falsos positivos no arranque quando há poucos dados)
Z_THRESHOLD = 4.5     # limiar de rejeição: |z| > threshold -> outlier
                      # 3.0 = agressivo | 4.5 = conservador | 5.0+ = só casos extremos


# ─── MOTOR ESTATÍSTICO ────────────────────────────────────────────────────────

class JanelaEstatistica:
    """Janela deslizante com deteção de outliers por z-score."""

    def __init__(self, maxlen=JANELA, min_amostras=JANELA_MIN, threshold=Z_THRESHOLD):
        self._buf        = deque(maxlen=maxlen)
        self._min        = min_amostras
        self._threshold  = threshold

    def _stats(self):
        n = len(self._buf)
        if n < self._min:
            return None, None
        media = sum(self._buf) / n
        variancia = sum((x - media) ** 2 for x in self._buf) / (n - 1)
        return media, math.sqrt(variancia)

    def is_outlier(self, valor):
        """
        Verifica se o valor é estatisticamente anómalo.
        O valor é sempre adicionado à janela, mesmo que seja outlier,
        para manter a distribuição representativa da série real.
        """
        media, desvio = self._stats()
        self._buf.append(valor)

        if media is None:
            return False   # ainda a acumular amostras minimas - nao rejeitar
        if desvio < 1e-9:
            return False   # sem variancia (todos iguais) - nao e possivel calcular z

        return abs(valor - media) / desvio > self._threshold


# Janelas independentes por tipo de sensor
_janela_temperatura = JanelaEstatistica()
_janela_som         = JanelaEstatistica()


# ─── API PÚBLICA ──────────────────────────────────────────────────────────────

def _parse_float(valor):
    """Converte para float ou devolve None se invalido/nulo."""
    if valor is None:
        return None
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def validar_temperatura(raw):
    """
    Valida um valor de temperatura vindo do MongoDB.

    Retorna:
      (float, None)       - valor valido, pronto a inserir no MySQL
      (None,  "motivo")   - valor rejeitado, com descricao do motivo
    """
    v = _parse_float(raw)
    if v is None:
        return None, f"valor nao numerico ou nulo: {raw!r}"
    if not (TEMP_MIN <= v <= TEMP_MAX):
        return None, f"fora do intervalo fisico [{TEMP_MIN}, {TEMP_MAX}]: {v}"
    if _janela_temperatura.is_outlier(v):
        return None, f"outlier estatistico (|z| > {Z_THRESHOLD}): {v}"
    return v, None


def validar_som(raw):
    """
    Valida um valor de som/ruido vindo do MongoDB.

    Retorna:
      (float, None)       - valor valido, pronto a inserir no MySQL
      (None,  "motivo")   - valor rejeitado, com descricao do motivo
    """
    v = _parse_float(raw)
    if v is None:
        return None, f"valor nao numerico ou nulo: {raw!r}"
    if not (SOM_MIN <= v <= SOM_MAX):
        return None, f"fora do intervalo fisico [{SOM_MIN}, {SOM_MAX}]: {v}"
    if _janela_som.is_outlier(v):
        return None, f"outlier estatistico (|z| > {Z_THRESHOLD}): {v}"
    return v, None
