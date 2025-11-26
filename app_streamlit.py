import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Bolsa Atleta - Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Variável global para armazenar a conexão
_conn_cache = None

# Função para obter uma conexão válida
def get_valid_connection():
    """Retorna uma conexão válida ao banco de dados"""
    global _conn_cache
    
    # Verifica se a conexão existe e está válida
    if _conn_cache is not None:
        try:
            # Testa se a conexão ainda está válida
            _conn_cache.execute("SELECT 1")
            return _conn_cache
        except (sqlite3.ProgrammingError, sqlite3.OperationalError, sqlite3.InterfaceError):
            # Conexão inválida, fecha e recria
            try:
                _conn_cache.close()
            except:
                pass
            _conn_cache = None
    
    # Cria nova conexão
    db_path = Path('bolsa_atleta.db')
    if not db_path.exists():
        st.error(f"Banco de dados não encontrado: {db_path}")
        st.stop()
    
    _conn_cache = sqlite3.connect(str(db_path), check_same_thread=False)
    _conn_cache.execute("PRAGMA busy_timeout = 30000")
    return _conn_cache

# Função para conectar ao banco de dados (mantida para compatibilidade)
@st.cache_resource
def get_db_connection():
    """Conecta ao banco de dados SQLite"""
    return get_valid_connection()

# Função auxiliar para executar queries
def fetch_query(query: str, conn: sqlite3.Connection = None) -> pd.DataFrame:
    """Executa uma query SQL e retorna um DataFrame"""
    # Sempre usa uma conexão válida do cache global
    valid_conn = get_valid_connection()
    
    try:
        return pd.read_sql_query(query, valid_conn)
    except (sqlite3.ProgrammingError, sqlite3.OperationalError, sqlite3.InterfaceError) as e:
        # Se houver erro, limpa o cache e tenta novamente com uma nova conexão
        global _conn_cache
        try:
            if _conn_cache:
                _conn_cache.close()
        except:
            pass
        _conn_cache = None
        valid_conn = get_valid_connection()
        return pd.read_sql_query(query, valid_conn)

# Função para obter estatísticas gerais
@st.cache_data
def get_statistics(_conn):
    """Retorna estatísticas gerais do banco de dados"""
    stats = {}
    
    # Total de pagamentos
    stats['total_pagamentos'] = fetch_query('SELECT COUNT(*) as total FROM pagamento', _conn)['total'].iloc[0]
    
    # Total de atletas únicos
    stats['total_atletas'] = fetch_query('SELECT COUNT(DISTINCT cpf) as total FROM atleta', _conn)['total'].iloc[0]
    
    # Valor total pago
    stats['valor_total'] = fetch_query('SELECT SUM(valor_pago) as total FROM pagamento', _conn)['total'].iloc[0]
    
    # Valor médio por pagamento
    stats['valor_medio'] = stats['valor_total'] / stats['total_pagamentos'] if stats['total_pagamentos'] > 0 else 0
    
    # Total de modalidades
    stats['total_modalidades'] = fetch_query('SELECT COUNT(*) as total FROM modalidade', _conn)['total'].iloc[0]
    
    # Total de categorias
    stats['total_categorias'] = fetch_query('SELECT COUNT(*) as total FROM categoria', _conn)['total'].iloc[0]
    
    # Total de municípios
    stats['total_municipios'] = fetch_query('SELECT COUNT(*) as total FROM municipio', _conn)['total'].iloc[0]
    
    return stats

# Função helper para garantir conexão válida
def ensure_valid_connection(current_conn):
    """Garante que a conexão passada está válida, retorna uma nova se necessário"""
    if current_conn is None:
        return get_valid_connection()
    try:
        current_conn.execute("SELECT 1")
        return current_conn
    except (sqlite3.ProgrammingError, sqlite3.OperationalError, sqlite3.InterfaceError):
        return get_valid_connection()

# Conexão com o banco de dados (sempre obtém uma conexão válida)
conn = get_valid_connection()

# Sidebar para navegação e filtros
st.sidebar.title("📊 Navegação")
page = st.sidebar.radio(
    "Selecione uma página:",
    ["Visão Geral", "Análise por Categoria", "Análise por Modalidade", 
     "Análise por Região", "Análise Temporal", "Busca de Atletas", "Dados Brutos"]
)

st.sidebar.markdown("---")
st.sidebar.title("🔧 Filtros Globais")

# Carregar opções para filtros
@st.cache_data
def get_filter_options(_conn):
    """Carrega opções para os filtros"""
    categorias = fetch_query('SELECT categoria FROM categoria ORDER BY categoria', _conn)['categoria'].tolist()
    modalidades = fetch_query('SELECT modalidade FROM modalidade ORDER BY modalidade', _conn)['modalidade'].tolist()
    estados = fetch_query('SELECT DISTINCT uf FROM municipio ORDER BY uf', _conn)['uf'].tolist()
    
    # Obter range de datas
    min_date = fetch_query('SELECT MIN(data_pagamento) as min_date FROM pagamento WHERE data_pagamento IS NOT NULL', _conn)['min_date'].iloc[0]
    max_date = fetch_query('SELECT MAX(data_pagamento) as max_date FROM pagamento WHERE data_pagamento IS NOT NULL', _conn)['max_date'].iloc[0]
    
    return {
        'categorias': categorias,
        'modalidades': modalidades,
        'estados': estados,
        'min_date': min_date,
        'max_date': max_date
    }

