# PISID — Grupo 32 — Documentação da Infraestrutura

## Arquitetura Geral

```
mazerun.exe 32
     │  publica tópicos MQTT (pisid_mazemov_32, pisid_mazetemp_32, pisid_mazesound_32)
     ▼
┌─────────────────────────────────────────────────────────┐
│  PC1                                                    │
│                                                         │
│  [PC1_01_mqtt_to_mongo.py]                              │
│   • Subscreve tópicos do mazerun                        │
│   • Valida dados (anomalias + outliers)                 │
│   • Insere em MongoDB (pisid_grupo32)                   │
│       ├── Movimento   (RoomOrigin, RoomDestiny, Status) │
│       ├── temperatura (Temperature, Hour)               │
│       └── Som         (Sound, Hour)                     │
│                                                         │
│  [PC1_02_mongo_to_mqtt.py]                              │
│   • Lê MongoDB incrementalmente (checkpoint por _id)    │
│   • Publica em tópicos de migração (pisid_mig_*)        │
│   • Intervalo: 0.1s | Lote: 20 docs (normal)           │
│                                                         │
│  Docker: MongoDB Replica Set                            │
│   mongo1 :27017 (primary)                              │
│   mongo2 :27018 (secondary)                            │
│   mongo3 :27019 (secondary)                            │
└─────────────────┬───────────────────────────────────────┘
                  │  MQTT broker.emqx.io (QoS 1)
                  │  tópicos: pisid_mig_mov_32
                  │           pisid_mig_temp_32
                  │           pisid_mig_sound_32
                  ▼
┌─────────────────────────────────────────────────────────┐
│  PC2                                                    │
│                                                         │
│  [PC2_01_mqtt_to_mysql.py]                              │
│   • Subscreve tópicos de migração                       │
│   • Insere em MySQL (labirinto)                         │
│       ├── medicoespassagens                             │
│       ├── temperatura                                   │
│       └── som                                           │
│                                                         │
│  Docker: MySQL 8.0 + PHP + phpMyAdmin                   │
│   MySQL      :3306                                      │
│   PHP/Web    :9000  → http://localhost:9000             │
│   phpMyAdmin :9001  → http://localhost:9001             │
│                                                         │
│  Android App  →  http://<IP_PC2>/maze_app_php/          │
└─────────────────────────────────────────────────────────┘
```

---

## Estrutura de Ficheiros

```
dbdata32/
├── .gitignore
├── INFRASTRUCTURE.md              ← este ficheiro
│
├── PC1/
│   ├── docker-compose.yml         ← MongoDB replica set (3 nós)
│   ├── reset_mongo.bat            ← apaga e reinicia MongoDB
│   ├── mazerun/
│   │   └── mazerun.exe            ← simulador do labirinto
│   └── Python/
│       ├── PC1_01_mqtt_to_mongo.py  ← MQTT → MongoDB (Fase A)
│       ├── PC1_02_mongo_to_mqtt.py  ← MongoDB → MQTT (Fase B, parte 1)
│       └── requirements.txt
│
└── PC2/
    ├── docker-compose.yml         ← MySQL + PHP + phpMyAdmin
    ├── Dockerfile                 ← imagem PHP
    ├── reset_bd.bat               ← apaga e reinicia MySQL
    ├── mysql_files/
    │   ├── labirinto.sql          ← schema (auto-executado pelo Docker)
    │   └── patch_grupo32.sql      ← SPs + Trigger + Users (executar 1x manualmente)
    ├── Python/
    │   ├── PC2_01_mqtt_to_mysql.py  ← MQTT → MySQL (Fase B, parte 2)
    │   └── requirements.txt
    ├── src/                       ← pasta web (montada em /var/www/html)
    │   ├── index.html             ← web app (login, simulações, dashboard, alertas)
    │   ├── db.php                 ← ligação MySQL (host:mysql, pass:root)
    │   ├── api_simulacoes.php
    │   ├── api_utilizadores.php
    │   ├── api_alertas.php
    │   ├── api_dashboard.php
    │   ├── api_config.php
    │   ├── api_procedures.php
    │   └── maze_app_php/          ← PHP para Android
    │       ├── login.php
    │       ├── get_temperature_data.php
    │       ├── get_sound_data.php
    │       ├── get_room_data.php
    │       ├── get_messages.php
    │       ├── get_min_max_temp_values.php
    │       ├── get_max_sound_value.php
    │       ├── criar_utilizador.php
    │       ├── alterar_utilizador.php
    │       ├── remover_utilizador.php
    │       ├── criar_jogo.php
    │       └── alterar_jogo.php
    └── android/                   ← projeto Android Studio
        └── app/src/main/java/com/maze/
```

> ⚠️ A pasta `mysql_data/` é gerada pelo Docker e está no `.gitignore`. Nunca commitar.

