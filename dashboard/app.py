import streamlit as st
import pandas as pd
import plotly.express as px

from app.db.connection import get_connection


def build_dashboard() -> None:
    st.set_page_config(page_title="Dashboard Antifraude", page_icon="🛡️", layout="wide")
    st.title("🛡️ Painel de Controle Antifraude")
    st.markdown("Monitoramento de transações, alertas de Machine Learning e gestão de risco.")

    @st.cache_data(ttl=60)
    def carregar_dados() -> pd.DataFrame:
        conn = get_connection()
        try:
            return pd.read_sql("SELECT * FROM transacoes", conn)
        finally:
            conn.close()

    df = carregar_dados()

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
    st.markdown("O modelo preditivo analisa o valor da transação cruzado com o horário e as tentativas. Veja como as anomalias se distanciam do padrão normal.")

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

    st.subheader("⚠️ Alertas Aguardando Validação do Cliente (Épico 3)")
    if "status_validacao" in df.columns:
        df_pendentes = df[df["status_validacao"] == "pendente"]
        if not df_pendentes.empty:
            colunas_exibicao = ["id", "conta", "valor", "data", "hora", "estabelecimento", "cidade"]
            st.dataframe(df_pendentes[colunas_exibicao], use_container_width=True)
        else:
            st.success("Nenhuma transação pendente de validação no momento! 🎉")