filter_options = get_filter_options(conn)

# Filtros configuráveis
st.sidebar.subheader("Filtros de Dados")

# Filtro de categoria
filtro_categoria = st.sidebar.multiselect(
    "Categorias:",
    options=filter_options['categorias'],
    default=[],
    help="Selecione as categorias para filtrar (deixe vazio para todas)"
)

# Filtro de modalidade
filtro_modalidade = st.sidebar.multiselect(
    "Modalidades:",
    options=filter_options['modalidades'],
    default=[],
    help="Selecione as modalidades para filtrar (deixe vazio para todas)"
)

# Filtro de estado
filtro_estado = st.sidebar.multiselect(
    "Estados (UF):",
    options=filter_options['estados'],
    default=[],
    help="Selecione os estados para filtrar (deixe vazio para todos)"
)

# Filtro de período
st.sidebar.subheader("Período")
use_date_filter = st.sidebar.checkbox("Filtrar por período", value=False, help="Marque para ativar filtro de datas")

if use_date_filter:
    filtro_data_inicio = st.sidebar.date_input(
        "Data Início:",
        value=pd.to_datetime(filter_options['min_date']).date() if filter_options['min_date'] else None,
        min_value=pd.to_datetime(filter_options['min_date']).date() if filter_options['min_date'] else None,
        max_value=pd.to_datetime(filter_options['max_date']).date() if filter_options['max_date'] else None,
        help="Data inicial do período"
    )
    
    filtro_data_fim = st.sidebar.date_input(
        "Data Fim:",
        value=pd.to_datetime(filter_options['max_date']).date() if filter_options['max_date'] else None,
        min_value=pd.to_datetime(filter_options['min_date']).date() if filter_options['min_date'] else None,
        max_value=pd.to_datetime(filter_options['max_date']).date() if filter_options['max_date'] else None,
        help="Data final do período"
    )
else:
    filtro_data_inicio = None
    filtro_data_fim = None

# Filtro de valor
st.sidebar.subheader("Valor")
use_value_filter = st.sidebar.checkbox("Filtrar por valor", value=False, help="Marque para ativar filtro de valores")

if use_value_filter:
    filtro_valor_min = st.sidebar.number_input(
        "Valor Mínimo (R$):",
        min_value=0.0,
        value=0.0,
        step=100.0,
        help="Valor mínimo do pagamento"
    )
    
    filtro_valor_max = st.sidebar.number_input(
        "Valor Máximo (R$):",
        min_value=0.0,
        value=0.0,
        step=100.0,
        help="Valor máximo do pagamento (0 = sem limite)"
    )
else:
    filtro_valor_min = 0.0
    filtro_valor_max = 0.0

# Função para construir cláusula WHERE baseada nos filtros
def build_where_clause():
    """Constrói cláusula WHERE baseada nos filtros selecionados"""
    conditions = []
    
    if filtro_categoria:
        cats = "', '".join(filtro_categoria)
        conditions.append(f"c.categoria IN ('{cats}')")
    
    if filtro_modalidade:
        mods = "', '".join(filtro_modalidade)
        conditions.append(f"m.modalidade IN ('{mods}')")
    
    if filtro_estado:
        ufs = "', '".join(filtro_estado)
        conditions.append(f"mu.uf IN ('{ufs}')")
    
    # Só aplica filtros de data se o checkbox estiver marcado
    if use_date_filter:
        if filtro_data_inicio:
            conditions.append(f"p.data_pagamento >= '{filtro_data_inicio}'")
        
        if filtro_data_fim:
            conditions.append(f"p.data_pagamento <= '{filtro_data_fim}'")
    
    # Só aplica filtros de valor se o checkbox estiver marcado
    if use_value_filter:
        if filtro_valor_min > 0:
            conditions.append(f"p.valor_pago >= {filtro_valor_min}")
        
        if filtro_valor_max > 0:
            conditions.append(f"p.valor_pago <= {filtro_valor_max}")
    
    return " AND ".join(conditions) if conditions else None

