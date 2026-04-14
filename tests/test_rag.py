import pytest
from chatbot.rag import _build_context, _analyze_patterns, _build_campaigns_context, _extract_campaigns


SAMPLE_ANUNCIOS = [
    {
        "nome_video": "Video CRM Provedor",
        "transcricao": "Dono de provedor, você ainda usa planilha para gerenciar seus clientes? Conheça o CRM que vai triplicar suas vendas.",
        "ganchos": "Pergunta direta ao dono de provedor sobre uso de planilha",
        "argumentos_venda": "Triplicar vendas, gestão automatizada, integração com WhatsApp",
        "ctas": "Agende uma demonstração gratuita agora",
        "tom_voz": "informal e direto",
        "estrutura_roteiro": "Inicia com problema, apresenta solução, CTA direto",
        "pontos_fortes": "Linguagem próxima, dados concretos, CTA claro",
        "resumo_ia": "Vídeo focado em dono de provedor, apresentando CRM como solução para gestão.",
        "anuncio_ads": "CRM_Provedor_V1",
    },
    {
        "nome_video": "Assessoria Comercial",
        "transcricao": "O mercado de provedores cresceu 30% no último ano. Sua equipe comercial está preparada?",
        "ganchos": "Dado de mercado impactante sobre crescimento do setor",
        "argumentos_venda": "Crescimento do mercado, equipe preparada, método validado",
        "ctas": "Fale com um especialista hoje",
        "tom_voz": "informal e direto, com um toque de urgência",
        "estrutura_roteiro": "Inicia com notícia, desenvolve o problema, CTA com urgência",
        "pontos_fortes": "Dado concreto, senso de oportunidade, autoridade",
        "resumo_ia": "Vídeo de assessoria comercial usando dado de mercado para gerar urgência.",
        "anuncio_ads": "Assessoria_V2",
    },
    {
        "nome_video": "Plataforma Demo",
        "transcricao": "Veja como funciona o painel de controle do seu provedor. Aqui você gerencia tudo em um só lugar.",
        "ganchos": "Demonstração da interface do produto em funcionamento",
        "argumentos_venda": "Centralização, visão completa, facilidade de uso",
        "ctas": "Teste grátis por 7 dias",
        "tom_voz": "informal e direto",
        "estrutura_roteiro": "Apresenta funcionalidade, demonstra benefício, CTA suave",
        "pontos_fortes": "Visual concreto, simplicidade, prova de conceito",
        "resumo_ia": "Vídeo demo mostrando a plataforma em uso real.",
        "anuncio_ads": "Demo_Plataforma_V1",
    },
]

SAMPLE_CAMPANHAS = [
    {"campaign_name": "CRM Q1 2026", "vendidos": 15, "negociacao": 8, "valor_total": 45000.0},
    {"campaign_name": "Assessoria Mar", "vendidos": 10, "negociacao": 5, "valor_total": 30000.0},
    {"campaign_name": "Demo Trial", "vendidos": 3, "negociacao": 12, "valor_total": 9000.0},
]


class TestBuildContext:
    def test_empty_list(self):
        result = _build_context([])
        assert "Nenhum anúncio disponível" in result

    def test_includes_all_videos(self):
        result = _build_context(SAMPLE_ANUNCIOS)
        assert "Video CRM Provedor" in result
        assert "Assessoria Comercial" in result
        assert "Plataforma Demo" in result

    def test_includes_resumo(self):
        result = _build_context(SAMPLE_ANUNCIOS)
        assert "Resumo:" in result

    def test_truncates_long_transcription(self):
        long_ad = {
            "nome_video": "Long Video",
            "transcricao": "A" * 1000,
            "ganchos": "",
            "argumentos_venda": "",
            "ctas": "",
            "tom_voz": "",
            "estrutura_roteiro": "",
            "pontos_fortes": "",
            "resumo_ia": "",
            "anuncio_ads": "",
        }
        result = _build_context([long_ad])
        assert "[...]" in result

    def test_short_transcription_no_truncation(self):
        result = _build_context(SAMPLE_ANUNCIOS)
        assert "[...]" not in result


class TestAnalyzePatterns:
    def test_empty_list(self):
        result = _analyze_patterns([])
        assert "Nenhum padrão" in result

    def test_reports_total_count(self):
        result = _analyze_patterns(SAMPLE_ANUNCIOS)
        assert "3 anúncios" in result

    def test_includes_tom_de_voz(self):
        result = _analyze_patterns(SAMPLE_ANUNCIOS)
        assert "Tom de voz" in result

    def test_includes_cta(self):
        result = _analyze_patterns(SAMPLE_ANUNCIOS)
        assert "CTA" in result

    def test_includes_frequency_data(self):
        result = _analyze_patterns(SAMPLE_ANUNCIOS)
        # Should contain frequency markers like "(Nx)" or "(N/3)"
        assert "x)" in result or "/3)" in result


class TestBuildCampaignsContext:
    def test_empty_list(self):
        result = _build_campaigns_context([])
        assert "Nenhum dado" in result

    def test_includes_all_campaigns(self):
        result = _build_campaigns_context(SAMPLE_CAMPANHAS)
        assert "CRM Q1 2026" in result
        assert "Assessoria Mar" in result
        assert "Demo Trial" in result

    def test_includes_metrics(self):
        result = _build_campaigns_context(SAMPLE_CAMPANHAS)
        assert "15 vendidos" in result
        assert "R$" in result


class TestExtractCampaigns:
    def test_finds_matching_video_name(self):
        reply = "Baseado no Video CRM Provedor, recomendo este roteiro..."
        result = _extract_campaigns(reply, SAMPLE_ANUNCIOS)
        assert "Video CRM Provedor" in result

    def test_case_insensitive(self):
        reply = "Analisando o video crm provedor e assessoria comercial..."
        result = _extract_campaigns(reply, SAMPLE_ANUNCIOS)
        assert len(result) == 2

    def test_no_match(self):
        reply = "Aqui está um roteiro genérico para você."
        result = _extract_campaigns(reply, SAMPLE_ANUNCIOS)
        assert result == []

    def test_deduplicates(self):
        reply = "Video CRM Provedor é ótimo. Sim, Video CRM Provedor é o melhor."
        result = _extract_campaigns(reply, SAMPLE_ANUNCIOS)
        assert result.count("Video CRM Provedor") == 1
