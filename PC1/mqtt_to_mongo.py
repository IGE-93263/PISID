import json
import paho.mqtt.client as mqtt
from pymongo import MongoClient
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES MONGODB
# ==========================================
MONGO_URI = "mongodb://127.0.0.1:27017/?directConnection=true"
cliente_mongo = MongoClient(MONGO_URI)
db = cliente_mongo["labirinto"]
col_movimentos = db["movimentos"]
col_temperatura = db["temperatura"]
col_ruido = db["ruido"]

# ==========================================
# 2. CONFIGURAÇÕES MQTT
# ==========================================
NUMERO_EQUIPA = 19  # Ajustado para a tua equipa do log

TOPICO_SOM = f"pisid_mazesound_{NUMERO_EQUIPA}"
TOPICO_TEMP = f"pisid_mazetemp_{NUMERO_EQUIPA}"
TOPICO_MOV = f"pisid_mazemov_{NUMERO_EQUIPA}"

# NOTA: No teu log, o simulador ligou-se a "broker.emqx.io". Vamos usar o mesmo!
BROKER = "broker.emqx.io" 
PORTA = 1883

def on_connect(client, userdata, flags, rc):
    print(f"✅ Ligado ao Broker {BROKER}!")
    client.subscribe([(TOPICO_SOM, 0), (TOPICO_TEMP, 0), (TOPICO_MOV, 0)])
    print(f"🎧 À escuta da equipa {NUMERO_EQUIPA}...\n")

def on_message(client, userdata, msg):
    topico = msg.topic
    payload_sujo = msg.payload.decode('utf-8')
    
    try:
        # LIMPEZA DOS DADOS: Encontrar onde acaba o JSON (a última '}')
        fim_json = payload_sujo.rfind('}')
        if fim_json != -1:
            # Cortar a "sujidade" (ex: " - topic pisid_mazesound_19")
            payload_limpo = payload_sujo[:fim_json + 1] 
        else:
            payload_limpo = payload_sujo # Se não tiver '}', assume que está tudo bem

        # Agora sim, converte o texto limpo para JSON Python
        dados = json.loads(payload_limpo)
        
        # Adiciona a HORA REAL em que a mensagem chegou ao nosso PC
        # (Para nos protegermos das datas falsas "2025-05-32" do simulador)
        dados['HoraRecepcao'] = datetime.now()

        # Inserir na base de dados certa
        if topico == TOPICO_MOV:
            col_movimentos.insert_one(dados)
            print(f"🏃 [MOVIMENTO] Marsami {dados.get('Marsami')} da Sala {dados.get('RoomOrigin')} para a {dados.get('RoomDestiny')} (Status: {dados.get('Status')})")
            
        elif topico == TOPICO_TEMP:
            col_temperatura.insert_one(dados)
            print(f"🌡️ [TEMPERATURA] Registado: {dados.get('Temperature')}")
            
        elif topico == TOPICO_SOM:
            col_ruido.insert_one(dados)
            print(f"🔊 [RUÍDO] Registado: {dados.get('Sound')}")

    except Exception as e:
        print(f"⚠️ Erro ao processar mensagem! Ignorada: {payload_sujo}")
        print(f"Detalhe: {e}")

# Iniciar o ouvinte MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"A tentar ligar a {BROKER}...")
client.connect(BROKER, PORTA, 60)
client.loop_forever()