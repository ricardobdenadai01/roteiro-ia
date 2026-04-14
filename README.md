# Roteiro IA — Chatbot + Coleta de Dados

Sistema com duas funções principais:

1. **Chatbot de Roteiros** — Cria e lapida roteiros de vídeo para anúncios, usando como base análises de vídeos que performaram bem (tabela `analise_anuncios` no Supabase).
2. **Pipeline de Coleta CRM** — Coleta dados de performance de uma API CRM, gera rankings e salva no Supabase.

## Como funciona o Chatbot

O chatbot analisa os vídeos/anúncios cadastrados na tabela `analise_anuncios` e identifica padrões recorrentes (tom de voz, ganchos, CTAs, estrutura, pontos fortes). Com isso, ele:

- **Cria roteiros do zero** fundamentados nos padrões de sucesso
- **Lapida ideias do usuário** comparando com o que funciona nos anúncios analisados
- **Responde perguntas** sobre performance de campanhas e padrões identificados

## Pré-requisitos

- Python 3.11+
- Conta no Supabase com as tabelas criadas (`schema.sql`)
- Chave de API do Google Gemini

## Instalação

```bash
cd roteiro-ia-coleta

python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

## Configuração

1. Copie `.env.example` para `.env`:

```bash
copy .env.example .env
```

2. Preencha suas credenciais no `.env`.

3. Execute o SQL de `schema.sql` no SQL Editor do Supabase para criar as tabelas.

## Uso

### Chatbot API

```bash
uvicorn chatbot.api:app --reload --port 8000
```

Endpoints:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Health check |
| POST | `/chat` | Envia mensagem ao chatbot |
| DELETE | `/session/{session_id}` | Apaga sessão de conversa |

Exemplo de request:

```json
POST /chat
{
  "message": "Crie um roteiro para um anúncio de CRM para provedores",
  "session_id": "user-123"
}
```

Se `CHATBOT_API_KEY` estiver configurado no `.env`, inclua o header `x-api-key` nas requisições.

### Frontend

Abra `frontend/index.html` no navegador, ou sirva com:

```bash
python -m http.server 3000 --directory frontend
```

### Pipeline de Coleta CRM

```bash
# Com datas padrão
python -m app.main

# Com datas específicas
python -m app.main --start 2026-01-01 --end 2026-03-26

# Sem confirmação interativa (para automação)
python -m app.main --force
```

## Estrutura do Projeto

```
roteiro-ia-coleta/
├── chatbot/
│   ├── api.py              # FastAPI — endpoints do chatbot
│   ├── models.py           # Modelos Pydantic (request/response)
│   ├── rag.py              # Busca de dados, análise de padrões, chamada ao Gemini
│   └── sessions.py         # Persistência de sessões no Supabase
├── app/
│   ├── config.py           # Configurações via .env
│   ├── main.py             # Orquestrador do pipeline CRM
│   ├── api_client.py       # Consumo da API do CRM
│   ├── data_cleaner.py     # Filtragem e limpeza dos dados
│   ├── ranking.py          # Rankings de vendas e engajamento
│   └── database.py         # Inserções no Supabase (pipeline)
├── shared/
│   ├── supabase_client.py  # Cliente Supabase compartilhado
│   └── cache.py            # Cache em memória com TTL
├── frontend/
│   └── index.html          # Interface web do chatbot
├── tests/
│   └── test_rag.py         # Testes unitários
├── schema.sql              # DDL de todas as tabelas
├── requirements.txt        # Dependências Python
├── .env.example            # Exemplo de variáveis de ambiente
└── README.md
```

## Tabelas no Supabase

| Tabela | Descrição |
|--------|-----------|
| `analise_anuncios` | Análises de vídeos/anúncios (base de conhecimento do chatbot) |
| `chat_sessions` | Sessões de conversa persistidas |
| `leads` | Leads filtrados do CRM (Vendido + Negociação) |
| `campaign_sales` | Performance de vendas por campanha |
| `ad_sales` | Performance de vendas por anúncio |
| `campaign_engagement` | Performance de engajamento por campanha |
| `ad_engagement` | Performance de engajamento por anúncio |
