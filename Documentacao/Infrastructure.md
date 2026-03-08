# 🏗️ Documentação da Infraestrutura do Projeto

Este documento explica os ficheiros principais usados para levantar e gerir a infraestrutura local deste projeto, que inclui serviços de **PHP**, **MySQL** e um **cluster MongoDB**.

---

## 1. Script de Reset — `reset_bd.bat`

Este ficheiro é um script de automação para Windows (PowerShell/CMD). A sua função principal é fazer um **Hard Reset** à base de dados MySQL.

> Como o Docker apenas importa o ficheiro `labirinto.sql` na **primeira vez** que a base de dados é criada, este script automatiza o processo de apagar o histórico e simular uma instalação limpa.

### O que cada bloco faz

| Bloco | Descrição |
|---|---|
| `@echo off` / `echo ...` | Esconde os comandos técnicos no terminal e mostra apenas mensagens amigáveis para sabermos em que passo estamos. |
| `docker-compose down` | Pára e remove todos os contentores, redes e volumes temporários em execução. |
| `rmdir /s /q .\mysql_data` | Apaga a pasta física onde o MySQL guarda os ficheiros de sistema no computador local. |
| `mkdir .\mysql_data` | Recria a pasta vazia, forçando o Docker a tratá-la como uma instalação nova. |
| `docker-compose up -d` | Reinicia todos os serviços em segundo plano. O MySQL, ao ver a pasta vazia, importa automaticamente o `labirinto.sql`. |

---

## 2. Orquestrador de Contentores — `docker-compose.yml`

O `docker-compose.yml` é o **coração da infraestrutura**. Define como os vários contentores se comportam, comunicam entre si e se ligam ao computador físico.

---

### Serviço: `php`

- **Objetivo:** Servidor web para correr o código da aplicação.
- **Configuração:** Constrói a imagem através de um `Dockerfile` local (em vez de usar uma imagem pré-definida).
- **Volumes:** Mapeia `./src` → `/var/www/html`, permitindo editar o código PHP localmente e ver as alterações em tempo real.
- **Acesso:** [`http://localhost:9000`](http://localhost:9000)

---

### Serviço: `mysql`

- **Objetivo:** Base de dados relacional.
- **Configuração:** Versão `8.0`, palavra-passe do utilizador `root` definida como `root`. A variável `MYSQL_DATABASE: labirinto` cria a base de dados automaticamente.
- **Acesso:** Porta padrão `3306`.

#### Volumes configurados

| Volume | Função |
|---|---|
| `.\mysql_data` | Persiste os dados para não se perderem ao desligar o contentor. |
| `.\mysql_files` | Pasta segura para troca de ficheiros (ex: CSVs). |
| `.\mysql_files\labirinto.sql` | Injeta o SQL em `/docker-entrypoint-initdb.d/`, criando as tabelas no primeiro arranque. |

---

### Serviço: `phpmyadmin`

- **Objetivo:** Interface visual para gerir o MySQL.
- **Configuração:** `PMA_ARBITRARY: 1` permite especificar o servidor (ex: `mysql`) no ecrã de login.
- **Acesso:** [`http://localhost:9001`](http://localhost:9001)

---

### Serviços MongoDB — `mongo1`, `mongo2`, `mongo3`

- **Objetivo:** Criar um cluster de bases de dados NoSQL em **Replica Set**.
- **Configuração:** Três instâncias independentes do MongoDB nas portas `27017`, `27018` e `27019`.
- **Comando:** `--replSet rs0` informa as instâncias que pertencem ao mesmo grupo de replicação.

---

### Serviço: `mongo-setup`

- **Objetivo:** Configurar automaticamente o cluster MongoDB.
- **Como funciona:**
  1. Arranca apenas **depois** dos três nós MongoDB estarem em execução.
  2. Aguarda **20 segundos** para garantir que estão prontos.
  3. Executa um script via `mongosh` que liga os três nós:
     - `mongo1` → nó **Primary** (`priority: 2`)
     - `mongo2`, `mongo3` → nós **Secondary** (`priority: 1`)
  4. Se o cluster já estiver configurado, deteta isso sem gerar erros.

---

## Resumo dos Acessos

| Serviço | URL / Porta |
|---|---|
| PHP (Aplicação) | `http://localhost:9000` |
| phpMyAdmin | `http://localhost:9001` |
| MySQL | `localhost:3306` |
| MongoDB 1 | `localhost:27017` |
| MongoDB 2 | `localhost:27018` |
| MongoDB 3 | `localhost:27019` |