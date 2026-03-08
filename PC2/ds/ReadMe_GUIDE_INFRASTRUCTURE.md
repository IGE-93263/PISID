# 🏗️ Documentação da Infraestrutura do Projeto

Este documento explica como levantar e gerir a infraestrutura local do projeto, que inclui serviços de **PHP**, **MySQL** e um **cluster MongoDB** em Replica Set.

> **Ficheiros principais:** `docker-compose.yml` · `reset_bd.bat`

---

## ⚡ Arranque Rápido

```bash
docker-compose up -d
```

Isto é tudo o que precisas para a primeira vez. O Docker trata de:
- Criar a base de dados `labirinto` automaticamente
- Importar o ficheiro `labirinto.sql` com todas as tabelas
- Configurar o cluster MongoDB

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

## 🔄 Reset da Base de Dados — `reset_bd.bat`

> **Quando usar:** sempre que precisares de apagar tudo e reimportar o `labirinto.sql` do zero (ex: após alterações ao schema ou dados corrompidos).

O Docker só importa o `labirinto.sql` **na primeira vez** que a base de dados é criada. Este script simula uma "instalação nova" ao apagar o histórico físico.

### Como executar

Faz duplo clique no `reset_bd.bat` ou corre no terminal:

```cmd
.\reset_bd.bat
```

### O que o script faz (passo a passo)

```bat
docker-compose down          ← Para e remove todos os contentores
rmdir /s /q .\mysql_data     ← Apaga a pasta com os dados do MySQL
mkdir .\mysql_data            ← Recria a pasta vazia
docker-compose up -d         ← Reinicia tudo; MySQL reimporta o labirinto.sql e labirinto_preencher.sql
```

> ⚠️ **Atenção:** Este processo **apaga todos os dados** da base de dados MySQL. Faz backup antes se necessário.

---

## 🐳 Infraestrutura — `docker-compose.yml`

### Serviço: `php`

Servidor web que corre o código da aplicação.

```yaml
build: . / Dockerfile     # Imagem construída localmente
volumes: ./src → /var/www/html  # Edita o código e vês as alterações em tempo real
ports: 9000:80
depends_on: mysql         # MySQL arranca antes do PHP
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
| `./mysql_files/labirinto_preencher.sql` | `/docker-entrypoint-initdb.d/labirinto_preencher.sql` | **Insere os dados iniciais após criar as tabelas (executa 2.º)** |

> 💡 A pasta `/docker-entrypoint-initdb.d/` executa os ficheiros por **ordem alfabética**, o que garante que `labirinto.sql` (schema) é sempre executado antes de `labirinto_preencher.sql` (dados).

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

**Fluxo de execução:**
1. Aguarda 20 segundos (para os três nós estarem prontos)
2. Liga ao `mongo1` e executa `rs.initiate()` com as prioridades definidas
3. Aguarda a eleição do Primary
4. Imprime o status dos membros
5. Se o cluster já estiver configurado (`AlreadyInitialized`), deteta isso sem erros e mostra o status atual

---

## 📁 Estrutura de Pastas Esperada

```
projeto/
├── docker-compose.yml
├── reset_bd.bat
├── Dockerfile
├── src/                    ← Código PHP da aplicação
├── mysql_data/             ← Dados do MySQL (gerido pelo Docker)
└── mysql_files/
    ├── labirinto.sql           ← Schema: cria as tabelas (executa 1.º)
    └── labirinto_preencher.sql ← Dados: preenche as tabelas (executa 2.º)
```

---

# 🔁 Teste do Fluxo Completo: MQTT → MongoDB → MySQL

## Pré-requisitos

1. **MongoDB** (3 réplicas no Docker)
2. **MySQL** (Docker ou local) com base `labirinto`
3. **Schema e seed** em MySQL — o `docker-compose.yml` faz isto automaticamente no primeiro arranque via:
   - `labirinto.sql` — cria o schema com FKs (executa 1.º)
   - `labirinto_preencher.sql` — insere dados mínimos: equipa 19, salas 0–10, utilizador, simulacao 1 (executa 2.º)

4. **Ficheiro `db_mysql.py`** — deve estar na mesma pasta que `mongo_to_mysql.py` com as credenciais de ligação ao MySQL:

```python
import os
import mysql.connector

MYSQL_CONFIG = {
    "host":     os.environ.get("MYSQL_HOST",     "localhost"),
    "user":     os.environ.get("MYSQL_USER",     "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "root"),
    "database": os.environ.get("MYSQL_DATABASE", "labirinto"),
    "port":     int(os.environ.get("MYSQL_PORT", 3306)),
}

def get_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)
```

   > 💡 Os valores `root` já estão definidos por defeito — não precisas de definir variáveis de ambiente.
   > Se quiseres sobrepor, podes fazê-lo assim:

   **Windows (CMD):**
   ```cmd
   set MYSQL_HOST=localhost
   set MYSQL_USER=root
   set MYSQL_PASSWORD=root
   set MYSQL_DATABASE=labirinto
   ```

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

   > ⚠️ Estas variáveis são **temporárias** — só existem na janela do terminal onde as correste. Se abrires uma nova janela, tens de as correr novamente.

5. **Dependências:**
```bash
pip install pymongo mysql-connector-python paho-mqtt
```

---

## Passos para Testar

### 1. Ligar a Infraestrutura

```powershell
cd C:\dev\mysqldocker
docker-compose up -d
```

> Aguarda ~30 s para o MySQL inicializar.

### 2. Arrancar os Componentes (em janelas separadas)

```powershell
# Janela 1 — Jogador (MQTT → MongoDB)
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
mongosh --port 27017
> use pisid_grupo19
> db.movimento.countDocuments()
> db.temperatura.countDocuments()
> db.som.countDocuments()
```

**MySQL** — novos registos nas tabelas (via phpMyAdmin em http://localhost:9001 ou terminal):
```sql
USE labirinto;
SELECT COUNT(*) FROM temperatura;
SELECT COUNT(*) FROM som;
SELECT COUNT(*) FROM medicoespassagens;
SELECT * FROM temperatura ORDER BY IDTemperatura DESC LIMIT 5;
```

**Migração** — no terminal do `mongo_to_mysql.py` devem surgir linhas como:
```
Migrados: 15 docs
```

### 4. Teste de Failover MongoDB (opcional)

1. Com tudo a correr, para o `mongo1`: `docker stop mongo1`
2. O `mqtt_to_mongo.py` faz failover automaticamente para `27018` ou `27019`
3. A migração continua a funcionar (lê de qualquer nó disponível)
4. Reinicia o `mongo1`: `docker start mongo1`

---

## Resumo do Fluxo

| Janela | Componente | Função |
|---|---|---|
| 1 | `mqtt_to_mongo.py` | MQTT → MongoDB |
| 2 | `mongo_to_mysql.py` | MongoDB → MySQL (a cada 5 s) |
| 3 | `mazerun.exe` | Publica sensores no MQTT |