# Botão para limpar filtros
if st.sidebar.button("🔄 Limpar Filtros"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Dica:** Use os filtros acima para personalizar as visualizações em todas as páginas.")

# Título principal
st.title("🏃 Dashboard - Bolsa Atleta")
st.markdown("---")

# ========== PÁGINA 1: VISÃO GERAL (DASHBOARD COMPLETO) ==========
if page == "Visão Geral":
    st.header("📈 Dashboard Executivo - Bolsa Atleta")
    
    # Aplicar filtros na query
    where_clause = build_where_clause()
    join_clause = """
    FROM pagamento p
    JOIN categoria c ON p.id_categoria = c.id_categoria
    JOIN modalidade m ON p.id_modalidade = m.id_modalidade
    JOIN atleta a ON p.cpf = a.cpf
    JOIN municipio mu ON a.id_municipio = mu.id_municipio
    """
    
    if where_clause:
        base_query = f"SELECT * {join_clause} WHERE {where_clause}"
    else:
        base_query = f"SELECT * {join_clause}"
    
    # Garantir que temos uma conexão válida antes de executar queries
    conn = ensure_valid_connection(conn)
    
    # Obter estatísticas com filtros
    if where_clause:
        query_stats = f"""
        SELECT 
            COUNT(*) as total_pagamentos,
            COUNT(DISTINCT p.cpf) as total_atletas,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        {join_clause}
        WHERE {where_clause}
        """
    else:
        query_stats = """
        SELECT 
            COUNT(*) as total_pagamentos,
            COUNT(DISTINCT p.cpf) as total_atletas,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        """
    
    df_stats = fetch_query(query_stats, conn)
    stats = {
        'total_pagamentos': int(df_stats['total_pagamentos'].iloc[0]) if not df_stats.empty else 0,
        'total_atletas': int(df_stats['total_atletas'].iloc[0]) if not df_stats.empty else 0,
        'valor_total': float(df_stats['valor_total'].iloc[0]) if not df_stats.empty and pd.notna(df_stats['valor_total'].iloc[0]) else 0.0,
        'valor_medio': float(df_stats['valor_medio'].iloc[0]) if not df_stats.empty and pd.notna(df_stats['valor_medio'].iloc[0]) else 0.0
    }
    
    # Métricas principais com cards destacados
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Total de Pagamentos",
            value=f"{stats['total_pagamentos']:,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="👥 Total de Atletas",
            value=f"{stats['total_atletas']:,}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="💵 Valor Total Pago",
            value=f"R$ {stats['valor_total']:,.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            label="📊 Valor Médio",
            value=f"R$ {stats['valor_medio']:,.2f}",
            delta=None
        )
    
    st.markdown("---")
    
    # Primeira linha de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Distribuição de Valores Pagos")
        if where_clause:
            query_valores = f"""
            SELECT 
                CASE 
                    WHEN p.valor_pago < 1000 THEN 'Até R$ 1.000'
                    WHEN p.valor_pago < 2000 THEN 'R$ 1.000 - R$ 2.000'
                    WHEN p.valor_pago < 3000 THEN 'R$ 2.000 - R$ 3.000'
                    WHEN p.valor_pago < 5000 THEN 'R$ 3.000 - R$ 5.000'
                    ELSE 'Acima de R$ 5.000'
                END as faixa_valor,
                COUNT(*) as quantidade
            {join_clause}
            WHERE {where_clause}
            GROUP BY faixa_valor
            ORDER BY MIN(p.valor_pago)
            """
        else:
            query_valores = """
            SELECT 
                CASE 
                    WHEN valor_pago < 1000 THEN 'Até R$ 1.000'
                    WHEN valor_pago < 2000 THEN 'R$ 1.000 - R$ 2.000'
                    WHEN valor_pago < 3000 THEN 'R$ 2.000 - R$ 3.000'
                    WHEN valor_pago < 5000 THEN 'R$ 3.000 - R$ 5.000'
                    ELSE 'Acima de R$ 5.000'
                END as faixa_valor,
                COUNT(*) as quantidade
            FROM pagamento
            GROUP BY faixa_valor
            ORDER BY MIN(valor_pago)
            """
        df_valores = fetch_query(query_valores, conn)
        if not df_valores.empty:
            fig_valores = px.bar(df_valores, x='faixa_valor', y='quantidade', 
                                title="Pagamentos por Faixa de Valor",
                                labels={'faixa_valor': 'Faixa de Valor', 'quantidade': 'Quantidade'},
                                color='quantidade',
                                color_continuous_scale='Blues')
            fig_valores.update_layout(height=400)
            st.plotly_chart(fig_valores, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    with col2:
        st.subheader("💵 Valor Médio por Categoria")
        if where_clause:
            query_valor_medio = f"""
            SELECT 
                c.categoria,
                AVG(p.valor_pago) as valor_medio,
                COUNT(p.id_pagamento) as num_pagamentos
            {join_clause}
            WHERE {where_clause}
            GROUP BY c.categoria
            ORDER BY valor_medio DESC
            """
        else:
            query_valor_medio = """
            SELECT 
                c.categoria,
                AVG(p.valor_pago) as valor_medio,
                COUNT(p.id_pagamento) as num_pagamentos
            FROM pagamento p
            JOIN categoria c ON p.id_categoria = c.id_categoria
            GROUP BY c.categoria
            ORDER BY valor_medio DESC
            """
        df_valor_medio = fetch_query(query_valor_medio, conn)
        if not df_valor_medio.empty:
            fig_valor_medio = px.bar(df_valor_medio, x='categoria', y='valor_medio',
                                     title="Valor Médio de Pagamento por Categoria",
                                     labels={'categoria': 'Categoria', 'valor_medio': 'Valor Médio (R$)'},
                                     color='valor_medio',
                                     color_continuous_scale='Greens',
                                     text='valor_medio')
            fig_valor_medio.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
            fig_valor_medio.update_xaxes(tickangle=45)
            fig_valor_medio.update_layout(height=400)
            st.plotly_chart(fig_valor_medio, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    st.markdown("---")
    
    # Segunda linha de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏅 Top 10 Modalidades por Valor Total")
        if where_clause:
            query_top_modalidades = f"""
            SELECT 
                m.modalidade,
                COUNT(p.id_pagamento) as num_pagamentos,
                SUM(p.valor_pago) as valor_total
            {join_clause}
            WHERE {where_clause}
            GROUP BY m.modalidade
            ORDER BY valor_total DESC
            LIMIT 10
            """
        else:
            query_top_modalidades = """
            SELECT 
                m.modalidade,
                COUNT(p.id_pagamento) as num_pagamentos,
                SUM(p.valor_pago) as valor_total
            FROM pagamento p
            JOIN modalidade m ON p.id_modalidade = m.id_modalidade
            GROUP BY m.modalidade
            ORDER BY valor_total DESC
            LIMIT 10
            """
        df_top_modalidades = fetch_query(query_top_modalidades, conn)
        if not df_top_modalidades.empty:
            fig_top_modalidades = px.bar(df_top_modalidades, x='modalidade', y='valor_total',
                                        title="Top 10 Modalidades",
                                        labels={'modalidade': 'Modalidade', 'valor_total': 'Valor Total (R$)'},
                                        color='valor_total',
                                        color_continuous_scale='Viridis')
            fig_top_modalidades.update_xaxes(tickangle=45)
            fig_top_modalidades.update_layout(height=400)
            st.plotly_chart(fig_top_modalidades, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    with col2:
        st.subheader("📊 Distribuição por Categoria")
        if where_clause:
            query_cat = f"""
            SELECT 
                c.categoria,
                COUNT(p.id_pagamento) as num_pagamentos,
                SUM(p.valor_pago) as valor_total
            {join_clause}
            WHERE {where_clause}
            GROUP BY c.categoria
            ORDER BY valor_total DESC
            """
        else:
            query_cat = """
            SELECT 
                c.categoria,
                COUNT(p.id_pagamento) as num_pagamentos,
                SUM(p.valor_pago) as valor_total
            FROM pagamento p
            JOIN categoria c ON p.id_categoria = c.id_categoria
            GROUP BY c.categoria
            ORDER BY valor_total DESC
            """
        df_cat = fetch_query(query_cat, conn)
        if not df_cat.empty:
            fig_cat = px.pie(df_cat, values='valor_total', names='categoria',
                            title="Distribuição de Valores por Categoria",
                            hole=0.4)
            fig_cat.update_layout(height=400)
            st.plotly_chart(fig_cat, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    st.markdown("---")
    
    # Terceira linha de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🗺️ Top 10 Estados por Valor Total")
        if where_clause:
            query_estados = f"""
            SELECT 
                mu.uf,
                COUNT(DISTINCT a.cpf) as num_atletas,
                SUM(p.valor_pago) as valor_total
            {join_clause}
            WHERE {where_clause}
            GROUP BY mu.uf
            ORDER BY valor_total DESC
            LIMIT 10
            """
        else:
            query_estados = """
            SELECT 
                mu.uf,
                COUNT(DISTINCT a.cpf) as num_atletas,
                SUM(p.valor_pago) as valor_total
            FROM pagamento p
            JOIN atleta a ON p.cpf = a.cpf
            JOIN municipio mu ON a.id_municipio = mu.id_municipio
            GROUP BY mu.uf
            ORDER BY valor_total DESC
            LIMIT 10
            """
        df_estados = fetch_query(query_estados, conn)
        if not df_estados.empty:
            fig_estados = px.bar(df_estados, x='uf', y='valor_total',
                                title="Top 10 Estados",
                                labels={'uf': 'Estado', 'valor_total': 'Valor Total (R$)'},
                                color='num_atletas',
                                color_continuous_scale='Reds')
            fig_estados.update_layout(height=400)
            st.plotly_chart(fig_estados, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    with col2:
        st.subheader("🏆 Top 10 Municípios por Valor Total")
        if where_clause:
            query_municipios = f"""
            SELECT 
                mu.municipio || ' - ' || mu.uf as localizacao,
                COUNT(DISTINCT a.cpf) as num_atletas,
                SUM(p.valor_pago) as valor_total
            {join_clause}
            WHERE {where_clause}
            GROUP BY mu.municipio, mu.uf
            ORDER BY valor_total DESC
            LIMIT 10
            """
        else:
            query_municipios = """
            SELECT 
                mu.municipio || ' - ' || mu.uf as localizacao,
                COUNT(DISTINCT a.cpf) as num_atletas,
                SUM(p.valor_pago) as valor_total
            FROM pagamento p
            JOIN atleta a ON p.cpf = a.cpf
            JOIN municipio mu ON a.id_municipio = mu.id_municipio
            GROUP BY mu.municipio, mu.uf
            ORDER BY valor_total DESC
            LIMIT 10
            """
        df_municipios = fetch_query(query_municipios, conn)
        if not df_municipios.empty:
            fig_municipios = px.bar(df_municipios, x='valor_total', y='localizacao',
                                   orientation='h',
                                   title="Top 10 Municípios por Valor Total",
                                   labels={'localizacao': 'Município - UF', 'valor_total': 'Valor Total (R$)'},
                                   color='num_atletas',
                                   color_continuous_scale='Oranges')
            fig_municipios.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_municipios, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    st.markdown("---")
    
    # Quarta linha - Comparação de modalidades e distribuição geográfica
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Comparação: Modalidades com Mais Atletas")
        if where_clause:
            query_modalidades_atletas = f"""
            SELECT 
                m.modalidade,
                COUNT(DISTINCT p.cpf) as num_atletas,
                SUM(p.valor_pago) as valor_total,
                AVG(p.valor_pago) as valor_medio
            {join_clause}
            WHERE {where_clause}
            GROUP BY m.modalidade
            ORDER BY num_atletas DESC
            LIMIT 10
            """
        else:
            query_modalidades_atletas = """
            SELECT 
                m.modalidade,
                COUNT(DISTINCT p.cpf) as num_atletas,
                SUM(p.valor_pago) as valor_total,
                AVG(p.valor_pago) as valor_medio
            FROM pagamento p
            JOIN modalidade m ON p.id_modalidade = m.id_modalidade
            GROUP BY m.modalidade
            ORDER BY num_atletas DESC
            LIMIT 10
            """
        df_modalidades_atletas = fetch_query(query_modalidades_atletas, conn)
        if not df_modalidades_atletas.empty:
            fig_modalidades = px.bar(df_modalidades_atletas, x='modalidade', y='num_atletas',
                                    title="Top 10 Modalidades por Número de Atletas",
                                    labels={'modalidade': 'Modalidade', 'num_atletas': 'Número de Atletas'},
                                    color='valor_total',
                                    color_continuous_scale='Purples',
                                    text='num_atletas')
            fig_modalidades.update_traces(texttemplate='%{text}', textposition='outside')
            fig_modalidades.update_xaxes(tickangle=45)
            fig_modalidades.update_layout(height=400)
            st.plotly_chart(fig_modalidades, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    with col2:
        st.subheader("🗺️ Distribuição Geográfica por Estado")
        if where_clause:
            query_dist_geo = f"""
            SELECT 
                mu.uf,
                COUNT(DISTINCT a.cpf) as num_atletas,
                COUNT(p.id_pagamento) as num_pagamentos,
                SUM(p.valor_pago) as valor_total
            {join_clause}
            WHERE {where_clause}
            GROUP BY mu.uf
            ORDER BY valor_total DESC
            """
        else:
            query_dist_geo = """
            SELECT 
                mu.uf,
                COUNT(DISTINCT a.cpf) as num_atletas,
                COUNT(p.id_pagamento) as num_pagamentos,
                SUM(p.valor_pago) as valor_total
            FROM pagamento p
            JOIN atleta a ON p.cpf = a.cpf
            JOIN municipio mu ON a.id_municipio = mu.id_municipio
            GROUP BY mu.uf
            ORDER BY valor_total DESC
            """
        df_dist_geo = fetch_query(query_dist_geo, conn)
        if not df_dist_geo.empty:
            fig_dist_geo = px.treemap(df_dist_geo, 
                                      path=['uf'], 
                                      values='valor_total',
                                      color='num_atletas',
                                      title="Distribuição de Valores por Estado",
                                      color_continuous_scale='RdBu',
                                      hover_data=['num_atletas', 'num_pagamentos'])
            fig_dist_geo.update_layout(height=400)
            st.plotly_chart(fig_dist_geo, width='stretch')
        else:
            st.info("📊 Nenhum dado encontrado para esta visualização com os filtros aplicados.")
    
    st.markdown("---")
    
    # Tabela resumo
    st.subheader("📋 Resumo Detalhado")
    if where_clause:
        query_resumo = f"""
        SELECT 
            c.categoria,
            m.modalidade,
            mu.uf,
            COUNT(DISTINCT p.cpf) as num_atletas,
            COUNT(p.id_pagamento) as num_pagamentos,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        {join_clause}
        WHERE {where_clause}
        GROUP BY c.categoria, m.modalidade, mu.uf
        ORDER BY valor_total DESC
        LIMIT 50
        """
    else:
        query_resumo = """
        SELECT 
            c.categoria,
            m.modalidade,
            mu.uf,
            COUNT(DISTINCT p.cpf) as num_atletas,
            COUNT(p.id_pagamento) as num_pagamentos,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN categoria c ON p.id_categoria = c.id_categoria
        JOIN modalidade m ON p.id_modalidade = m.id_modalidade
        JOIN atleta a ON p.cpf = a.cpf
        JOIN municipio mu ON a.id_municipio = mu.id_municipio
        GROUP BY c.categoria, m.modalidade, mu.uf
        ORDER BY valor_total DESC
        LIMIT 50
        """
    df_resumo = fetch_query(query_resumo, conn)
    if not df_resumo.empty:
        # Formatar valores para exibição
        df_resumo['valor_total'] = df_resumo['valor_total'].apply(lambda x: f"R$ {x:,.2f}")
        df_resumo['valor_medio'] = df_resumo['valor_medio'].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_resumo, width='stretch', height=400)

# ========== PÁGINA 2: ANÁLISE POR CATEGORIA ==========
elif page == "Análise por Categoria":
    st.header("📊 Análise por Categoria")
    
    # Obter todas as categorias
    categorias = fetch_query('SELECT categoria FROM categoria ORDER BY categoria', conn)['categoria'].tolist()
    
    # Filtros
    categoria_selecionada = st.selectbox("Selecione uma categoria:", ["Todas"] + categorias)
    
    # Query base
    if categoria_selecionada == "Todas":
        query_categoria = """
        SELECT 
            c.categoria,
            COUNT(p.id_pagamento) as num_pagamentos,
            COUNT(DISTINCT p.cpf) as num_atletas,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN categoria c ON p.id_categoria = c.id_categoria
        GROUP BY c.categoria
        ORDER BY valor_total DESC
        """
    else:
        query_categoria = f"""
        SELECT 
            c.categoria,
            COUNT(p.id_pagamento) as num_pagamentos,
            COUNT(DISTINCT p.cpf) as num_atletas,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN categoria c ON p.id_categoria = c.id_categoria
        WHERE c.categoria = '{categoria_selecionada}'
        GROUP BY c.categoria
        """
    
    df_categoria = fetch_query(query_categoria, conn)
    
    # Métricas
    if not df_categoria.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pagamentos", f"{df_categoria['num_pagamentos'].sum():,}")
        with col2:
            st.metric("Atletas", f"{df_categoria['num_atletas'].sum():,}")
        with col3:
            st.metric("Valor Total", f"R$ {df_categoria['valor_total'].sum():,.2f}")
        with col4:
            st.metric("Valor Médio", f"R$ {df_categoria['valor_medio'].mean():,.2f}")
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pizza = px.pie(df_categoria, values='valor_total', names='categoria',
                              title="Distribuição de Valores por Categoria")
            st.plotly_chart(fig_pizza, width='stretch')
        
        with col2:
            fig_barra = px.bar(df_categoria, x='categoria', y='num_atletas',
                              title="Número de Atletas por Categoria",
                              labels={'categoria': 'Categoria', 'num_atletas': 'Número de Atletas'})
            fig_barra.update_xaxes(tickangle=45)
            st.plotly_chart(fig_barra, width='stretch')
        
        # Tabela detalhada
        st.subheader("📋 Detalhamento")
        st.dataframe(df_categoria, width='stretch')

# ========== PÁGINA 3: ANÁLISE POR MODALIDADE ==========
elif page == "Análise por Modalidade":
    st.header("🏅 Análise por Modalidade")
    
    # Obter todas as modalidades
    modalidades = fetch_query('SELECT modalidade FROM modalidade ORDER BY modalidade', conn)['modalidade'].tolist()
    
    # Filtros
    modalidade_selecionada = st.selectbox("Selecione uma modalidade:", ["Todas"] + modalidades)
    
    # Query base
    if modalidade_selecionada == "Todas":
        query_modalidade = """
        SELECT 
            m.modalidade,
            COUNT(p.id_pagamento) as num_pagamentos,
            COUNT(DISTINCT p.cpf) as num_atletas,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN modalidade m ON p.id_modalidade = m.id_modalidade
        GROUP BY m.modalidade
        ORDER BY valor_total DESC
        """
    else:
        query_modalidade = f"""
        SELECT 
            m.modalidade,
            COUNT(p.id_pagamento) as num_pagamentos,
            COUNT(DISTINCT p.cpf) as num_atletas,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN modalidade m ON p.id_modalidade = m.id_modalidade
        WHERE m.modalidade = '{modalidade_selecionada}'
        GROUP BY m.modalidade
        """
    
    df_modalidade = fetch_query(query_modalidade, conn)
    
    # Métricas
    if not df_modalidade.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pagamentos", f"{df_modalidade['num_pagamentos'].sum():,}")
        with col2:
            st.metric("Atletas", f"{df_modalidade['num_atletas'].sum():,}")
        with col3:
            st.metric("Valor Total", f"R$ {df_modalidade['valor_total'].sum():,.2f}")
        with col4:
            st.metric("Valor Médio", f"R$ {df_modalidade['valor_medio'].mean():,.2f}")
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            # Top 20 modalidades
            df_top20 = df_modalidade.head(20)
            fig_barra = px.bar(df_top20, x='modalidade', y='valor_total',
                              title="Top 20 Modalidades por Valor Total",
                              labels={'modalidade': 'Modalidade', 'valor_total': 'Valor Total (R$)'})
            fig_barra.update_xaxes(tickangle=45)
            st.plotly_chart(fig_barra, width='stretch')
        
        with col2:
            fig_scatter = px.scatter(df_modalidade, x='num_atletas', y='valor_total',
                                    size='num_pagamentos', hover_name='modalidade',
                                    title="Relação: Atletas vs Valor Total",
                                    labels={'num_atletas': 'Número de Atletas', 
                                           'valor_total': 'Valor Total (R$)'})
            st.plotly_chart(fig_scatter, width='stretch')
        
        # Tabela detalhada
        st.subheader("📋 Detalhamento")
        st.dataframe(df_modalidade, width='stretch')

# ========== PÁGINA 4: ANÁLISE POR REGIÃO ==========
elif page == "Análise por Região":
    st.header("🗺️ Análise por Região")
    
    # Obter todos os estados
    estados = fetch_query('SELECT DISTINCT uf FROM municipio ORDER BY uf', conn)['uf'].tolist()
    
    # Filtros
    estado_selecionado = st.selectbox("Selecione um estado:", ["Todos"] + estados)
    
    # Query base
    if estado_selecionado == "Todos":
        query_regiao = """
        SELECT 
            mu.uf,
            COUNT(DISTINCT mu.id_municipio) as num_municipios,
            COUNT(DISTINCT a.cpf) as num_atletas,
            COUNT(p.id_pagamento) as num_pagamentos,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN atleta a ON p.cpf = a.cpf
        JOIN municipio mu ON a.id_municipio = mu.id_municipio
        GROUP BY mu.uf
        ORDER BY valor_total DESC
        """
    else:
        query_regiao = f"""
        SELECT 
            mu.uf,
            mu.municipio,
            COUNT(DISTINCT a.cpf) as num_atletas,
            COUNT(p.id_pagamento) as num_pagamentos,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio
        FROM pagamento p
        JOIN atleta a ON p.cpf = a.cpf
        JOIN municipio mu ON a.id_municipio = mu.id_municipio
        WHERE mu.uf = '{estado_selecionado}'
        GROUP BY mu.uf, mu.municipio
        ORDER BY valor_total DESC
        """
    
    df_regiao = fetch_query(query_regiao, conn)
    
    # Métricas
    if not df_regiao.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Municípios", f"{df_regiao['num_municipios'].sum() if 'num_municipios' in df_regiao.columns else len(df_regiao):,}")
        with col2:
            st.metric("Atletas", f"{df_regiao['num_atletas'].sum():,}")
        with col3:
            st.metric("Valor Total", f"R$ {df_regiao['valor_total'].sum():,.2f}")
        with col4:
            st.metric("Valor Médio", f"R$ {df_regiao['valor_medio'].mean():,.2f}")
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            if estado_selecionado == "Todos":
                fig_barra = px.bar(df_regiao, x='uf', y='valor_total',
                                  title="Valor Total por Estado",
                                  labels={'uf': 'Estado', 'valor_total': 'Valor Total (R$)'})
            else:
                df_top20_mun = df_regiao.head(20)
                fig_barra = px.bar(df_top20_mun, x='municipio', y='valor_total',
                                  title=f"Top 20 Municípios em {estado_selecionado}",
                                  labels={'municipio': 'Município', 'valor_total': 'Valor Total (R$)'})
            fig_barra.update_xaxes(tickangle=45)
            st.plotly_chart(fig_barra, width='stretch')
        
        with col2:
            if estado_selecionado == "Todos":
                fig_pizza = px.pie(df_regiao, values='num_atletas', names='uf',
                                  title="Distribuição de Atletas por Estado")
            else:
                df_top10_mun = df_regiao.head(10)
                fig_pizza = px.pie(df_top10_mun, values='num_atletas', names='municipio',
                                  title=f"Top 10 Municípios em {estado_selecionado}")
            st.plotly_chart(fig_pizza, width='stretch')
        
        # Tabela detalhada
        st.subheader("📋 Detalhamento")
        st.dataframe(df_regiao, width='stretch')

# ========== PÁGINA 5: ANÁLISE TEMPORAL ==========
elif page == "Análise Temporal":
    st.header("📅 Análise Temporal")
    
    # Filtros temporais
    col1, col2 = st.columns(2)
    with col1:
        tipo_agrupamento = st.selectbox("Agrupar por:", ["Ano", "Mês", "Ano-Mês"])
    with col2:
        metrica = st.selectbox("Métrica:", ["Quantidade de Pagamentos", "Valor Total"])
    
    # Query base
    if tipo_agrupamento == "Ano":
        formato_data = "strftime('%Y', data_pagamento)"
        label_data = "ano"
    elif tipo_agrupamento == "Mês":
        formato_data = "strftime('%m', data_pagamento)"
        label_data = "mes"
    else:
        formato_data = "strftime('%Y-%m', data_pagamento)"
        label_data = "ano_mes"
    
    if metrica == "Quantidade de Pagamentos":
        campo_metrica = "COUNT(*) as valor"
    else:
        campo_metrica = "SUM(valor_pago) as valor"
    
    query_temporal = f"""
    SELECT 
        {formato_data} as periodo,
        COUNT(*) as num_pagamentos,
        SUM(valor_pago) as valor_total,
        AVG(valor_pago) as valor_medio,
        COUNT(DISTINCT cpf) as num_atletas
    FROM pagamento
    WHERE data_pagamento IS NOT NULL
    GROUP BY periodo
    ORDER BY periodo
    """
    
    df_temporal = fetch_query(query_temporal, conn)
    
    if not df_temporal.empty:
        # Gráfico de linha temporal
        campo_grafico = 'valor_total' if metrica == "Valor Total" else 'num_pagamentos'
        titulo_grafico = f"Evolução {metrica} ao Longo do Tempo"
        
        fig_temporal = px.line(df_temporal, x='periodo', y=campo_grafico,
                              title=titulo_grafico,
                              labels={'periodo': 'Período', campo_grafico: metrica})
        st.plotly_chart(fig_temporal, width='stretch')
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Períodos", len(df_temporal))
        with col2:
            st.metric("Total de Pagamentos", f"{df_temporal['num_pagamentos'].sum():,}")
        with col3:
            st.metric("Valor Total", f"R$ {df_temporal['valor_total'].sum():,.2f}")
        with col4:
            st.metric("Valor Médio", f"R$ {df_temporal['valor_medio'].mean():,.2f}")
        
        st.markdown("---")
        
        # Gráfico de barras
        fig_barras = px.bar(df_temporal, x='periodo', y=campo_grafico,
                           title=f"{metrica} por Período",
                           labels={'periodo': 'Período', campo_grafico: metrica})
        fig_barras.update_xaxes(tickangle=45)
        st.plotly_chart(fig_barras, width='stretch')
        
        # Tabela detalhada
        st.subheader("📋 Detalhamento")
        st.dataframe(df_temporal, width='stretch')

# ========== PÁGINA 6: BUSCA DE ATLETAS ==========
elif page == "Busca de Atletas":
    st.header("🔍 Busca de Atletas")
    
    # Campo de busca
    busca = st.text_input("Digite o nome do atleta (ou parte do nome):", "")
    
    if busca:
        query_busca = f"""
        SELECT 
            a.nome,
            a.cpf,
            mu.municipio,
            mu.uf,
            COUNT(p.id_pagamento) as num_pagamentos,
            SUM(p.valor_pago) as valor_total,
            AVG(p.valor_pago) as valor_medio,
            MIN(p.data_pagamento) as primeira_data,
            MAX(p.data_pagamento) as ultima_data
        FROM atleta a
        JOIN municipio mu ON a.id_municipio = mu.id_municipio
        LEFT JOIN pagamento p ON a.cpf = p.cpf
        WHERE a.nome LIKE '%{busca}%'
        GROUP BY a.cpf, a.nome, mu.municipio, mu.uf
        ORDER BY valor_total DESC
        LIMIT 100
        """
        
        df_busca = fetch_query(query_busca, conn)
        
        if not df_busca.empty:
            st.success(f"Encontrados {len(df_busca)} atleta(s)")
            
            # Selecionar atleta para detalhamento
            atleta_selecionado = st.selectbox("Selecione um atleta para ver detalhes:",
                                             df_busca['nome'].tolist())
            
            if atleta_selecionado:
                cpf_atleta = df_busca[df_busca['nome'] == atleta_selecionado]['cpf'].iloc[0]
                
                # Detalhes do atleta
                query_detalhes = f"""
                SELECT 
                    p.data_pagamento,
                    p.data_referencia,
                    c.categoria,
                    m.modalidade,
                    s.situacao,
                    p.valor_pago,
                    e.id_edital as edital
                FROM pagamento p
                JOIN categoria c ON p.id_categoria = c.id_categoria
                JOIN modalidade m ON p.id_modalidade = m.id_modalidade
                JOIN situacao s ON p.id_situacao = s.id_situacao
                JOIN edital e ON p.id_edital = e.id_edital
                WHERE p.cpf = '{cpf_atleta}'
                ORDER BY p.data_pagamento DESC
                """
                
                df_detalhes = fetch_query(query_detalhes, conn)
                
                st.subheader(f"Detalhes de {atleta_selecionado}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Pagamentos", len(df_detalhes))
                with col2:
                    st.metric("Valor Total Recebido", f"R$ {df_detalhes['valor_pago'].sum():,.2f}")
                with col3:
                    st.metric("Valor Médio", f"R$ {df_detalhes['valor_pago'].mean():,.2f}")
                
                st.dataframe(df_detalhes, width='stretch')
        else:
            st.warning("Nenhum atleta encontrado com esse nome.")
    else:
        st.info("Digite um nome para buscar atletas.")

# ========== PÁGINA 7: DADOS BRUTOS ==========
elif page == "Dados Brutos":
    st.header("📄 Dados Brutos")
    
    # Selecionar tabela
    tabelas = ['pagamento', 'atleta', 'categoria', 'modalidade', 'municipio', 'situacao', 'edital']
    tabela_selecionada = st.selectbox("Selecione uma tabela:", tabelas)
    
    # Número de linhas
    num_linhas = st.slider("Número de linhas:", 10, 1000, 100)
    
    # Query
    query_dados = f"SELECT * FROM {tabela_selecionada} LIMIT {num_linhas}"
    df_dados = fetch_query(query_dados, conn)
    
    st.subheader(f"Dados da tabela: {tabela_selecionada}")
    st.dataframe(df_dados, width='stretch')
    
    # Estatísticas da tabela
    st.subheader("Estatísticas")
    st.write(f"Total de linhas exibidas: {len(df_dados)}")
    st.write(f"Total de colunas: {len(df_dados.columns)}")

# Nota: A conexão é gerenciada automaticamente pelo @st.cache_resource
# Não precisamos fechá-la manualmente

