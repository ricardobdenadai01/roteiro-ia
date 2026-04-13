# Roteiro IA — Coleta e Análise de Dados do CRM

Sistema de coleta automatizada de dados de uma API de CRM, com filtragem, mapeamento de setores, geração de rankings e persistência no Supabase.

## Funcionalidades

- Consome a API REST do CRM com filtro por período
- Filtra apenas leads com status **Vendido** e **Negociação**
- Mapeia setores usando `servicesContracted` como fonte de verdade
- Gera rankings top 5 / bottom 5 de campanhas e anúncios por setor
- Salva todos os dados no Supabase
- Relatório detalhado no terminal

## Pré-requisitos

- Python 3.11+
- Conta no Supabase com as tabelas criadas

## Instalação

```bash
# Clonar ou entrar no diretório do projeto
cd roteiro-ia-coleta

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt
```

## Configuração

1. Copie `.env.example` para `.env` e preencha suas credenciais:

```bash
copy .env.example .env
```

2. Edite o `.env` com suas credenciais do Supabase:

```
CRM_API_KEY=af932e1926de9aa1fbf99b4dc38242d7b1f482257106fc020002b153c546cd06
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-anon-key-aqui
```

3. Execute o SQL do arquivo `schema.sql` no SQL Editor do Supabase para criar as tabelas.

## Uso

```bash
# Executar com datas padrão (configuradas no .env)
python -m app.main

# Executar com datas específicas
python -m app.main --start 2026-01-01 --end 2026-03-26
```

## Estrutura do Projeto

```
roteiro-ia-coleta/
├── app/
│   ├── __init__.py           # Pacote Python
│   ├── config.py             # Configurações via .env
│   ├── database.py           # Cliente Supabase
│   ├── api_client.py         # Consumo da API do CRM
│   ├── data_cleaner.py       # Filtragem e limpeza dos dados
│   ├── sector_mapper.py      # Mapeamento de setores
│   ├── ranking.py            # Rankings top/bottom por setor
│   └── main.py               # Orquestrador principal
├── sector_mappings.json      # Mapeamento palavras-chave → setor
├── schema.sql                # SQL para criar tabelas no Supabase
├── requirements.txt          # Dependências Python
├── .env.example              # Exemplo de variáveis de ambiente
└── README.md
```

## Mapeamento de Setores

O arquivo `sector_mappings.json` contém palavras-chave para inferir o setor de leads em Negociação que não possuem `servicesContracted` preenchido. Edite conforme necessário:

```json
{
    "keywords": {
        "ASSESSORIA": "Assessoria Comercial",
        "IMERSAO": "Imersão Compra e Venda",
        "CRM": "CRM"
    }
}
```

## Tabelas no Supabase

| Tabela | Descrição |
|--------|-----------|
| `leads` | Leads filtrados (Vendido + Negociação) com dados brutos |
| `campaign_stats` | Estatísticas por campanha (apenas vendidos) |
| `ad_stats` | Estatísticas por anúncio (apenas vendidos) |
| `sector_rankings` | Rankings top/bottom por setor |
