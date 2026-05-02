# 🏗️ Documentação da Infraestrutura do Projeto

Este documento explica como levantar e gerir a infraestrutura local do projeto, que inclui serviços de **PHP**, **MySQL**, um **cluster MongoDB** em Replica Set, e os scripts Python de migração e lógica de jogo.

> **Ficheiros principais:** `docker-compose.yml` · `reset_bd.bat` · `ver_ip_pc1.bat`

---

## ⚡ Arranque Rápido

```bash
docker-compose up -d
```

Isto é tudo o que precisas para a primeira vez. O Docker trata de:
- Criar a base de dados `labirinto` automaticamente
- Importar `labirinto.sql` (schema) e `labirinto_preencher.sql` (dados iniciais)
- Configurar o cluster MongoDB em Replica Set

> 💡 Na **primeira vez**, executa também o `labirinto_patch.sql` no phpMyAdmin para adicionar as tabelas e colunas extras necessárias.

### Acesso aos Serviços

| Serviço | URL | Credenciais |
|---|---|---|
| Aplicação PHP | http://localhost:9000 | Email: `grupo19@labirinto.pt` · Password: `grupo19` |
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

> ⚠️ **Atenção:** Este processo **apaga todos os dados** da base de dados MySQL. Depois do reset, volta a executar o `labirinto_patch.sql` no phpMyAdmin.

---

## 🗃️ Ficheiros SQL — pasta `mysql_files/`

| Ficheiro | Quando executar | Função |
|---|---|---|
| `labirinto.sql` | Automático (Docker) | Cria todas as tabelas do schema |
| `labirinto_preencher.sql` | Automático (Docker) | Insere dados iniciais (equipa, salas, utilizador, simulação) |
| `labirinto_patch.sql` | **Manual** (phpMyAdmin) | Adiciona o que falta para PHP e Android funcionarem |

### O que faz o `labirinto_patch.sql`

- Adiciona `AUTO_INCREMENT` à tabela `simulacao`
- Adiciona coluna `Password` à tabela `utilizador` e define credenciais do utilizador de teste
- Cria tabela `configtemp` (limites de temperatura para o Android)
- Cria tabela `configsound` (limite de som para o Android)
- Inicializa `ocupacaolabirinto` com 0 marsamis para as salas 0–10
- Cria **3 triggers MySQL** automáticos (ver secção abaixo)

---

## ⚙️ Triggers MySQL

Os triggers disparam automaticamente — não precisas de alterar nenhum script Python para eles funcionarem.

### `trg_atualizar_ocupacao`

Dispara após cada `INSERT` em `medicoespassagens` (feito pelo `mongo_to_mysql.py`).

```
INSERT medicoespassagens (SalaOrigem=2, SalaDestino=5, Marsami=3)
        ↓ trigger automático
ocupacaolabirinto sala 5: NumeroMarsamisOdd  + 1   (Marsami 3 é ímpar)
ocupacaolabirinto sala 2: NumeroMarsamisOdd  - 1   (mínimo 0)
```

- `Marsami % 2 = 0` → Even · `Marsami % 2 != 0` → Odd
- Sala de origem 0 (spawn) é ignorada no decremento

### `trg_alerta_temperatura`

Dispara após cada `INSERT` em `temperatura`. Compara com os limites em `configtemp`.

```
INSERT temperatura (valor=85.0)  →  maximo=60  →  INSERT mensagens (TipoAlerta='Alerta')
```

### `trg_alerta_som`

Dispara após cada `INSERT` em `som`. Compara com o limite em `configsound`.

```
INSERT som (valor=75.0)  →  maximo=60  →  INSERT mensagens (TipoAlerta='Alerta')
```

---

## 🐍 Scripts Python — pasta `Python/`

### Dependências

```bash
pip install pymongo mysql-connector-python paho-mqtt
```

### Ficheiros

| Ficheiro | PC | Função |
|---|---|---|
| `mqtt_to_mongo.py` | PC1 | Recebe mensagens MQTT e guarda no MongoDB. Failover entre os 3 nós. Lança gatilhos odd/even e atuadores. |
| `mongo_to_mysql.py` | PC2 | Migração incremental MongoDB → MySQL a cada 5 s. Deteta outliers. |
| `db_mysql.py` | PC2 | Configuração da ligação ao MySQL (lido por `mongo_to_mysql.py`). |
| `outlier_detector.py` | PC2 | Deteção de outliers estatísticos (z-score) nos sensores. |
| `gatilho_odd_even.py` | PC1 | Rastreia marsamis odd/even por sala em tempo real. |
| `atuadores.py` | PC1 | Envia comandos automáticos via MQTT (AC, corredores) com base nos sensores. |

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

