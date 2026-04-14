-- =============================================
-- SCHEMA — Roteiro IA Coleta v4
-- Performance de Vendas + Engajamento + Chatbot
-- =============================================

DROP TABLE IF EXISTS chat_sessions;
DROP TABLE IF EXISTS analise_anuncios;
DROP TABLE IF EXISTS ad_engagement;
DROP TABLE IF EXISTS campaign_engagement;
DROP TABLE IF EXISTS ad_sales;
DROP TABLE IF EXISTS campaign_sales;
DROP TABLE IF EXISTS leads;

-- Leads filtrados (Vendido + Negociação) com dados completos
CREATE TABLE leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    campaign_name VARCHAR(500),
    ad_name VARCHAR(255),
    quality VARCHAR(100),
    services_contracted TEXT,
    service_type VARCHAR(100),
    sdr VARCHAR(255),
    closer VARCHAR(255),
    implantation_value NUMERIC,
    mrr_value NUMERIC,
    product_value NUMERIC,
    event_value NUMERIC,
    date_sold DATE,
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance de vendas por campanha
CREATE TABLE campaign_sales (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_name VARCHAR(500) NOT NULL,
    vendidos INTEGER DEFAULT 0,
    negociacao INTEGER DEFAULT 0,
    valor_total NUMERIC DEFAULT 0,
    ads JSONB DEFAULT '[]',
    servicos JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance de vendas por ad (vídeo)
CREATE TABLE ad_sales (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ad_name VARCHAR(255) NOT NULL,
    vendidos INTEGER DEFAULT 0,
    negociacao INTEGER DEFAULT 0,
    valor NUMERIC DEFAULT 0,
    campanhas JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance de engajamento por campanha
CREATE TABLE campaign_engagement (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_name VARCHAR(500) NOT NULL,
    monday_leads INTEGER DEFAULT 0,
    meta_leads INTEGER DEFAULT 0,
    spend NUMERIC DEFAULT 0,
    cpl NUMERIC DEFAULT 0,
    vendidos INTEGER DEFAULT 0,
    status_breakdown JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance de engajamento por ad (vídeo)
CREATE TABLE ad_engagement (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ad_name VARCHAR(255) NOT NULL,
    leads INTEGER DEFAULT 0,
    qualified INTEGER DEFAULT 0,
    sales INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Análise de anúncios/vídeos (base de conhecimento do chatbot)
CREATE TABLE analise_anuncios (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome_video VARCHAR(500),
    anuncio_ads VARCHAR(500),
    transcricao TEXT,
    ganchos TEXT,
    argumentos_venda TEXT,
    ctas TEXT,
    tom_voz VARCHAR(255),
    estrutura_roteiro TEXT,
    pontos_fortes TEXT,
    resumo_ia TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessões de chat persistidas
CREATE TABLE chat_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    history JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_chat_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX idx_analise_anuncios_nome ON analise_anuncios(nome_video);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_campaign ON leads(campaign_name);
CREATE INDEX idx_leads_ad ON leads(ad_name);
CREATE INDEX idx_cs_vendidos ON campaign_sales(vendidos DESC);
CREATE INDEX idx_as_vendidos ON ad_sales(vendidos DESC);
CREATE INDEX idx_ce_leads ON campaign_engagement(monday_leads DESC);
CREATE INDEX idx_ae_leads ON ad_engagement(leads DESC);
