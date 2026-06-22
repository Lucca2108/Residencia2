# API de Detecção de Anomalias em Transações Financeiras

## Descrição do Projeto

Este projeto foi desenvolvido para a disciplina **Residência em Software 2**, da **Universidade Tiradentes**, em parceria com o **Banco do Brasil**.

A aplicação consiste em uma **API REST** construída com **FastAPI** para gerenciamento e análise de transações financeiras, com foco em **detecção de anomalias e possíveis fraudes**. O sistema permite cadastrar, listar, atualizar, excluir e filtrar transações, além de aplicar uma lógica de avaliação de risco baseada em regras heurísticas.

O objetivo do projeto é simular uma solução backend capaz de apoiar cenários de monitoramento de operações financeiras, identificando padrões suspeitos a partir de atributos da transação, como valor, horário, país, tipo de transação, dispositivo utilizado e quantidade de tentativas.

---

## Objetivo

Desenvolver uma API para:

- cadastrar transações financeiras;
- consultar transações por ID;
- listar transações com paginação;
- buscar transações com filtros diversos;
- classificar transações com potencial de fraude;
- disponibilizar documentação interativa via Swagger/OpenAPI.

---

## Tecnologias Utilizadas

- Python
- FastAPI
- Uvicorn
- Pydantic
- MySQL
- mysql-connector-python
- python-dotenv

---

## Contexto Acadêmico

Este projeto foi proposto como atividade prática da disciplina **Residência em Software 2**, com o propósito de aplicar conceitos de:

- desenvolvimento de APIs REST;
- modelagem de dados;
- integração com banco de dados relacional;
- documentação de serviços;
- validação de dados;
- implementação de regras de negócio;
- análise de anomalias em transações financeiras.

A parceria com o **Banco do Brasil** fornece o contexto de negócio para o desenvolvimento da solução, aproximando o projeto acadêmico de um cenário real de software corporativo voltado ao setor financeiro.

---

## Funcionalidades da API

A API oferece as seguintes funcionalidades:

### 1. Listagem de transações
Permite listar transações com suporte a:

- `limit`
- `offset`

### 2. Busca com filtros
Permite buscar transações usando filtros opcionais, como:

- categoria
- conta
- cidade
- estado
- país
- tipo de transação
- dispositivo
- estabelecimento
- faixa de valor
- intervalo de datas
- indicador de fraude (`is_fraude`)

### 3. Busca por ID
Permite consultar uma transação específica pelo seu identificador.

### 4. Cadastro de transações
Permite inserir novas transações na base de dados.

Ao cadastrar uma transação, o sistema executa automaticamente uma avaliação de risco para definir se ela deve ser marcada como potencial fraude.

As transações recém-criadas recebem o estado `status_validacao = 'nao_avaliada'` até que a análise seja concluída. Após a verificação automática, o sistema atualiza o estado para:

- `pendente` — transação suspeita, aguardando validação do cliente;
- `aprovada` — transação avaliada como não fraude;
- `confirmada_pelo_cliente` — cliente confirmou que a transação é legítima;
- `fraude_confirmada` — cliente confirmou que a transação é fraude.

### 5. Atualização de transações
Permite atualizar uma transação existente.

Ao atualizar, a análise de fraude também é recalculada.

### 6. Exclusão de transações
Permite remover uma transação da base.

### 7. Documentação automática
A API disponibiliza interface interativa via Swagger para testes dos endpoints.

---

## Estrutura do Projeto

O projeto está organizado em pacotes para separar claramente as camadas de configuração, dados, domínio, serviços, jobs, API e dashboard:

```bash
.
├── app/
│   ├── api/
│   │   └── routers/
│   ├── core/
│   ├── db/
│   ├── domain/
│   ├── jobs/
│   ├── repositories/
│   ├── services/
│   ├── utils/
│   └── schemas.py
├── dashboard/
│   └── dashboard_app.py
├── data/
│   ├── transacoes_treino.json
│   └── transacoes_treino_sem_fraude.json
├── notebook/
│   └── dataset.ipynb
├── scripts/
│   ├── run_api.py
│   ├── run_dashboard.py
│   ├── run_import.py
│   └── run_recalcular_nao_avaliadas.py
├── dashboard.py             # Wrapper de compatibilidade do dashboard
├── myapi.py                 # Wrapper de compatibilidade da API
└── requirements.txt         # Dependências do projeto
```

## Como Executar

Antes de iniciar a aplicação, crie o banco `bancodobrasil` no MySQL e configure o arquivo `.env` com as variáveis `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` e `DB_PORT`. Na maioria dos casos, você só precisará ajustar usuário, senha e host.

### API

O jeito recomendado de subir a API é:

```bash
python scripts/run_api.py
```

Esse script executa o wrapper [myapi.py](myapi.py), que expõe a aplicação FastAPI em `app.main:app`. Se preferir, você também pode iniciar diretamente com:

```bash
uvicorn myapi:app --reload
```

Depois disso, acesse `http://127.0.0.1:8000/docs` para abrir o Swagger/OpenAPI.

### Dashboard

O dashboard Streamlit deve ser iniciado com:

```bash
python scripts/run_dashboard.py
```

Esse script executa [dashboard/dashboard_app.py](dashboard/dashboard_app.py), que carrega os dados da API `GET /transacoes/dashboard` quando o backend está disponível e faz fallback para o banco local quando necessário.

Se quiser executar diretamente, use:

```bash
streamlit run dashboard/dashboard_app.py
```

O wrapper [dashboard.py](dashboard.py) foi mantido por compatibilidade, mas o entrypoint principal é o módulo em `dashboard/dashboard_app.py`.

### Scripts Auxiliares

- `python scripts/run_import.py` - importa os dados de origem para o banco.
- `python scripts/run_recalcular_nao_avaliadas.py` - recalcula a fraude para transações ainda não avaliadas.

### Endpoints principais para o frontend

- `GET /` - status básico da API
- `GET /transacoes` - lista transações com paginação
- `GET /transacoes/dashboard` - resumo agregado usado pelo dashboard
- `POST /transacoes` - cria e analisa uma transação
- `POST /analisar` - analisa uma transação sem persistir
- `DELETE /transacoes/{id}` - remove uma transação

### Exemplos rápidos

`POST /analisar`

```json
{
  "valor": 120.5,
  "data": "2026-05-18",
  "hora": "14:30:00",
  "conta": "12345-6"
}
```

`POST /transacoes`

```json
{
  "valor": 120.5,
  "data": "2026-05-18",
  "hora": "14:30:00",
  "dia_semana": "segunda-feira",
  "categoria": "alimentacao",
  "conta": "12345-6",
  "cidade": "Fortaleza",
  "estado": "CE",
  "pais": "Brasil",
  "latitude": -3.731862,
  "longitude": -38.52667,
  "tipo_transacao": "debito",
  "dispositivo": "android",
  "estabelecimento": "Mercado Central",
  "tentativas": 1,
  "ip_origem": "192.168.0.10"
}
```

### CORS habilitado

A API aceita chamadas do frontend local em:

- `http://localhost:5500`
- `http://127.0.0.1:5500`
- `http://localhost:3000`
- `http://127.0.0.1:3000`