Quando um valor é rejeitado pelo Python, é inserida uma mensagem em `mensagens` com `TipoAlerta = 'Outlier'`. Os alertas de limites configurados ficam a cargo dos triggers MySQL (`TipoAlerta = 'Alerta'`).

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

### `atuadores.py` — Atuadores Automáticos

Monitoriza os sensores em tempo real e publica comandos no tópico `pisid_mazeact_19`.

| Evento | Condição | Comando enviado |
|---|---|---|
| Temperatura recebida | valor > máximo (`configtemp`) | `TurnOnAC` → sala |
| Temperatura recebida | valor ≤ máximo e AC estava ligado | `TurnOffAC` → sala |
| Som recebido | valor > máximo (`configsound`) | `CloseGate` → corredor de entrada |

**Formato das mensagens publicadas:**
```json
{ "Type": "TurnOnAC",   "Player": 19, "Room": 3 }
{ "Type": "TurnOffAC",  "Player": 19, "Room": 3 }
{ "Type": "CloseGate",  "Player": 19, "RoomOrigin": 2, "RoomDestination": 3 }
```

**Comportamento:**
- Os limites são lidos de `configtemp` / `configsound` no MySQL e **recarregados a cada 60 s** — podes alterar os limites no phpMyAdmin durante a simulação sem reiniciar nada
- O AC liga/desliga automaticamente conforme a temperatura sobe e desce
- O corredor **não reabre automaticamente** após o som baixar (evita oscilações)
- Se `atuadores.py` não estiver presente, o `mqtt_to_mongo.py` continua a funcionar normalmente sem atuadores

**Output no terminal (Janela 1 — `mqtt_to_mongo.py`):**
```
[atuadores] ativo | temp [0.0, 60.0] | som max 60.0
[atuadores] → pisid_mazeact_19: {"Type": "TurnOnAC", "Player": 19, "Room": 3}
[atuadores] → pisid_mazeact_19: {"Type": "CloseGate", "Player": 19, "RoomOrigin": 2, "RoomDestination": 3}
```

---

## 🌐 Formulários PHP — pasta `src/`

### Páginas disponíveis

| Ficheiro | URL | Função |
|---|---|---|
| `login.php` | http://localhost:9000/login.php | Login com email + password |
| `simulacoes.php` | http://localhost:9000/simulacoes.php | Listar e criar simulações |
| `editar_simulacao.php` | http://localhost:9000/editar_simulacao.php?id=X | Editar descrição de uma simulação |
| `iniciar_simulacao.php` | http://localhost:9000/iniciar_simulacao.php?id=X | Iniciar / parar `mqtt_to_mongo.py` |
| `logout.php` | http://localhost:9000/logout.php | Terminar sessão |

**Credenciais de teste:** `grupo19@labirinto.pt` / `grupo19`

---

## 📱 APIs PHP para Android — pasta `src/`

Todas as APIs aceitam parâmetros via GET ou POST: `username`, `password`, `database`.

| Ficheiro | Dados retornados |
|---|---|
| `login.php` | `success`, `IDGrupo` |
| `get_temperature_data.php` | Lista `{temperatura, idtemperatura}` |
| `get_sound_data.php` | Lista `{som, idsom}` |
| `get_room_data.php` | Lista `{Sala, NumeroMarsamisEven, NumeroMarsamisOdd}` |
| `get_messages.php` | Lista `{id, tipoalerta, hora, msg, leitura, sensor}` |
| `get_min_max_temp_values.php` | `{minimo, maximo}` de `configtemp` |
| `get_max_sound_value.php` | `{maximo}` de `configsound` |

> 💡 Os ficheiros PHP das APIs foram corrigidos para usar os nomes reais das colunas do schema (`IDSala`, `TipoAlerta`, `HoraEscrita`, etc.) mantendo aliases em minúsculas para compatibilidade com o Android.

---

## 🔁 Fluxo Completo: MQTT → MongoDB → MySQL

### Arquitetura dos 2 PCs

```
PC1:  mazerun.exe → MQTT → mqtt_to_mongo.py → MongoDB (Docker)
                                   ↓
                    ┌──────────────┴──────────────┐
                    ↓                             ↓
             gatilho odd/even              atuadores.py
             → MQTT (Score)         → MQTT (TurnOnAC / CloseGate)

PC2:  mongo_to_mysql.py (lê MongoDB do PC1 via rede) → MySQL (Docker local)
                ↓
        outlier_detector.py
         ├── Outlier z-score → INSERT mensagens (TipoAlerta='Outlier')
         └── Valor normal → INSERT temperatura/som
                                    ↓
                             Trigger MySQL automático
                              ├── Fora dos limites → INSERT mensagens (TipoAlerta='Alerta')
                              └── Passagem marsami → UPDATE ocupacaolabirinto
```

