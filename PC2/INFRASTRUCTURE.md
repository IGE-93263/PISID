# 🏗️ Documentação da Infraestrutura do Projeto

Este documento explica como levantar e gerir a infraestrutura local do projeto, que inclui serviços de **PHP**, **MySQL**, um **cluster MongoDB** em Replica Set, e os scripts Python de migração e lógica de jogo.

> **Ficheiros principais:** `docker-compose.yml` · `reset_bd.bat`

---

## ⚡ Arranque Rápido

```bash
docker-compose up -d
```

Isto é tudo o que precisas para a primeira vez. O Docker trata de:
- Criar a base de dados `labirinto` automaticamente
- Importar `labirinto.sql` (schema) e `labirinto_preencher.sql` (dados iniciais)
- Configurar o cluster MongoDB em Replica Set

### Acesso aos Serviços

| Serviço | URL | Credenciais |
|---|---|---|
| Aplicação PHP | http://localhost:9000 | — |
| phpMyAdmin | http://localhost:9001 | Server: `mysql` · User: `root` · Password: `root` |
| MySQL | `localhost:3306` | User: `root` · Password: `root` |
| MongoDB Primary | `localhost:27017` | — |
| MongoDB Secondary | `localhost:27018` | — |
| MongoDB Secondary | `localhost:27019` | — |

---

## 🔄 Reset da Base de Dados MySQL — `reset_bd.bat`

> **Quando usar:** sempre que precisares de apagar tudo e reimportar o schema do zero (ex: após alterações ao schema ou dados corrompidos).

```cmd
.\reset_bd.bat
```

```bat
docker-compose down          ← Para e remove todos os contentores
rmdir /s /q .\mysql_data     ← Apaga a pasta com os dados do MySQL
mkdir .\mysql_data            ← Recria a pasta vazia
docker-compose up -d         ← Reinicia tudo; MySQL reimporta ambos os .sql
```

> ⚠️ **Atenção:** Este processo **apaga todos os dados** da base de dados MySQL. Faz backup antes se necessário.

---


## 🐳 Infraestrutura — `docker-compose.yml`

### Serviço: `php`

Servidor web que corre o código da aplicação.

```yaml
build: . / Dockerfile          # Imagem construída localmente
volumes: ./src → /var/www/html  # Edita o código e vês as alterações em tempo real
ports: 9000:80
depends_on: mysql               # MySQL arranca antes do PHP
```

---

### Serviço: `mysql`

Base de dados relacional principal do projeto.

```yaml
image: mysql:8.0
platform: linux/amd64     # Compatibilidade com Macs Apple Silicon
restart: no
```

**Variáveis de ambiente:**

| Variável | Valor | Função |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | `root` | Password do utilizador root |
| `MYSQL_DATABASE` | `labirinto` | Cria a BD automaticamente no arranque |
| `MYSQL_DEFAULT_AUTHENTICATION_PLUGIN` | `mysql_native_password` | Compatibilidade com PHP |

**Volumes:**

| Volume local | Destino no contentor | Função |
|---|---|---|
| `./mysql_data/` | `/var/lib/mysql` | Persiste os dados entre reinicios |
| `./mysql_files/` | `/var/lib/mysql-files/` | Pasta segura para importar/exportar CSVs |
| `./mysql_files/labirinto.sql` | `/docker-entrypoint-initdb.d/labirinto.sql` | Cria as tabelas no primeiro arranque (executa 1.º) |
| `./mysql_files/labirinto_preencher.sql` | `/docker-entrypoint-initdb.d/labirinto_preencher.sql` | Insere os dados iniciais após criar as tabelas (executa 2.º) |

> 💡 A pasta `/docker-entrypoint-initdb.d/` executa os ficheiros por **ordem alfabética**, garantindo que `labirinto.sql` corre antes de `labirinto_preencher.sql`.

---

### Serviço: `phpmyadmin`

Interface gráfica para gerir o MySQL no browser.

```yaml
image: phpmyadmin:latest
ports: 9001:80
PMA_ARBITRARY: 1    # Permite escolher o servidor no ecrã de login
```

Acede em **http://localhost:9001** e usa `mysql` como Server.

---

### Cluster MongoDB — `mongo1`, `mongo2`, `mongo3`

Três instâncias MongoDB configuradas como **Replica Set** (`rs0`).

| Contentor | Porta externa | Função no cluster |
|---|---|---|
| `mongo1` | `27017` | **Primary** (priority: 2) |
| `mongo2` | `27018` | Secondary (priority: 1) |
| `mongo3` | `27019` | Secondary (priority: 1) |

Todos os nós arrancam com `--replSet rs0 --bind_ip_all`.

---

### Serviço: `mongo-setup`

Contentor temporário que configura o Replica Set automaticamente.

1. Aguarda 20 segundos (para os três nós estarem prontos)
2. Liga ao `mongo1` e executa `rs.initiate()` com as prioridades definidas
3. Aguarda a eleição do Primary e imprime o status dos membros
4. Se o cluster já estiver configurado (`AlreadyInitialized`), deteta isso sem erros

---

## 🐍 Scripts Python — pasta `Python/`

### Dependências

```bash
pip install pymongo mysql-connector-python paho-mqtt
```

### Ficheiros

