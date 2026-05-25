# 📋 Guia de Execução da Aplicação

Após reorganizar o projeto, use os scripts abaixo para executar as diferentes funcionalidades:

## 🚀 Opção 1: Executar a API FastAPI

```bash
python scripts/run_api.py
```

Acesso: `http://localhost:8000`
Documentação: `http://localhost:8000/docs`

## 📊 Opção 2: Executar o Dashboard Streamlit

```bash
python scripts/run_dashboard.py
```

Acesso: `http://localhost:8501`

## 🔄 Opção 3: Reavaliação de Fraude

Reavalia todas as transações usando regras de negócio e Machine Learning:

```bash
python scripts/run_recalcular.py
```

**Nota:** Este processo é automático no startup da API, mas pode ser executado manualmente.

## 📥 Opção 4: Importar Dados

Importa dados JSON para o banco de dados (se ainda não importados):

```bash
python scripts/run_import.py
```

**Nota:** Este processo é automático no startup da API se a tabela estiver vazia.

---

## 📁 Estrutura do Projeto

```
app/
├── jobs/                    ← Jobs e tasks (recalcular, importar, etc)
│   ├── recalcular_fraude.py
│   └── importar_dados.py
├── api/routers/            ← Rotas FastAPI
├── services/               ← Lógica de negócio
├── repositories/           ← Acesso a dados
├── domain/                 ← Regras de negócio (fraude, ML)
├── db/                     ← Configuração do banco
├── core/                   ← Configurações globais
└── main.py                 ← Entry point da API

scripts/                    ← Scripts de execução
├── run_api.py
├── run_dashboard.py
├── run_recalcular.py
└── run_import.py

dashboard/                  ← Dashboard Streamlit
└── app.py

myapi.py                    ← FastAPI app (usado por uvicorn)
```

---

## ⚙️ Primeiro Uso

1. **Configurar variáveis de ambiente:**
   ```bash
   cp .env.example .env
   # Editar .env com suas configurações
   ```

2. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Executar a API (dados são importados automaticamente):**
   ```bash
   python scripts/run_api.py
   ```

---

## 🎯 Fluxo Automático no Startup

Quando você executa `python scripts/run_api.py`, automaticamente:

1. ✅ Cria as tabelas do banco (se não existirem)
2. ✅ Importa dados JSON (se tabela estiver vazia)
3. ✅ Avalia fraude apenas para transações com `status_validacao = 'nao_avaliada'`
4. ✅ Inicia a API

Você não precisa executar nada manualmente!

---

## 📝 Arquivos Removidos da Raiz

Os seguintes arquivos foram movidos para a estrutura organizada:

- ❌ `recalcular_fraude.py` → ✅ `app/jobs/recalcular_fraude.py`
- ❌ `importar_json_mysql.py` → ✅ `app/jobs/importar_dados.py`
- ❌ `ml_motor.py` → ✅ `app/domain/ml.py` (já existia)
- ❌ `dashboard.py` → ✅ `dashboard/app.py` (já existia)
- ✅ `myapi.py` → mantido na raiz (entry point do uvicorn)

---

## 🐛 Troubleshooting

### Erro: "Módulo não encontrado"
```bash
# Adicione o diretório do projeto ao PYTHONPATH
set PYTHONPATH=%cd%  # Windows
export PYTHONPATH=$(pwd)  # Linux/Mac
```

### Erro: "Conexão com banco de dados"
Verifique suas variáveis de ambiente em `.env`:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=1234
DB_NAME=bancodobrasil
```

---

## ✨ Benefícios da Nova Estrutura

✅ Código organizado em módulos  
✅ Fácil manutenção e escalabilidade  
✅ Scripts reutilizáveis  
✅ Separação clara de responsabilidades  
✅ Sem arquivos soltos na raiz  
