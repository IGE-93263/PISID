# Arquitetura: Migração incremental MongoDB → MySQL

## Visão geral

```
                    ┌─────────────────────┐
   MQTT             │     mqtt_to_db      │             MongoDB
   ──────►          │  (inalterado)       │  ──────────►  (27017/18/19)
                    └─────────────────────┘
                                    │
                                    │  replicação automática
                                    ▼
                    ┌─────────────────────────────────────┐
                    │         Mongo Replica Set           │
                    │  movimento | temperatura | som      │
                    └─────────────────────────────────────┘
                                    │
                                    │  migração incremental
                                    │  (processo separado)
                                    ▼
                    ┌─────────────────────────────────────┐
                    │     mongo_to_mysql.py               │
                    │  - Lê novos docs (por cursor)       │
                    │  - Escreve em MySQL                 │
                    │  - Guarda checkpoint                │
                    └─────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────┐
                    │            MySQL                   │
                    │  medicoespassagens | temperatura |  │
                    │  som (tabelas labirinto)            │
                    └─────────────────────────────────────┘
```

## Princípios

1. **mqtt_to_db** — mantém-se focado em MQTT → MongoDB. Não escreve em MySQL.
2. **Processo separado** — `mongo_to_mysql.py` corre como serviço ou cron, desacoplado do mqtt_to_db.
3. **Incremental** — usa cursor (ex: último `_id` ou `Hora`) para migrar só novos documentos.
4. **Tolerante a falhas** — se MySQL falhar, mantém o cursor e reenvia na próxima execução.

## Componentes

| Componente | Função |
|------------|--------|
| `mongo_to_mysql.py` | Processo principal: lê Mongo → escreve MySQL → atualiza checkpoint |
| `checkpoint` | Valor guardado (ficheiro ou tabela MySQL) com o último doc migrado |
| `db_mysql.py` | Funções de ligação e escrita MySQL |

## Mapeamento MongoDB → MySQL

| Mongo (coleção) | MySQL (tabela) | Campos |
|-----------------|----------------|--------|
| movimento | medicoespassagens | Player→?, Marsami, RoomOrigin→salade?, RoomDestiny→salapara?, Status, Hora |
| temperatura | temperatura | Temperature→temperatura, Hour→hora (ajustar ao teu schema) |
| som | som | Sound→som, Hour→hora (ajustar ao teu schema) |

*Nota: Os nomes exatos das colunas MySQL dependem do teu `labirinto.sql`.*

## Checkpoint (incremental)

Opções para saber o que já foi migrado:

- **A) Ficheiro** `migration_checkpoint.json` — `{"movimento": "ObjectId(...)", "temperatura": "...", "som": "..."}`
- **B) Tabela MySQL** `migration_checkpoint` — uma linha com último _id por coleção

Consultas MongoDB para documentos novos:
```javascript
db.movimento.find({ _id: { $gt: ObjectId(checkpoint) } }).sort({ _id: 1 })
```

## Ciclo de execução

1. Carregar checkpoint
2. Para cada coleção: consultar docs com `_id` > checkpoint
3. Para cada documento: converter campos e fazer INSERT no MySQL
4. Guardar novo checkpoint (último _id processado)
5. Repetir a cada N segundos (ex: 5–10 s)

## Execução

```bash
pip install mysql-connector-python  # se necessário
python mongo_to_mysql.py 19
```

Pode correr em paralelo com `mqtt_to_db.py` e `mazerun`.

## Ajustes ao teu schema MySQL

O `mongo_to_mysql.py` usa nomes de colunas por defeito. Se o teu `labirinto.sql` tiver estrutura diferente, edita as funções `migrar_movimento`, `migrar_temperatura`, `migrar_som` e os SQLs INSERT.

Exemplo: se `temperatura` tiver só `(idtemperatura, temperatura)`, o INSERT será:
```sql
INSERT INTO temperatura (temperatura) VALUES (%s)
```
e passas só `d.get("Temperature")`.