| Ficheiro | Função |
|---|---|
| `mqtt_to_mongo.py` | Recebe mensagens MQTT e guarda no MongoDB. Inclui failover entre os 3 nós e buffer em ficheiro quando MongoDB está indisponível. |
| `mongo_to_mysql.py` | Migração incremental MongoDB → MySQL a cada 5 segundos. Usa checkpoint para não reprocessar dados. |
| `db_mysql.py` | Configuração da ligação ao MySQL. Lido por `mongo_to_mysql.py`. |
| `outlier_detector.py` | Deteção de outliers e dados sujos nos sensores. |
| `gatilho_odd_even.py` | Lógica dos gatilhos odd/even em tempo real. |

---

### `db_mysql.py` — Credenciais MySQL

Os valores `root` já estão definidos por defeito — não precisas de variáveis de ambiente. Se quiseres sobrepor:

**Windows (PowerShell):**
```powershell
$env:MYSQL_HOST="localhost"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="root"
$env:MYSQL_DATABASE="labirinto"
```

**Mac/Linux:**
```bash
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=root
export MYSQL_DATABASE=labirinto
```

> ⚠️ Variáveis temporárias — só existem na janela do terminal atual.

---

### `outlier_detector.py` — Deteção de Dados Sujos

Validação em duas camadas antes de inserir no MySQL:

**1. Validação física** — rejeita imediatamente valores fora dos limites:

| Sensor | Mínimo | Máximo |
|---|---|---|
| Temperatura | -50.0 | 150.0 |
| Som | 0.0 | 200.0 |

**2. Z-score estatístico** — janela deslizante das últimas 50 leituras:
- Só ativa após acumular **20 leituras** (evita falsos positivos no arranque)
- Rejeita valores com `|z| > 4.5`

Quando um valor é rejeitado, aparece no terminal:
```
[OUTLIER temperatura] rejeitado — outlier estatístico (|z| > 4.5): 999.0
Temperatura: 4 inseridos, 1 rejeitados (outliers/dados sujos)
```

---

### `gatilho_odd_even.py` — Lógica dos Gatilhos

Rastreia em tempo real quantos marsamis **odd** (ID ímpar) e **even** (ID par) estão em cada sala.

**Regras:**
- Quando `odd == even > 0` numa sala → envia gatilho via MQTT: `{Type: Score, Player: 19, Room: X}`
- Máximo **3 gatilhos por sala** por simulação
- Só dispara novamente após o equilíbrio se desfazer e reaparecer

**Output no terminal (Janela 1 — `mqtt_to_mongo.py`):**
```
Tracker odd/even ativo (max 3 gatilhos/sala)
  [GATILHO] Sala 3: odd=2 == even=2 → Score enviado! (1/3)
  [DEBUG odd/even] Estado das salas:
    Sala  3: odd=  2  even=  2  gatilhos=1/3  ⚖ EQUILIBRIO!
    Sala  5: odd=  4  even=  1  gatilhos=0/3
```

O estado das salas é impresso a cada **15 segundos** para monitorização.

---

## 🔁 Teste do Fluxo Completo: MQTT → MongoDB → MySQL

### 1. Ligar a Infraestrutura

```powershell
cd C:\dev\mysqldocker
docker-compose up -d
```

> Aguarda ~30 s para o MySQL inicializar.

### 2. Arrancar os Componentes (em janelas separadas)

```powershell
# Janela 1 — Jogador (MQTT → MongoDB + gatilhos odd/even)
cd C:\Users\PC\Desktop\PISID\jogador
python mqtt_to_mongo.py 19

# Janela 2 — Migração (MongoDB → MySQL)
cd C:\Users\PC\Desktop\PISID\jogador
python mongo_to_mysql.py 19

# Janela 3 — Simulador
cd C:\Users\PC\Desktop\PISID\mazerun
.\mazerun.exe 19 --flagMessage 1
```

> **Ordem:** arranca as janelas 1 e 2 primeiro, depois a 3.

### 3. Verificar o Fluxo

**MongoDB** — novos documentos nas coleções:
```powershell
docker exec mongo1 mongosh pisid_grupo19 --quiet --eval "
  print('movimento: ' + db.movimento.countDocuments());
  print('temperatura: ' + db.temperatura.countDocuments());
  print('som: ' + db.som.countDocuments());
"
```

**MySQL** — novos registos nas tabelas (via phpMyAdmin em http://localhost:9001):
```sql
USE labirinto;
SELECT COUNT(*) FROM temperatura;
SELECT COUNT(*) FROM som;
SELECT COUNT(*) FROM medicoespassagens;
SELECT * FROM temperatura ORDER BY IDTemperatura DESC LIMIT 5;
```

### 4. Teste de Failover MongoDB (opcional)

```powershell
docker stop mongo1   # Para o nó primário
# mqtt_to_mongo.py faz failover automático para 27018 ou 27019
docker start mongo1  # Reinicia o nó
```

---

## 📁 Estrutura de Pastas

```
projeto/
├── docker-compose.yml
├── reset_bd.bat                    ← Reset completo MySQL
├── Dockerfile
├── src/                            ← Código PHP da aplicação
├── mysql_data/                     ← Dados do MySQL (gerido pelo Docker)
├── mysql_files/
│   ├── labirinto.sql               ← Schema: cria as tabelas (executa 1.º)
│   └── labirinto_preencher.sql     ← Dados: preenche as tabelas (executa 2.º)
└── Python/
    ├── mqtt_to_mongo.py            ← MQTT → MongoDB + gatilhos odd/even
    ├── mongo_to_mysql.py           ← MongoDB → MySQL (migração incremental)
    ├── db_mysql.py                 ← Configuração da ligação MySQL
    ├── outlier_detector.py         ← Deteção de outliers/dados sujos
    └── gatilho_odd_even.py         ← Lógica dos gatilhos odd/even
```
