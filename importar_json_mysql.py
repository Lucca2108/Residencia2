import json
import mysql.connector
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

json_path = BASE_DIR / "data" / "transacoes_treino_sem_fraude.json"

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="bancodobrasil"
)

cursor = conn.cursor()

with open(json_path, "r", encoding="utf-8") as f:
    dados = json.load(f)

sql = """
INSERT INTO transacoes (
    id,
    valor,
    data,
    hora,
    dia_semana,
    categoria,
    conta,
    cidade,
    estado,
    pais,
    latitude,
    longitude,
    tipo_transacao,
    dispositivo,
    estabelecimento,
    tentativas,
    ip_origem,
    is_fraude
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

valores = []

for item in dados:
    valores.append((
        item["id"],
        item["valor"],
        item["data"],
        item["hora"],
        item["dia_semana"],
        item["categoria"],
        item["conta"],
        item["cidade"],
        item["estado"],
        item["pais"],
        item["latitude"],
        item["longitude"],
        item["tipo_transacao"],
        item["dispositivo"],
        item["estabelecimento"],
        item["tentativas"],
        item["ip_origem"],
        item["is_fraude"]
    ))

batch_size = 1000

for i in range(0, len(valores), batch_size):
    lote = valores[i:i + batch_size]

    cursor.executemany(sql, lote)
    conn.commit()

    print(f"Lote {i // batch_size + 1} inserido com sucesso!")

print(f"{cursor.rowcount} registros inseridos!")

cursor.close()
conn.close()
