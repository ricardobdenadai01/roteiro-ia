import re
from collections import Counter
from google import genai
from google.genai import types
from supabase import create_client

from app.config import settings
from chatbot.models import Message

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase


def _fetch_anuncios() -> list[dict]:
    client = _get_supabase()
    result = (
        client.table("analise_anuncios")
        .select(
            "nome_video, transcricao, ganchos, argumentos_venda, ctas, "
            "tom_voz, estrutura_roteiro, pontos_fortes, resumo_ia, anuncio_ads"
        )
        .execute()
    )
    return result.data or []


def _fetch_campaign_sales() -> list[dict]:
    client = _get_supabase()
    result = (
        client.table("campaign_sales")
        .select("campaign_name, vendidos, negociacao, valor_total")
        .order("vendidos", desc=True)
        .execute()
    )
    return result.data or []


def _build_context(anuncios: list[dict]) -> str:
    if not anuncios:
        return "Nenhum anúncio disponível na base de conhecimento."

    linhas = []
    for ad in anuncios:
        nome = ad.get("nome_video") or ad.get("anuncio_ads") or "Sem nome"
        linhas.append(f"### Anúncio: {nome}")
        if ad.get("transcricao"):
            linhas.append(f"**Transcrição:** {ad['transcricao']}")
        if ad.get("ganchos"):
            linhas.append(f"**Gancho:** {ad['ganchos']}")
        if ad.get("argumentos_venda"):
            linhas.append(f"**Argumentos de venda:** {ad['argumentos_venda']}")
        if ad.get("ctas"):
            linhas.append(f"**CTA:** {ad['ctas']}")
        if ad.get("tom_voz"):
            linhas.append(f"**Tom de voz:** {ad['tom_voz']}")
        if ad.get("estrutura_roteiro"):
            linhas.append(f"**Estrutura:** {ad['estrutura_roteiro']}")
        if ad.get("pontos_fortes"):
            linhas.append(f"**Pontos fortes:** {ad['pontos_fortes']}")
        if ad.get("resumo_ia"):
            linhas.append(f"**Resumo:** {ad['resumo_ia']}")
        linhas.append("")

    return "\n".join(linhas)


