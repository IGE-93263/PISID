"""
popular_corridor.py — Popula a tabela corridor automaticamente.

Lê todos os movimentos válidos já existentes em medicoespassagens
e extrai os pares únicos (IDSalaOrigem, IDSalaDestino) onde
IDSalaOrigem > 0 — esses são os corredores reais do labirinto.

Uso:
    python popular_corridor.py

Corre UMA VEZ após teres dados em medicoespassagens.
Pode ser corrido novamente sem problema (usa INSERT IGNORE).
"""

import mysql.connector

MYSQL_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "root",
    "database": "labirinto",
}

def main():
    conn   = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    # Extrai todos os pares origem→destino onde origem > 0
    cursor.execute("""
        SELECT DISTINCT IDSalaOrigem, IDSalaDestino
        FROM medicoespassagens
        WHERE IDSalaOrigem > 0
          AND IDSalaDestino > 0
        ORDER BY IDSalaOrigem, IDSalaDestino
    """)
    pares = cursor.fetchall()

    if not pares:
        print("Nenhum movimento encontrado em medicoespassagens.")
        print("Corre o mazerun primeiro e deixa os dados chegar ao MySQL.")
        return

    print(f"Corredores encontrados: {len(pares)}")
    for origem, destino in pares:
        print(f"  {origem} → {destino}")

    # Insere na tabela corridor (INSERT IGNORE — não duplica)
    inseridos = 0
    for origem, destino in pares:
        try:
            cursor.execute(
                "INSERT IGNORE INTO corridor (IDSala1, IDSala2) VALUES (%s, %s)",
                (origem, destino)
            )
            if cursor.rowcount > 0:
                inseridos += 1
        except mysql.connector.Error as e:
            print(f"  [Erro] {origem}→{destino}: {e}")

    conn.commit()
    print(f"\nInseridos {inseridos} novos corredores na tabela corridor.")

    # Verificação final
    cursor.execute("SELECT COUNT(*) FROM corridor")
    total = cursor.fetchone()[0]
    print(f"Total de corredores na tabela: {total}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
