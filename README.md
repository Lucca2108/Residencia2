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

### 5. Atualização de transações
Permite atualizar uma transação existente.

Ao atualizar, a análise de fraude também é recalculada.

### 6. Exclusão de transações
Permite remover uma transação da base.

### 7. Documentação automática
A API disponibiliza interface interativa via Swagger para testes dos endpoints.

---

## Estrutura do Projeto

O projeto agora está organizado em pacotes para separar claramente as camadas de configuração, dados, domínio, serviços e API:

```bash
.
├── app/
│   ├── api/
│   │   └── routers/
│   ├── core/
│   ├── db/
│   ├── domain/
│   ├── repositories/
│   ├── services/
│   ├── utils/
│   └── schemas.py
├── dashboard/
│   └── app.py
├── myapi.py                  # Wrapper da API para compatibilidade com uvicorn
├── dashboard.py             # Wrapper do dashboard para compatibilidade com streamlit
├── requirements.txt         # Dependências do projeto
└── data/
    └── transacoes_treino.json
```

Como iniciar a API no VS Code
Abra o projeto no VS Code, abra o terminal integrado e ative o ambiente virtual. Antes de iniciar a API, crie o banco bancodobrasil no MySQL, preencha corretamente o arquivo .env.example com DB_HOST, DB_USER, DB_PASSWORD, DB_NAME e DB_PORT. Em geral, será necessário alterar apenas o usuário e a senha. Garanta também que o schema/banco esteja disponível para conexão. Em seguida, execute o comando `uvicorn myapi:app --reload`. Depois disso, acesse `http://127.0.0.1:8000/docs` no navegador para abrir o Swagger e testar os endpoints da API.

Como iniciar o dashboard
Execute `streamlit run dashboard.py` para abrir o painel de visualização.