def _analyze_patterns(anuncios: list[dict]) -> str:
    """
    Analisa os anúncios e identifica padrões recorrentes por campo,
    ordenados por frequência. Escala conforme mais vídeos são adicionados.
    """
    if not anuncios:
        return "Nenhum padrão identificado ainda."

    total = len(anuncios)

    # Palavras-chave a ignorar na contagem de termos
    stopwords = {
        "e", "o", "a", "os", "as", "de", "do", "da", "dos", "das", "em", "no",
        "na", "nos", "nas", "com", "para", "por", "um", "uma", "que", "se",
        "ao", "à", "é", "são", "foi", "ser", "ter", "uma", "seu", "sua",
        "também", "mais", "como", "ou", "mas", "já", "quando", "onde",
    }

    def extrair_termos(texto: str) -> list[str]:
        palavras = re.findall(r"[a-záéíóúãõâêîôûàèìòùç]+", texto.lower())
        return [p for p in palavras if p not in stopwords and len(p) > 3]

    # --- Tom de voz ---
    tons = [ad["tom_voz"] for ad in anuncios if ad.get("tom_voz")]
    contador_tom = Counter(t.strip().lower() for t in tons)
    tom_top = contador_tom.most_common(1)
    tom_resumo = (
        f"{tom_top[0][0].capitalize()} ({tom_top[0][1]}/{total} anúncios)"
        if tom_top else "N/D"
    )

    # --- Tipo de gancho (classifica por padrão de abertura) ---
    tipos_gancho: dict[str, int] = {
        "Pergunta direta ao dono do provedor": 0,
        "Notícia ou dado de mercado impactante": 0,
        "Apresentação de problema comum": 0,
        "Demonstração de funcionalidade": 0,
        "Outro": 0,
    }
    for ad in anuncios:
        gancho = (ad.get("ganchos") or "").lower()
        transcricao = (ad.get("transcricao") or "").lower()
        abertura = transcricao[:120]
        if abertura.endswith("?") or "dono de provedor" in abertura or abertura.strip().startswith("dono"):
            tipos_gancho["Pergunta direta ao dono do provedor"] += 1
        elif any(w in abertura for w in ["compra", "faturou", "cresce", "mercado", "bilhão", "milhão"]):
            tipos_gancho["Notícia ou dado de mercado impactante"] += 1
        elif any(w in gancho for w in ["dor", "problema", "dificuldade", "ainda", "aborda"]):
            tipos_gancho["Apresentação de problema comum"] += 1
        elif any(w in gancho for w in ["apresenta", "mostra", "tela", "plataforma", "funcionalidade"]):
            tipos_gancho["Demonstração de funcionalidade"] += 1
        else:
            tipos_gancho["Outro"] += 1

    gancho_top = sorted(tipos_gancho.items(), key=lambda x: x[1], reverse=True)
    gancho_resumo = " | ".join(
        f"{k}: {v}/{total}" for k, v in gancho_top if v > 0
    )

    # --- Estrutura do roteiro (termos mais frequentes) ---
    todos_termos_estrutura: list[str] = []
    for ad in anuncios:
        if ad.get("estrutura_roteiro"):
            todos_termos_estrutura.extend(extrair_termos(ad["estrutura_roteiro"]))
    termos_estrutura = Counter(todos_termos_estrutura).most_common(6)
    estrutura_resumo = ", ".join(f"{t} ({n}x)" for t, n in termos_estrutura) if termos_estrutura else "N/D"

    # --- Pontos fortes recorrentes ---
    todos_termos_pontos: list[str] = []
    for ad in anuncios:
        if ad.get("pontos_fortes"):
            todos_termos_pontos.extend(extrair_termos(ad["pontos_fortes"]))
    termos_pontos = Counter(todos_termos_pontos).most_common(6)
    pontos_resumo = ", ".join(f"{t} ({n}x)" for t, n in termos_pontos) if termos_pontos else "N/D"

    # --- Padrão de CTA ---
    todos_termos_cta: list[str] = []
    for ad in anuncios:
        if ad.get("ctas"):
            todos_termos_cta.extend(extrair_termos(ad["ctas"]))
    termos_cta = Counter(todos_termos_cta).most_common(4)
    cta_resumo = ", ".join(f"{t} ({n}x)" for t, n in termos_cta) if termos_cta else "N/D"

    # --- Padrão dominante → frase "Atenção" pré-montada em Python ---
    candidatos = []
    if tom_top:
        candidatos.append((tom_top[0][1] / total, "tom_voz", tom_top[0][0]))
    gancho_principal = gancho_top[0] if gancho_top else None
    if gancho_principal and gancho_principal[1] > 0:
        candidatos.append((gancho_principal[1] / total, "gancho", gancho_principal[0]))

    # Termos de estrutura mais frequentes como candidato adicional
    if termos_estrutura:
        termo_top = termos_estrutura[0]
        candidatos.append((termo_top[1] / (total * 5), "estrutura", termo_top[0]))

    candidatos.sort(reverse=True)

    # Metadados do indicador dominante (mesmo indicador → o modelo varia a redação)
    tipo_dom = "tom_voz"
    valor_dom = "informal e direto"
    ocorr_dom = tom_top[0][1] if tom_top else 0
    if candidatos:
        _, tipo_dom, valor_dom = candidatos[0]
        if tipo_dom == "tom_voz" and tom_top:
            ocorr_dom = tom_top[0][1]
        elif tipo_dom == "gancho":
            ocorr_dom = tipos_gancho.get(valor_dom, 0)
        elif tipo_dom == "estrutura":
            ocorr_dom = next(
                (c for w, c in termos_estrutura if w == valor_dom),
                termos_estrutura[0][1] if termos_estrutura else 0,
            )

    _specs: dict[tuple[str, str], tuple[str, str, list[str]]] = {
        ("tom_voz", "informal e direto"): (
            "Tom de voz",
            "Semelhança mais forte: linguagem próxima e direta, sem formalidade excessiva nem tom institucional.",
            [
                "Enfatize que o ponto comum é tom conversacional voltado ao decisor. Exemplo: um vídeo em que o apresentador explica o tema como em uma conversa objetiva com o dono do negócio.",
                "Enfatize clareza e proximidade sem jargão corporativo. Exemplo: narração em segunda pessoa, frases curtas, sem abertura tipo “prezado cliente”.",
            ],
        ),
        (
            "tom_voz",
            "informal e direto, com um toque de urgência",
        ): (
            "Tom de voz",
            "Semelhança mais forte: linguagem direta combinada com chamada à ação imediata ou senso de oportunidade limitada.",
            [
                "Destaque tom direto + convite a agir logo. Exemplo: vídeo que apresenta o problema e encerra com convite explícito para falar com especialista ainda no mesmo dia.",
            ],
        ),
        (
            "gancho",
            "Pergunta direta ao dono do provedor",
        ): (
            "Gancho",
            "Semelhança mais forte: abertura com pergunta direcionada ao público-alvo (dono de provedor) nos primeiros segundos.",
            [
                "Explique que o gancho comum é pergunta que gera identificação imediata. Exemplo: vídeo que começa perguntando se o time ainda usa determinado processo ou canal (ex.: WhatsApp) de forma problemática.",
            ],
        ),
        (
            "gancho",
            "Notícia ou dado de mercado impactante",
        ): (
            "Gancho",
            "Semelhança mais forte: abertura com fato, número ou notícia de mercado para gerar credibilidade antes da oferta.",
            [
                "Destaque uso de dado ou evento do setor na entrada. Exemplo: vídeo que inicia citando aquisição, faturamento ou movimento relevante no mercado e depois conecta ao tema do produto.",
            ],
        ),
        (
            "gancho",
            "Apresentação de problema comum",
        ): (
            "Gancho",
            "Semelhança mais forte: apresentar primeiro a dor ou dúvida recorrente do público e só depois a solução.",
            [
                "Explique o padrão problema → contexto. Exemplo: vídeo que abre com a incerteza sobre cancelamentos ou retrabalho antes de mostrar a ferramenta ou serviço.",
            ],
        ),
        (
            "gancho",
            "Demonstração de funcionalidade",
        ): (
            "Formato do vídeo",
            "Semelhança mais forte: mostrar interface ou produto em uso enquanto o áudio explica o benefício (não só rosto falando à câmera).",
            [
                "Destaque combinação de narração + imagens do sistema. Exemplo: um vídeo demonstrando as funções do produto na tela enquanto o locutor descreve o que o espectador está vendo.",
                "Enfatize concretude visual. Exemplo: vídeo mais explicativo com walkthrough da plataforma alinhado ao roteiro.",
            ],
        ),
        ("estrutura", "inicia"): (
            "Estrutura do roteiro",
            "Semelhança mais forte: sequência problema → desenvolvimento da solução → chamada para ação ao final.",
            [
                "Descreva o fluxo em três blocos claros. Exemplo: vídeo que primeiro expõe a dor, em seguida apresenta a proposta e fecha pedindo clique ou contato com especialista.",
            ],
        ),
        ("estrutura", "problema"): (
            "Estrutura do roteiro",
            "Semelhança mais forte: deixar explícito no início qual é o problema e para quem ele vale.",
            [
                "Explique abertura focada na dor. Exemplo: vídeo que nos primeiros segundos já nomeia o desafio (ex.: vendas, churn, operação) antes de qualquer menção à marca.",
            ],
        ),
        ("estrutura", "solução"): (
            "Estrutura do roteiro",
            "Semelhança mais forte: apresentação objetiva da solução, com benefícios em destaque e pouca digressão.",
            [
                "Destaque objetividade no miolo. Exemplo: vídeo que vai direto aos benefícios principais e integrações, sem longos preâmbulos.",
            ],
        ),
    }

    spec = _specs.get((tipo_dom, valor_dom))
    if not spec:
        for chave in _specs:
            if chave[0] == tipo_dom:
                spec = _specs[chave]
                break
    if not spec:
        dim_lbl, desc_lbl, sementes = (
            "Tom de voz",
            "Semelhança mais forte entre as análises: tom direto e próximo ao ouvinte, evitando linguagem excessivamente formal.",
            [
                "Formule o ponto de forma objetiva. Exemplo: um vídeo mais explicativo, com narração clara e tom de conversa profissional com o decisor.",
            ],
        )
    else:
        dim_lbl, desc_lbl, sementes = spec

    pct = int(100 * ocorr_dom / total) if total else 0
    sementes_txt = "\n".join(f"  - {s}" for s in sementes)

    bloco_indicador = f"""
### Indicador dominante (fonte da verdade para a linha Atenção)
- **Principal ponto (nomeie assim na Atenção):** {dim_lbl} — é a dimensão que mais se destaca nas análises atuais.
- **Semelhança entre as análises (texto objetivo):** {desc_lbl}
- **Recorrência aproximada:** {ocorr_dom}/{total} anúncios (~{pct}%)
- **Modelos de frase** (uma ideia por linha; na Atenção use **uma** linha só, com **Principal ponto** + **semelhança** + **pelo menos um** “Exemplo: …”; varie a redação entre respostas):
{sementes_txt}
"""

    contexto_detalhado = f"""Padrões nos {total} anúncios analisados:
- Tom de voz mais frequente: {tom_resumo}
- Tipos de gancho: {gancho_resumo}
- Termos recorrentes na estrutura: {estrutura_resumo}
- Pontos fortes recorrentes: {pontos_resumo}
- Padrão de CTA: {cta_resumo}
{bloco_indicador}"""

    return contexto_detalhado