---

### PC1 — Configuração

#### 1. Descobrir o IP do PC1

Corre o script `ver_ip_pc1.bat` (ou no terminal):

```cmd
ipconfig | findstr /i "IPv4"
```

Guarda o IP da rede local (ex: `192.168.1.45`). Vais precisar dele no PC2.

#### 2. Ligar a infraestrutura

```powershell
cd C:\dev\mysqldocker
docker-compose up -d
```

> Aguarda ~30 s para o MySQL e MongoDB inicializarem.

#### 3. Arrancar os componentes (janelas separadas)

```powershell
# Janela 1 — Jogador (MQTT → MongoDB + gatilhos odd/even)
cd C:\Users\PC\Desktop\PISID\jogador
python mqtt_to_mongo.py 19

# Janela 2 — Simulador
cd C:\Users\PC\Desktop\PISID\mazerun
.\mazerun.exe 19 --flagMessage 1
```

> **Ordem:** arranca a Janela 1 primeiro, depois a 2.

---

### PC2 — Configuração

#### 1. Ligar a infraestrutura MySQL

```powershell
cd C:\dev\mysqldocker
docker-compose up -d
```

#### 2. Definir o IP do PC1 e arrancar a migração

**PowerShell:**
```powershell
$env:MONGO_HOST="192.168.1.45"   # ← IP do PC1
python mongo_to_mysql.py 19
```

**CMD:**
```cmd
set MONGO_HOST=192.168.1.45
python mongo_to_mysql.py 19
```

> Se não definires `MONGO_HOST`, o script assume `localhost` (modo de desenvolvimento num único PC).

---

### Resumo do Fluxo

| PC | Janela | Componente | Função |
|---|---|---|---|
| PC1 | 1 | `mqtt_to_mongo.py` | MQTT → MongoDB + gatilhos odd/even |
| PC1 | 2 | `mazerun.exe` | Publica sensores no MQTT |
| PC2 | 1 | `mongo_to_mysql.py` | MongoDB (PC1) → MySQL (PC2) a cada 5 s |

---

### Verificar o Fluxo

**MongoDB** — novos documentos nas coleções:
```powershell
docker exec mongo1 mongosh pisid_grupo19 --quiet --eval "
  print('movimento: ' + db.movimento.countDocuments());
  print('temperatura: ' + db.temperatura.countDocuments());
  print('som: ' + db.som.countDocuments());
"
```

**MySQL** — novos registos (via phpMyAdmin em http://localhost:9001):
```sql
USE labirinto;
SELECT COUNT(*) FROM temperatura;
SELECT COUNT(*) FROM som;
SELECT COUNT(*) FROM medicoespassagens;
SELECT COUNT(*) FROM mensagens;
SELECT * FROM ocupacaolabirinto ORDER BY IDSala;
```

### Teste de Failover MongoDB (opcional)

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
├── ver_ip_pc1.bat                  ← Mostra o IP deste PC para ligar do PC2
├── Dockerfile
├── src/                            ← Código PHP
│   ├── login.php                   ← Login de utilizador
│   ├── simulacoes.php              ← Listar e criar simulações
│   ├── editar_simulacao.php        ← Editar simulação
│   ├── iniciar_simulacao.php       ← Iniciar/parar mqtt_to_mongo.py
│   ├── logout.php                  ← Terminar sessão
│   ├── get_temperature_data.php    ← API Android: dados de temperatura
│   ├── get_sound_data.php          ← API Android: dados de som
│   ├── get_room_data.php           ← API Android: ocupação das salas
│   ├── get_messages.php            ← API Android: mensagens de alerta
│   ├── get_min_max_temp_values.php ← API Android: limites de temperatura
│   └── get_max_sound_value.php     ← API Android: limite de som
├── mysql_data/                     ← Dados do MySQL (gerido pelo Docker)
├── mysql_files/
│   ├── labirinto.sql               ← Schema: cria as tabelas (executa 1.º)
│   ├── labirinto_preencher.sql     ← Dados: preenche as tabelas (executa 2.º)
│   └── labirinto_patch.sql         ← Patch manual: tabelas extra + triggers
└── Python/
    ├── mqtt_to_mongo.py            ← MQTT → MongoDB + gatilhos odd/even
    ├── mongo_to_mysql.py           ← MongoDB → MySQL (migração incremental + outliers)
    ├── db_mysql.py                 ← Configuração da ligação MySQL
    ├── outlier_detector.py         ← Deteção de outliers/dados sujos
    ├── gatilho_odd_even.py         ← Lógica dos gatilhos odd/even
    └── atuadores.py                ← Atuadores automáticos (AC + corredores)
```
