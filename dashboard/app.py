from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd
import plotly.express as px
import streamlit as st

from app.db.connection import get_connection


API_BASE_URL = "http://127.0.0.1:8000"


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _carregar_resumo_api() -> dict | None:
    try:
        return _fetch_json(f"{API_BASE_URL}/transacoes/dashboard")
    except (URLError, TimeoutError, json.JSONDecodeError, Exception):
        return None


@st.cache_data(ttl=60)
def _carregar_transacoes_local() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM transacoes", conn)
    finally:
        conn.close()


def _metrics_from_resumo(resumo: dict) -> tuple[int, int, float]:
    totais = resumo.get("totais", {})
    total_transacoes = int(totais.get("total_transacoes") or 0)
    total_fraudes = int(totais.get("total_fraudes") or 0)
    taxa_fraude = (total_fraudes / total_transacoes) * 100 if total_transacoes else 0.0
    return total_transacoes, total_fraudes, taxa_fraude


def build_dashboard() -> None:
    st.set_page_config(page_title="Dashboard Antifraude", page_icon="🛡️", layout="wide")
    st.title("🛡️ Painel de Controle Antifraude")
    st.markdown("Monitoramento de transações, alertas de Machine Learning e gestão de risco.")

    resumo = _carregar_resumo_api()

    if resumo:
        totais = resumo.get("totais", {})
        total_transacoes, total_fraudes, taxa_fraude = _metrics_from_resumo(resumo)

        st.subheader("📊 Visão Geral")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total de Transações", f"{total_transacoes:,}")
        col2.metric("Fraudes Detectadas", f"{total_fraudes:,}")
        col3.metric("Taxa de Fraude (%)", f"{taxa_fraude:.2f}%")
        col4.metric("Valor Total", f"R$ {float(totais.get('valor_total') or 0):,.2f}")
        col5.metric("Maior Transação", f"R$ {float(totais.get('maior_transacao') or 0):,.2f}")

        st.divider()
        st.subheader("📈 Gráficos do Resumo")

        col_a, col_b = st.columns(2)
        with col_a:
            categorias = pd.DataFrame(resumo.get("categorias", []))
            if not categorias.empty:
                fig_categoria = px.bar(
                    categorias,
                    x="categoria",
                    y="valor_total",
                    title="Valor Total por Categoria",
                    labels={"categoria": "Categoria", "valor_total": "Valor Total (R$)"},
                    color="valor_total",
                    color_continuous_scale="Reds",
                )
                st.plotly_chart(fig_categoria, use_container_width=True)
            else:
                st.info("Sem dados de categorias para exibir.")

        with col_b:
            horas = pd.DataFrame(resumo.get("horas", []))
            if not horas.empty:
                fig_horas = px.line(
                    horas,
                    x="hora_label",
                    y="valor_total",
                    markers=True,
                    title="Distribuição de Valor por Hora",
                    labels={"hora_label": "Hora", "valor_total": "Valor Total (R$)"},
                )
                st.plotly_chart(fig_horas, use_container_width=True)
            else:
                st.info("Sem dados de horários para exibir.")

        col_c, col_d = st.columns(2)
        with col_c:
            dispositivos = pd.DataFrame(resumo.get("dispositivos", []))
            if not dispositivos.empty:
                fig_dispositivos = px.pie(
                    dispositivos,
                    names="dispositivo",
                    values="total",
                    title="Transações por Dispositivo",
                    hole=0.35,
                )
                st.plotly_chart(fig_dispositivos, use_container_width=True)
            else:
                st.info("Sem dados de dispositivos para exibir.")

        with col_d:
            tipos = pd.DataFrame(resumo.get("tipos_transacao", []))
            if not tipos.empty:
                fig_tipos = px.bar(
                    tipos,
                    x="tipo_transacao",
                    y="total",
                    title="Quantidade por Tipo de Transação",
                    labels={"tipo_transacao": "Tipo", "total": "Quantidade"},
                    color="total",
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(fig_tipos, use_container_width=True)
            else:
                st.info("Sem dados de tipos de transação para exibir.")

        col_e, col_f = st.columns(2)
        with col_e:
            fraudes = pd.DataFrame(resumo.get("fraudes", []))
            if not fraudes.empty:
                fig_fraudes = px.bar(
                    fraudes,
                    x="label",
                    y="valor",
                    title="Normal x Fraude",
                    labels={"label": "Classe", "valor": "Quantidade"},
                    color="label",
                    color_discrete_map={"Normais": "#00cc96", "Fraudes": "#ef553b"},
                )
                st.plotly_chart(fig_fraudes, use_container_width=True)
            else:
                st.info("Sem dados de fraude para exibir.")

        with col_f:
            paises = pd.DataFrame(resumo.get("paises", []))
            if not paises.empty:
                fig_paises = px.bar(
                    paises,
                    x="pais",
                    y="total",
                    title="Transações por País",
                    labels={"pais": "País", "total": "Quantidade"},
                    color="total",
                    color_continuous_scale="Purples",
                )
                st.plotly_chart(fig_paises, use_container_width=True)
            else:
                st.info("Sem dados de países para exibir.")

        st.divider()
        st.caption("Dados carregados do endpoint GET /transacoes/dashboard.")
        return

    df = _carregar_transacoes_local()

    if df.empty:
        st.warning("Nenhuma transação encontrada no banco de dados.")
        return

    st.subheader("📊 Visão Geral")
    col1, col2, col3, col4 = st.columns(4)

    total_transacoes = len(df)
    total_fraudes = len(df[df["is_fraude"] == 1])
    taxa_fraude = (total_fraudes / total_transacoes) * 100 if total_transacoes > 0 else 0
    pendentes = len(df[df["status_validacao"] == "pendente"]) if "status_validacao" in df.columns else 0

    col1.metric("Total de Transações", f"{total_transacoes:,}")
    col2.metric("Fraudes Detectadas", f"{total_fraudes:,}")
    col3.metric("Taxa de Fraude (%)", f"{taxa_fraude:.2f}%")
    col4.metric("Validações Pendentes", f"{pendentes}")

    st.divider()
    st.subheader("📈 Análise de Padrões")
    col_grafico1, col_grafico2 = st.columns(2)

    with col_grafico1:
        df_fraudes = df[df["is_fraude"] == 1]
        if not df_fraudes.empty:
            fig_categoria = px.bar(
                df_fraudes["categoria"].value_counts().reset_index(name="count"),
                x="categoria",
                y="count",
                title="Fraudes por Categoria de Produto",
                labels={"categoria": "Categoria", "count": "Quantidade de Fraudes"},
                color_discrete_sequence=["#ef553b"],
            )
            st.plotly_chart(fig_categoria, use_container_width=True)
        else:
            st.info("Nenhuma fraude registrada para gerar o gráfico de categorias.")

    with col_grafico2:
        fig_disp = px.histogram(
            df,
            x="dispositivo",
            color="is_fraude",
            barmode="group",
            title="Transações por Dispositivo (Normal x Fraude)",
            labels={"dispositivo": "Dispositivo", "is_fraude": "É Fraude?"},
            color_discrete_map={0: "#00cc96", 1: "#ef553b"},
        )
        st.plotly_chart(fig_disp, use_container_width=True)

    st.divider()
    st.subheader("🤖 Visão do Machine Learning (Isolation Forest)")
    st.markdown(
        "O modelo preditivo analisa o valor da transação cruzado com o horário e as tentativas. "
        "Veja como as anomalias se distanciam do padrão normal."
    )

    df["hora_int"] = pd.to_timedelta(df["hora"].astype(str), errors="coerce").dt.components.hours
    df["status_fraude"] = df["is_fraude"].replace({0: "Normal", 1: "Fraude"})
    df_plot = df.dropna(subset=["hora_int", "valor", "tentativas"])

    fig_ml = px.scatter(
        df_plot,
        x="hora_int",
        y="valor",
        color="status_fraude",
        size="tentativas",
        hover_data=["conta", "categoria", "cidade", "estabelecimento"],
        title="Dispersão de Anomalias: Horário vs Valor da Transação",
        labels={
            "hora_int": "Hora do Dia (0h - 23h)",
            "valor": "Valor da Transação (R$)",
            "status_fraude": "Classificação",
            "tentativas": "Nº de Tentativas",
        },
        color_discrete_map={"Normal": "#636efa", "Fraude": "#ef553b"},
        opacity=0.7,
    )
    st.plotly_chart(fig_ml, use_container_width=True)
    st.divider()

    st.subheader("⚠️ Alertas Aguardando Validação do Cliente")
    if "status_validacao" in df.columns:
        df_pendentes = df[df["status_validacao"] == "pendente"]
        if not df_pendentes.empty:
            colunas_exibicao = ["id", "conta", "valor", "data", "hora", "estabelecimento", "cidade"]
            st.dataframe(df_pendentes[colunas_exibicao], use_container_width=True)
        else:
            st.success("Nenhuma transação pendente de validação no momento!")