def _build_system_prompt(
    context_anuncios: str,
    context_campanhas: str,
    context_padroes: str,
) -> str:
    return f"""Você é um especialista em criação de roteiros de vídeo para anúncios de provedores de internet.

Você possui três bases de conhecimento com responsabilidades distintas. Siga rigorosamente as regras abaixo.

---

## BASE 1 — Anúncios analisados (use para criar e lapidar roteiros)

Transcrições, ganchos, argumentos, CTAs, tom de voz, estrutura e pontos fortes de vídeos que performaram bem.

{context_anuncios}

---

## BASE 2 — Performance das campanhas (use para perguntas sobre campanhas)

Dados reais de performance: nome da campanha, vendidos, em negociação e valor gerado.

{context_campanhas}

---

## BASE 3 — Padrões recorrentes identificados

Análise automática de frequência entre todos os anúncios da BASE 1.

{context_padroes}

---

## Regras obrigatórias

1. **Criar ou lapidar roteiros** → use a BASE 1. Estruture sempre em: **Gancho**, **Desenvolvimento** e **CTA**. Inicie sempre com: "Levando em consideração os vídeos analisados das campanhas que mais deram certo, segue dois possíveis roteiros:"
   - Ao final dos roteiros, inclua **uma única linha** começando com **⚠️ Atenção —**, em linguagem **objetiva e clara**, obrigatoriamente com **três partes** (pode ser na mesma linha, separadas por ponto ou ponto e vírgula):
     1) **Principal ponto:** diga explicitamente qual é o eixo em destaque (ex.: tom de voz, gancho, estrutura do roteiro, formato do vídeo), usando o nome da **Dimensão / Principal ponto** do bloco **Indicador dominante** na BASE 3.
     2) **Semelhança:** uma frase objetiva dizendo **o que se repete** entre as análises, alinhada ao texto **Semelhança entre as análises** da BASE 3.
     3) **Exemplo:** pelo menos um trecho no formato **"Exemplo: …"** descrevendo tipo de vídeo ou abordagem (ex.: "Exemplo: um vídeo mais explicativo" ou "Exemplo: um vídeo demonstrando as funções do produto na tela").
     Sem gírias nessa linha. Varie a redação entre respostas sem mudar o significado; não repita a mesma frase literal de uma mensagem anterior nesta conversa enquanto o indicador dominante for o mesmo.

2. **Perguntas sobre campanhas/performance** → use apenas a BASE 2. Liste nome, vendidos, negociação e valor. Destaque as com mais vendas.

3. **Perguntas sobre padrões ou o que mais funciona** → use a BASE 3 e explique os padrões com as frequências disponíveis.

4. Nunca misture as bases indevidamente. Nunca inclua marcações como "[Baseado em: ...]". Responda em português brasileiro: nos **roteiros**, use tom próximo e direto; na linha **⚠️ Atenção**, mantenha tom **objetivo e profissional**, como acima.
"""


