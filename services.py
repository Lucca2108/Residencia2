from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from db import get_connection
from regras_fraude import avaliar_fraude
from schemas import TransacaoCreate, TransacaoUpdate
from schemas import ViagemCreate
from ml_motor import prever_anomalia


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "sim"}

    return False


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)[:10]


def normalize_time(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    text = str(value).strip()
    if len(text) == 5:
        return f"{text}:00"

    return text


def normalize_decimal(value: Any):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    return value


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "valor": float(normalize_decimal(row["valor"])),
        "data": normalize_date(row["data"]),
        "hora": normalize_time(row["hora"]),
        "dia_semana": row["dia_semana"],
        "categoria": row["categoria"],
        "conta": row["conta"],
        "cidade": row["cidade"],
        "estado": row["estado"],
        "pais": row["pais"],
        "latitude": None if row["latitude"] is None else float(normalize_decimal(row["latitude"])),
        "longitude": None if row["longitude"] is None else float(normalize_decimal(row["longitude"])),
        "tipo_transacao": row["tipo_transacao"],
        "dispositivo": row["dispositivo"],
        "estabelecimento": row["estabelecimento"],
        "tentativas": int(row["tentativas"]),
        "ip_origem": row["ip_origem"],
        "is_fraude": normalize_bool(row["is_fraude"]),
    }


