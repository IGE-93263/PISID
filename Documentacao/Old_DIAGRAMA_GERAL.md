# Diagrama Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MAZERUN (Simulador)                                  │
│                         Publica sensores e posições via MQTT                      │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        │  broker.emqx.io:1883
                                        │  pisid_mazemov_19 | mazetemp_19 | mazesound_19
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            mqtt_to_db.py (Jogador)                              │
│  • Subscreve MQTT                                                               │
│  • Prioridade MongoDB: 27017 → 27018 → 27019                                    │
│  • Write concern majority + retry + fila fallback                               │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        │  insert
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MongoDB Replica Set (3 nós)                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                         │
│  │ mongo1:27017 │   │ mongo2:27018 │   │ mongo3:27019 │                         │
│  │  primário    │◄──┤ secundário   │◄──┤ secundário   │  replicação automática  │
│  └──────────────┘   └──────────────┘   └──────────────┘                         │
│         │                    │                    │                             │
│         └────────────────────┴────────────────────┘                             │
│                              base: pisid_grupo19                                │
│                    coleções: movimento | temperatura | som                      │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        │  migração incremental (checkpoint)
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          mongo_to_mysql.py                                      │
│  • Lê docs novos (_id > checpoint)                                              │
│  • Insere em MySQL                                                              │
│  • Atualiza checkpoint  json                                                    │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        │  INSERT
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MySQL (labirinto)                                  │
│  medicoespassagens | temperatura | som | equipa | sala | utilizador | ...       │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Ferramentas de teste                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  mqtt_capture.py      → grava todas as mensagens MQTT em mqtt_capture.json      │
│  verify_mqtt_mongo.py → compara mqtt_capture.json com documentos no MongoDB     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Fluxo de dados

```
mazerun  ──MQTT──►  mqtt_to_db  ──►  MongoDB  ──migração──►  MySQL
```