def _build_campaigns_context(campanhas: list[dict]) -> str:
    if not campanhas:
        return "Nenhum dado de campanha disponível."

    linhas = []
    for c in campanhas:
        nome = c.get("campaign_name", "Sem nome")
        vendidos = c.get("vendidos", 0)
        negociacao = c.get("negociacao", 0)
        valor = c.get("valor_total", 0) or 0
        linhas.append(
            f"- **{nome}**: {vendidos} vendidos | {negociacao} em negociação | R$ {valor:,.2f} gerados"
        )

    return "\n".join(linhas)


def _extract_campaigns(reply: str, anuncios: list[dict]) -> list[str]:
    campaigns = []
    for ad in anuncios:
        nome = ad.get("nome_video") or ad.get("anuncio_ads") or ""
        if nome and nome.lower() in reply.lower():
            campaigns.append(nome)

    # Também captura padrão [Baseado em: ...]
    match = re.search(r"\[Baseado em:\s*([^\]]+)\]", reply, re.IGNORECASE)
    if match:
        referencias = [r.strip() for r in match.group(1).split(",")]
        for ref in referencias:
            if ref and ref not in campaigns:
                campaigns.append(ref)

    return list(dict.fromkeys(campaigns))  # dedup mantendo ordem


def chat(message: str, history: list[Message]) -> tuple[str, list[str]]:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    anuncios = _fetch_anuncios()
    campanhas = _fetch_campaign_sales()
    context_anuncios = _build_context(anuncios)
    context_campanhas = _build_campaigns_context(campanhas)
    context_padroes = _analyze_patterns(anuncios)
    system_prompt = _build_system_prompt(context_anuncios, context_campanhas, context_padroes)

    gemini_history = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        gemini_history.append(
            types.Content(role=role, parts=[types.Part(text=msg.content)])
        )
    gemini_history.append(
        types.Content(role="user", parts=[types.Part(text=message)])
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=gemini_history,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
        ),
    )
    reply = response.text

    campaigns_used = _extract_campaigns(reply, anuncios)
    return reply, campaigns_used