def list_transacoes(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM transacoes ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        rows = cursor.fetchall()
        return [normalize_row(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def get_transacao_by_id(transacao_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM transacoes WHERE id = %s",
            (transacao_id,),
        )
        row = cursor.fetchone()
        return normalize_row(row) if row else None
    finally:
        cursor.close()
        conn.close()


def search_transacoes(
    categoria: str | None = None,
    conta: str | None = None,
    cidade: str | None = None,
    estado: str | None = None,
    pais: str | None = None,
    tipo_transacao: str | None = None,
    dispositivo: str | None = None,
    estabelecimento: str | None = None,
    is_fraude: int | None = None,
    data_inicial: str | None = None,
    data_final: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM transacoes"
    conditions = []
    params: list[Any] = []

    if categoria:
        conditions.append("categoria LIKE %s")
        params.append(f"%{categoria}%")

    if conta:
        conditions.append("conta LIKE %s")
        params.append(f"%{conta}%")

    if cidade:
        conditions.append("cidade LIKE %s")
        params.append(f"%{cidade}%")

    if estado:
        conditions.append("estado = %s")
        params.append(estado)

    if pais:
        conditions.append("pais = %s")
        params.append(pais)

    if tipo_transacao:
        conditions.append("tipo_transacao = %s")
        params.append(tipo_transacao)

    if dispositivo:
        conditions.append("dispositivo LIKE %s")
        params.append(f"%{dispositivo}%")

    if estabelecimento:
        conditions.append("estabelecimento LIKE %s")
        params.append(f"%{estabelecimento}%")

    if is_fraude is not None:
        conditions.append("is_fraude = %s")
        params.append(is_fraude)

    if data_inicial:
        conditions.append("data >= %s")
        params.append(data_inicial)

    if data_final:
        conditions.append("data <= %s")
        params.append(data_final)

    if valor_min is not None:
        conditions.append("valor >= %s")
        params.append(valor_min)

    if valor_max is not None:
        conditions.append("valor <= %s")
        params.append(valor_max)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [normalize_row(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def _format_payload_hora(hora: str) -> str:
    return hora if len(hora) == 8 else f"{hora}:00"


def get_estatisticas_conta(conta: str) -> float:
    """Calcula a média histórica de gastos da conta."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT AVG(valor) as media_valor FROM transacoes WHERE conta = %s AND is_fraude = 0",
            (conta,)
        )
        row = cursor.fetchone()
        return float(row["media_valor"]) if row and row["media_valor"] else 0.0
    finally:
        cursor.close()
        conn.close()


def get_frequencia_recente(conta: str, data_tx: str, hora_tx: str, minutos: int = 30) -> int:
    """Conta o número de transações da conta nos últimos X minutos em relação à transação atual."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        SELECT COUNT(*) FROM transacoes 
        WHERE conta = %s 
        AND TIMESTAMP(data, hora) BETWEEN TIMESTAMP(%s, %s) - INTERVAL %s MINUTE AND TIMESTAMP(%s, %s)
        """
        cursor.execute(sql, (conta, data_tx, hora_tx,
                       minutos, data_tx, hora_tx))
        total = cursor.fetchone()[0]
        return int(total)
    finally:
        cursor.close()
        conn.close()


def create_transacao(payload: TransacaoCreate) -> dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        hora_formatada = _format_payload_hora(payload.hora)
        media_hist = get_estatisticas_conta(payload.conta)
        freq = get_frequencia_recente(
            payload.conta, payload.data, hora_formatada, minutos=30)
        viagens_ativas = get_viagem_ativa_por_conta(
            payload.conta, payload.data)
        em_viagem_legitima = False

        for viagem in viagens_ativas:
            pais_destino = str(viagem.get("pais_destino", "")).strip().lower()
            estado_destino = str(viagem.get(
                "estado_destino", "")).strip().lower()
            if payload.pais.lower() == pais_destino:
                em_viagem_legitima = True
                break
            if payload.estado and payload.estado.lower() == estado_destino:
                em_viagem_legitima = True
                break

        resultado_ia = prever_anomalia(payload.dict())
        analise_fraude = avaliar_fraude(payload, media_historica=media_hist,
                                        frequencia_recente=freq, em_viagem=em_viagem_legitima, resultado_ml=resultado_ia)
        
        is_fraude = 1 if analise_fraude["is_fraude"] else 0
        status_validacao = 'pendente' if is_fraude == 1 else 'aprovada'

        if status_validacao == 'pendente':
            print(f"⚠️ [ALERTA ANTIFRAUDE] Transação suspeita detectada!")
            print(f"📱 Disparando Push Notification/SMS para o cliente da conta {payload.conta}...")
            print(f"Motivos: {', '.join(analise_fraude['motivos'])}")

        sql = """
        INSERT INTO transacoes (
            valor, data, hora, dia_semana, categoria, conta, cidade, estado, pais, 
            latitude, longitude, tipo_transacao, dispositivo, estabelecimento, 
            tentativas, ip_origem, is_fraude, status_validacao
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            payload.valor,
            payload.data,
            _format_payload_hora(payload.hora),
            payload.dia_semana,
            payload.categoria,
            payload.conta,
            payload.cidade,
            payload.estado,
            payload.pais,
            payload.latitude,
            payload.longitude,
            payload.tipo_transacao,
            payload.dispositivo,
            payload.estabelecimento,
            payload.tentativas,
            payload.ip_origem,
            1 if analise_fraude["is_fraude"] else 0,
            status_validacao
        )

        cursor.execute(sql, values)
        conn.commit()
        transacao_id = cursor.lastrowid
        return get_transacao_by_id(transacao_id)
    finally:
        cursor.close()
        conn.close()


def create_viagem(payload: ViagemCreate) -> dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO viagens (conta, cidade_destino, estado_destino, pais_destino, data_inicio, data_fim)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            payload.conta,
            payload.cidade_destino,
            payload.estado_destino,
            payload.pais_destino,
            payload.data_inicio,
            payload.data_fim
        )
        cursor.execute(sql, values)
        conn.commit()
        viagem_id = cursor.lastrowid

        return {
            "id": viagem_id,
            "conta": payload.conta,
            "cidade_destino": payload.cidade_destino,
            "estado_destino": payload.estado_destino,
            "pais_destino": payload.pais_destino,
            "data_inicio": payload.data_inicio,
            "data_fim": payload.data_fim
        }
    finally:
        cursor.close()
        conn.close()


def get_viagem_ativa_por_conta(conta: str, data_transacao: str) -> list[dict[str, Any]]:
    """Busca viagens ativas de uma conta em uma data específica."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
        SELECT * FROM viagens 
        WHERE conta = %s AND %s BETWEEN data_inicio AND data_fim
        """
        cursor.execute(sql, (conta, data_transacao))
        viagens = cursor.fetchall()
        for viagem in viagens:
            if viagem.get('data_inicio'):
                viagem['data_inicio'] = str(viagem['data_inicio'])
            if viagem.get('data_fim'):
                viagem['data_fim'] = str(viagem['data_fim'])
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
        
def get_viagens_por_conta(conta: str) -> list[dict[str, Any]]:
    """Busca todo o histórico de viagens cadastradas para uma conta."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM viagens WHERE conta = %s ORDER BY data_inicio DESC"
        cursor.execute(sql, (conta,))
        viagens = cursor.fetchall()
        
        for viagem in viagens:
            if viagem.get('data_inicio'):
                viagem['data_inicio'] = str(viagem['data_inicio'])
            if viagem.get('data_fim'):
                viagem['data_fim'] = str(viagem['data_fim'])
                
        return viagens
    finally:
        cursor.close()
        conn.close()


def update_transacao(transacao_id: int, payload: TransacaoUpdate) -> dict[str, Any] | None:
    existing = get_transacao_by_id(transacao_id)
    if not existing:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        analise_fraude = avaliar_fraude(payload)

        sql = """
        UPDATE transacoes
        SET
            valor = %s,
            data = %s,
            hora = %s,
            dia_semana = %s,
            categoria = %s,
            conta = %s,
            cidade = %s,
            estado = %s,
            pais = %s,
            latitude = %s,
            longitude = %s,
            tipo_transacao = %s,
            dispositivo = %s,
            estabelecimento = %s,
            tentativas = %s,
            ip_origem = %s,
            is_fraude = %s
        WHERE id = %s
        """

        values = (
            payload.valor,
            payload.data,
            _format_payload_hora(payload.hora),
            payload.dia_semana,
            payload.categoria,
            payload.conta,
            payload.cidade,
            payload.estado,
            payload.pais,
            payload.latitude,
            payload.longitude,
            payload.tipo_transacao,
            payload.dispositivo,
            payload.estabelecimento,
            payload.tentativas,
            payload.ip_origem,
            1 if analise_fraude["is_fraude"] else 0,
            transacao_id,
        )

        cursor.execute(sql, values)
        conn.commit()
        return get_transacao_by_id(transacao_id)
    finally:
        cursor.close()
        conn.close()


def delete_transacao(transacao_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transacoes WHERE id = %s", (transacao_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()
        
def validar_transacao_cliente(transacao_id: int, confirmada: bool) -> dict[str, Any] | None:
    """Atualiza o status da transação baseado na resposta do cliente no app."""
    transacao = get_transacao_by_id(transacao_id)
    if not transacao:
        return None

    novo_status = 'confirmada_pelo_cliente' if confirmada else 'fraude_confirmada'
    is_fraude_atualizado = 0 if confirmada else 1

    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        UPDATE transacoes 
        SET status_validacao = %s, is_fraude = %s
        WHERE id = %s
        """
        cursor.execute(sql, (novo_status, is_fraude_atualizado, transacao_id))
        conn.commit()
        return get_transacao_by_id(transacao_id)
    finally:
        cursor.close()
        conn.close()