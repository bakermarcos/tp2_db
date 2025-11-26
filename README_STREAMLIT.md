# 🏃 Dashboard Bolsa Atleta - Streamlit

Aplicativo web interativo para visualização e análise dos dados do banco de dados `bolsa_atleta.db`.

## 📋 Requisitos

- Python 3.8 ou superior
- Banco de dados `bolsa_atleta.db` no mesmo diretório do aplicativo

## 🚀 Instalação

1. Instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

Ou instale manualmente:

```bash
pip install streamlit pandas plotly
```

## ▶️ Como Executar

Execute o seguinte comando no terminal:

```bash
streamlit run app_streamlit.py
```

O aplicativo será aberto automaticamente no seu navegador em `http://localhost:8501`.

## 📊 Funcionalidades

O dashboard possui 7 páginas principais:

### 1. **Visão Geral**
- Estatísticas gerais do banco de dados
- Métricas principais (total de pagamentos, atletas, valores)
- Gráficos de distribuição de valores
- Evolução temporal de pagamentos
- Top 10 modalidades por valor total

### 2. **Análise por Categoria**
- Filtro por categoria de atleta
- Visualizações em pizza e barras
- Estatísticas detalhadas por categoria
- Tabela com dados agregados

### 3. **Análise por Modalidade**
- Filtro por modalidade esportiva
- Top 20 modalidades por valor total
- Gráfico de dispersão (atletas vs valor total)
- Análise detalhada por modalidade

### 4. **Análise por Região**
- Filtro por estado (UF)
- Visualização por município quando um estado é selecionado
- Gráficos de barras e pizza
- Distribuição geográfica dos pagamentos

### 5. **Análise Temporal**
- Agrupamento por Ano, Mês ou Ano-Mês
- Métricas: Quantidade de Pagamentos ou Valor Total
- Gráficos de linha e barras temporais
- Evolução dos pagamentos ao longo do tempo

### 6. **Busca de Atletas**
- Busca por nome do atleta
- Visualização de estatísticas do atleta
- Histórico completo de pagamentos
- Detalhamento de cada pagamento

### 7. **Dados Brutos**
- Visualização direta das tabelas do banco
- Seleção de tabela e número de linhas
- Estatísticas básicas das tabelas

## 🎨 Características

- ✅ Interface intuitiva e responsiva
- ✅ Gráficos interativos com Plotly
- ✅ Filtros dinâmicos
- ✅ Cache de dados para melhor performance
- ✅ Visualizações em tempo real

## 📁 Estrutura de Arquivos

```
tp2/
├── app_streamlit.py          # Aplicativo principal
├── bolsa_atleta.db           # Banco de dados SQLite
├── requirements.txt          # Dependências do projeto
└── README_STREAMLIT.md       # Este arquivo
```

## 🔧 Personalização

Você pode personalizar o aplicativo editando `app_streamlit.py`:

- Adicionar novas páginas na sidebar
- Criar novas visualizações
- Modificar queries SQL
- Alterar cores e estilos dos gráficos

## 📝 Notas

- O banco de dados deve estar no mesmo diretório do aplicativo
- Certifique-se de que o arquivo `bolsa_atleta.db` existe antes de executar
- Os dados são carregados em cache para melhor performance

## 🐛 Solução de Problemas

**Erro: "Banco de dados não encontrado"**
- Verifique se o arquivo `bolsa_atleta.db` está no mesmo diretório do `app_streamlit.py`

**Erro: "ModuleNotFoundError"**
- Execute `pip install -r requirements.txt` para instalar todas as dependências

**Aplicativo não abre no navegador**
- Acesse manualmente `http://localhost:8501` no seu navegador

