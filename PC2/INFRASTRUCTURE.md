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
docker-compose up -d         ← Reinicia tudo; MySQL reimporta o labirinto.sql
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
| `./mysql_files/labirinto.sql` | `/docker-entrypoint-initdb.d/labirinto.sql` | **Importa o schema e dados no primeiro arranque** |

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
    └── labirinto.sql       ← Schema e dados iniciais da BD
```
