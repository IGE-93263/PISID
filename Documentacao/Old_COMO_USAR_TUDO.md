# Teste do fluxo completo: MQTT → MongoDB → MySQL

## Pré-requisitos

1. **MongoDB** (3 réplicas no Docker)
2. **MySQL** (Docker ou local) com base `labirinto`
3. **Schema e seed** em MySQL (usa o ficheiro existente + seed):

No phpMyAdmin (localhost:9001), executa **por ordem**:

   - **labirinto.sql** — cria o schema com FKs (em `C:\dev\mysqldocker\mysql_files\labirinto.sql`)
   - **labirinto_seed.sql** — insere dados mínimos (equipa 19, salas 0–10, utilizador, simulacao 1)

4. **Credenciais MySQL** — editar `db_mysql.py` ou variáveis de ambiente:
   ```bash
   set MYSQL_HOST=localhost
   set MYSQL_USER=root
   set MYSQL_PASSWORD=...
   set MYSQL_DATABASE=labirinto
   ```

5. **Dependências:** `pip install pymongo mysql-connector-python`

---

## Passos para testar

### 1. Ligar infraestrutura

```powershell
cd C:\dev\mysqldocker
docker-compose up -d
```
(Aguarda ~30 s para MySQL inicializar)

### 2. Arrancar os 4 componentes (em janelas diferentes)

```powershell
# Janela 1: Jogador (MQTT → MongoDB)
cd C:\Users\PC\Desktop\PISID\jogador
python mqtt_to_db.py 19

# Janela 2: Migração (MongoDB → MySQL)
python mongo_to_mysql.py 19

# Janela 3: Simulador
cd C:\Users\PC\Desktop\PISID\mazerun
.\mazerun.exe 19 --flagMessage 1
```

### 3. Verificar o fluxo

**MongoDB** — novos documentos nas coleções:
```powershell
mongosh --port 27017
> use pisid_grupo19
> db.movimento.countDocuments()
> db.temperatura.countDocuments()
> db.som.countDocuments()
```

**MySQL** — novos registos nas tabelas:
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

### 4. Teste de failover (opcional)

1. Com tudo a correr, para mongo1: `docker stop mongo1`
2. O mqtt_to_db deve fazer failover para 27018/27019
3. A migração continua a funcionar (lê de qualquer nó Mongo disponível)
4. Reinicia mongo1: `docker start mongo1`

---

## Resumo do fluxo

| Janela | Componente       | Função                          |
|--------|------------------|----------------------------------|
| 1      | mqtt_to_db       | MQTT → MongoDB                   |
| 2      | mongo_to_mysql   | MongoDB → MySQL (a cada 5 s)     |
| 3      | mazerun          | Publica sensores no MQTT         |

**Ordem:** Inicia 1 e 2, depois 3.
