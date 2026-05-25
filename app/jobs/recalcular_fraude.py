"""
Job para reavaliação de fraude em todas as transações.
Útil para processar histórico ou reavaliar com novas regras de negócio.
"""
from __future__ import annotations

from app.db.connection import get_connection
from app.domain.fraude import avaliar_fraude
from app.domain.ml import prever_anomalia
from app.repositories.transacao_repository import (
    bulk_update_fraude_status,
    list_transacoes,
)
from app.repositories.viagem_repository import get_viagem_ativa_por_conta


def _transacao_em_viagem_legitima(conta: str, pais: str, estado: str | None, data: str) -> bool:
    viagens_ativas = get_viagem_ativa_por_conta(conta, data)
    pais = str(pais or "").strip().lower()
    estado = str(estado or "").strip().lower()

    for viagem in viagens_ativas:
        pais_destino = str(viagem.get("pais_destino", "")).strip().lower()
        estado_destino = str(viagem.get("estado_destino", "")).strip().lower()
        if pais and pais == pais_destino:
            return True
        if estado and estado == estado_destino:
            return True

    return False


def _build_estatisticas_cache() -> dict[str, float]:
    """
    Carrega TODAS as estatísticas de contas em uma única query.
    Retorna: dict {conta: media_valor}
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT conta, AVG(valor) as media_valor
            FROM transacoes
            WHERE is_fraude = 0
            GROUP BY conta
        """)
        rows = cursor.fetchall()
        return {row["conta"]: float(row["media_valor"]) for row in rows}
    finally:
        cursor.close()
        conn.close()


def recalcular_todas_transacoes(limit: int = 1000000, offset: int = 0, batch_size: int = 500) -> int:
    """
    Versão otimizada com:
    - Cache de estatísticas por conta (uma query)
    - Bulk update em lotes (reduz de 30k queries para 60)
    """
    print(f"[RECALC] Carregando todas as transações...")
    all_transacoes = []
    page_offset = 0
    
    # Carrega todas as transações de uma vez
    while page_offset < limit:
        batch = list_transacoes(limit=batch_size, offset=page_offset)
        if not batch:
            break
        all_transacoes.extend(batch)
        page_offset += batch_size
    
    total_count = len(all_transacoes)
    print(f"[RECALC] Total de transações: {total_count}")
    
    if total_count == 0:
        return 0
    
    # Cache de estatísticas por conta (uma única query!)
    print(f"[RECALC] Construindo cache de estatísticas...")
    stats_cache = _build_estatisticas_cache()
    print(f"[RECALC] {len(stats_cache)} contas com histórico")
    
    # Processa em batches e acumula atualizações
    updates_batch = []
    total_updated = 0
    processed = 0
    
    for transacao in all_transacoes:
        processed += 1
        
        try:
            hora = transacao.get("hora")
            conta = transacao["conta"]
            
            # Usa cache em vez de query
            media_hist = stats_cache.get(conta, 0.0)
            
            # Uma query por conta (mas com cache local)
            from app.repositories.transacao_repository import get_frequencia_recente
            freq = get_frequencia_recente(conta, transacao["data"], hora, minutos=30)
            em_viagem_legitima = _transacao_em_viagem_legitima(
                conta, transacao["pais"], transacao.get("estado"), transacao["data"]
            )
            resultado_ia = prever_anomalia(transacao)
            analise = avaliar_fraude(
                transacao,
                media_historica=media_hist,
                frequencia_recente=freq,
                em_viagem=em_viagem_legitima,
                resultado_ml=resultado_ia,
            )

            updates_batch.append({
                "id": transacao["id"],
                "is_fraude": analise["is_fraude"],
                "status_validacao": "pendente" if analise["is_fraude"] else "aprovada",
            })

            # Executa bulk update a cada batch_size registros
            if len(updates_batch) >= batch_size:
                updated = bulk_update_fraude_status(updates_batch)
                total_updated += updated
                print(f"[RECALC] Processadas {processed}/{total_count} ({updated} atualizadas neste lote)")
                updates_batch = []
                
        except Exception as e:
            print(f"[RECALC] Erro ao avaliar transação {transacao.get('id')}: {e}")
            continue
    
    # Atualiza o último lote
    if updates_batch:
        updated = bulk_update_fraude_status(updates_batch)
        total_updated += updated
        print(f"[RECALC] Lote final: {updated} atualizadas")
    
    print(f"[RECALC] Recalculadas {total_updated} transações no total.")
    return total_updated