---

## Instalação de Raiz — PC1

### Pré-requisitos
- Docker Desktop
- Python 3.10+
- `pip install -r Python/requirements.txt`

### 1. Arrancar MongoDB
```powershell
cd PC1
docker-compose up -d
# Aguarda ~30s para o replica set inicializar
```

### 2. Verificar replica set (opcional)
```powershell
docker exec mongo1 mongosh --quiet --eval "rs.status().members.forEach(m => print(m.name, m.stateStr))"
# Deve mostrar: mongo1:27017 PRIMARY
```

### 3. Arrancar os scripts Python (3 janelas separadas)

**Janela 1 — mazerun (simulador)**
```powershell
cd PC1\mazerun
.\mazerun.exe 32 --flagMessage 1
```

**Janela 2 — MQTT → MongoDB**
```powershell
cd PC1\Python
python PC1_01_mqtt_to_mongo.py 32
```

**Janela 3 — MongoDB → MQTT**
```powershell
cd PC1\Python
python PC1_02_mongo_to_mqtt.py 32
```

---

## Instalação de Raiz — PC2

### Pré-requisitos
- Docker Desktop
- Python 3.10+
- `pip install -r Python/requirements.txt`
- Android Studio (para a app Android)

### 1. Arrancar MySQL + PHP
```powershell
cd PC2
docker-compose up -d
# Aguarda ~30s para o MySQL inicializar
```

### 2. Configurar a base de dados (apenas na primeira vez)

O `labirinto.sql` cria as tabelas automaticamente ao arrancar.  
Depois, correr o patch manualmente:

1. Abrir **phpMyAdmin**: http://localhost:9001  
   - Servidor: `mysql` | Utilizador: `root` | Password: `root`
2. Selecionar a BD `labirinto` → separador **SQL**
3. Colar o conteúdo de `mysql_files/patch_grupo32.sql` → **Executar**

O resultado final deve mostrar: **11 tabelas, 5 procedures, 1 trigger, 2 users**

### 3. Arrancar o script Python

```powershell
cd PC2\Python
python PC2_01_mqtt_to_mysql.py 32
```

### 4. Web App
Abrir no browser: **http://localhost:9000**

### 5. Android App
- Abrir Android Studio → `File > Open` → pasta `PC2/android`
- Sync Gradle
- No ecrã de login da app:
  - **Host**: `<IP_do_PC2>:9000`
  - **Username**: `admin@iscte-ul.pt`
  - **Password**: `root`
  - **Database**: `labirinto`

---

## Reset Completo

**PC1 — apagar MongoDB e recomeçar:**
```powershell
cd PC1
reset_mongo.bat
# Depois apagar os checkpoints:
del Python\mongo_mqtt_checkpoint.json
```

**PC2 — apagar MySQL e recomeçar:**
```powershell
cd PC2
reset_bd.bat
# Após reiniciar, correr patch_grupo32.sql no phpMyAdmin
```

---

## Credenciais

| Serviço | URL | User | Password |
|---|---|---|---|
| phpMyAdmin | http://localhost:9001 | root | root |
| MySQL (direto) | localhost:3306 | root | root |
| Web App | http://localhost:9000 | admin@iscte-ul.pt | root |
| MongoDB primary | localhost:27017 | — | — |

### Utilizadores MySQL da app

| User MySQL | Password | Permissões |
|---|---|---|
| `admin_app` | `admin_pw` | CRUD + todas as SPs |
| `user_app` | `user_pw` | SELECT + Alterar/Criar jogo |

---

## Base de Dados MongoDB

- **BD**: `pisid_grupo32`
- **Coleções**: `Movimento`, `temperatura`, `Som`
- **Checkpoint** (gerado em runtime): `Python/mongo_mqtt_checkpoint.json`

## Base de Dados MySQL

- **BD**: `labirinto`
- **Tabelas principais**: `medicoespassagens`, `temperatura`, `som`, `mensagens`, `ocupacaolabirinto`
- **Trigger**: `trg_temperatura_alerta` — insere em `mensagens` quando temperatura > 59ºC
- **IDSimulacao** usado pelos scripts Python: `1`

---

## Tópicos MQTT

| Tópico | Direção | Conteúdo |
|---|---|---|
| `pisid_mazemov_32` | mazerun → PC1_01 | movimentos dos marsamis |
| `pisid_mazetemp_32` | mazerun → PC1_01 | leituras de temperatura |
| `pisid_mazesound_32` | mazerun → PC1_01 | leituras de som |
| `pisid_mig_mov_32` | PC1_02 → PC2_01 | migração movimentos |
| `pisid_mig_temp_32` | PC1_02 → PC2_01 | migração temperatura |
| `pisid_mig_sound_32` | PC1_02 → PC2_01 | migração som |
