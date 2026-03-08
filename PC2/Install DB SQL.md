# Configuração da Base de Dados (MySQL Docker)

Este guia explica como configurar a base de dados **labirinto** utilizando o Docker.

## 🚀 Passo a Passo

### 1. Preparação do Ficheiro
Coloque o ficheiro `labirinto.sql` dentro da pasta do seu projeto no seguinte caminho:
`\mysqldocker\mysql_files`

### 2. Configuração via Terminal Docker
No Docker Desktop (ou via CLI), abra o **"Open in terminal"** do seu container MySQL e execute os seguintes comandos:

1.  **Aceder ao MySQL:**
    ```bash
    mysql -u root -p
    ```
    *(A password é `root`)*

2.  **Criar a Base de Dados:**
    ```sql
    create database labirinto;
    exit
    ```

3.  **Importar o Script SQL:**
    ```bash
    mysql -u root -p labirinto < /var/lib/mysql-files/labirinto.sql
    ```

4.  **Verificar a Instalação:**
    ```bash
    mysql -u root -p
    use labirinto;
    show tables;
    ```

---

## 🌐 Acesso via Browser (Adminer / PHPMyAdmin)

Para visualizar os dados graficamente, aceda ao seguinte endereço no seu browser:

* **URL:** [http://localhost:9001/](http://localhost:9001/)
* **Server:** `mysql`
* **User:** `root`
* **Password:** `root`

---

## 📊 Estrutura do Modelo Relacional

O script configura as seguintes tabelas para o projeto:
* `equipa` e `utilizador` (Gestão de participantes)
* `sala` e `simulacao` (Estrutura do labirinto e sessões)
* `mensagens`, `temperatura`, `som` (Logs de sensores)
* `medicoespassagens` e `ocupacaolabirinto` (Rastreamento de movimentos)
