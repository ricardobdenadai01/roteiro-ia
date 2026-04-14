import re
import time
from collections import Counter
from google import genai
from google.genai import types

from app.config import settings
from chatbot.models import Message
from shared.supabase_client import get_client
from shared import cache

_CACHE_KEY_ANUNCIOS = "anuncios"
_CACHE_KEY_CAMPAIGNS = "campaign_sales"
_CACHE_TTL = 300  # 5 minutes


def _fetch_anuncios() -> list[dict]:
    cached = cache.get(_CACHE_KEY_ANUNCIOS)
    if cached is not None:
        return cached

    client = get_client()
    result = (
        client.table("analise_anuncios")
        .select(
            "nome_video, transcricao, ganchos, argumentos_venda, ctas, "
            "tom_voz, estrutura_roteiro, pontos_fortes, resumo_ia, anuncio_ads"
        )
        .execute()
    )
    data = result.data or []
    cache.set(_CACHE_KEY_ANUNCIOS, data, _CACHE_TTL)
    return data


def _fetch_campaign_sales() -> list[dict]:
    cached = cache.get(_CACHE_KEY_CAMPAIGNS)
    if cached is not None:
        return cached

    client = get_client()
    result = (
        client.table("campaign_sales")
        .select("campaign_name, vendidos, negociacao, valor_total")
        .order("vendidos", desc=True)
        .execute()
    )
    data = result.data or []
    cache.set(_CACHE_KEY_CAMPAIGNS, data, _CACHE_TTL)
    return data


def _build_context(anuncios: list[dict]) -> str:
    if not anuncios:
        return "Nenhum anúncio disponível na base de conhecimento."

    linhas = []
    for ad in anuncios:
        nome = ad.get("nome_video") or ad.get("anuncio_ads") or "Sem nome"
        linhas.append(f"### Anúncio: {nome}")
        if ad.get("resumo_ia"):
            linhas.append(f"**Resumo:** {ad['resumo_ia']}")
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
        if ad.get("transcricao"):
            trecho = ad["transcricao"][:500]
            if len(ad["transcricao"]) > 500:
                trecho += " [...]"
            linhas.append(f"**Transcrição (trecho):** {trecho}")
        linhas.append("")

    return "\n".join(linhas)


def _analyze_patterns(anuncios: list[dict]) -> str:
    if not anuncios:
        return "Nenhum padrão identificado ainda."

    total = len(anuncios)

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
    tom_top = contador_tom.most_common(3)
    tom_resumo = " | ".join(
        f"{t.capitalize()} ({n}/{total})" for t, n in tom_top
    ) if tom_top else "N/D"

    # --- Ganchos (usando o campo analisado, não keyword matching) ---
    ganchos_raw = [ad["ganchos"] for ad in anuncios if ad.get("ganchos")]
    todos_termos_gancho: list[str] = []
    for g in ganchos_raw:
        todos_termos_gancho.extend(extrair_termos(g))
    termos_gancho = Counter(todos_termos_gancho).most_common(6)
    gancho_resumo = ", ".join(f"{t} ({n}x)" for t, n in termos_gancho) if termos_gancho else "N/D"

    # --- Estrutura do roteiro ---
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

    # --- Argumentos de venda ---
    todos_termos_args: list[str] = []
    for ad in anuncios:
        if ad.get("argumentos_venda"):
            todos_termos_args.extend(extrair_termos(ad["argumentos_venda"]))
    termos_args = Counter(todos_termos_args).most_common(6)
    args_resumo = ", ".join(f"{t} ({n}x)" for t, n in termos_args) if termos_args else "N/D"

    return f"""Padrões identificados nos {total} anúncios analisados:

- **Tom de voz mais frequente:** {tom_resumo}
- **Termos recorrentes nos ganchos:** {gancho_resumo}
- **Termos recorrentes na estrutura:** {estrutura_resumo}
- **Pontos fortes recorrentes:** {pontos_resumo}
- **Padrão de CTA:** {cta_resumo}
- **Argumentos de venda recorrentes:** {args_resumo}

Use esses padrões para fundamentar suas recomendações. Quando citar um padrão, mencione a frequência (ex: "aparece em X dos {total} anúncios")."""


def _build_system_prompt(
    context_anuncios: str,
    context_campanhas: str,
    context_padroes: str,
) -> str:
    return f"""Você é um especialista em criação de roteiros de vídeo para anúncios voltados a provedores de internet.

A empresa é a **Delipe** e vende os seguintes produtos/serviços para provedores de internet:

- **Plataforma de BI** — Business Intelligence com dashboards e métricas para gestão do provedor.
- **Plataforma de IA** — Funciona como um supervisor virtual. A IA analisa todas as conversas e reuniões dos vendedores/atendentes do provedor, verifica se seguiram o processo definido pelo gestor (ex: ofereceu benefício, plano mais caro/barato, pesquisou necessidade de internet), atribui uma nota para cada conversa e envia feedback automático para o vendedor e o gestor. O processo de avaliação é personalizável pelo cliente. Não é IA para vender — é IA para supervisionar e melhorar a operação comercial de dentro para fora.
- **Assessoria Comercial** — Consultoria para estruturar e escalar o setor comercial do provedor.
- **Marketing** — Serviço de marketing para provedores.

Nunca mencione CRM como produto da empresa.

Você possui três bases de conhecimento. Consulte-as de acordo com o que o usuário pedir.

---

## BASE 1 — Anúncios analisados (roteiros, ganchos, estrutura, tom)

Dados detalhados de vídeos que performaram bem: transcrições, ganchos, argumentos, CTAs, tom de voz, estrutura e pontos fortes.

{context_anuncios}

---

## BASE 2 — Performance das campanhas

Dados reais de performance: nome da campanha, vendidos, em negociação e valor gerado.

{context_campanhas}

---

## BASE 3 — Padrões recorrentes identificados

Análise de frequência entre todos os anúncios da BASE 1.

{context_padroes}

---

## Como responder

Você deve adaptar sua resposta ao que o usuário pedir. Existem três cenários principais:

### Cenário A — Criar roteiro do zero
Quando o usuário pedir para criar um roteiro novo sem trazer uma ideia própria:
- Vá direto ao ponto. Comece com algo breve como "Claro, aqui estão dois roteiros:" e entregue os roteiros.
- Estruture em: **Gancho**, **Desenvolvimento** e **CTA**.
- Ofereça duas opções de roteiro com abordagens diferentes.
- Ao final, inclua uma **observação curta** (com ⚠️) de 2-3 frases no máximo, de forma direta e educada. Foque no insight, não nos dados brutos. Exemplo de tom: "O tom informal e direto cria conexão com donos de provedores. CTAs com benefício imediato e tangível, como 'fale com um especialista', geram leads mais qualificados." Nunca mencione quantos vídeos ou anúncios foram analisados nessa observação — apenas traga o ponto de atenção de forma natural.

### Cenário B — Lapidar / melhorar ideia do usuário
Quando o usuário trouxer uma ideia, rascunho ou roteiro para melhorar:
- **Não ignore a ideia do usuário.** Trabalhe a partir dela.
- Vá direto ao ponto: diga rapidamente o que está bom e o que pode melhorar.
- Ofereça uma versão lapidada mantendo a essência da ideia original.
- Se algo importante estiver ausente (gancho forte, CTA claro, etc.), sugira adições específicas.

### Cenário C — Perguntas sobre campanhas, performance ou padrões
- Para performance: use a BASE 2. Liste nome, vendidos, negociação e valor.
- Para padrões ("o que funciona?"): use a BASE 3 e explique com frequências.
- Para detalhes de um anúncio específico: use a BASE 1.

## Regras gerais
- Responda sempre em português brasileiro.
- Seja direto e conciso. Não faça introduções longas. Evite parágrafos explicativos antes de entregar o que foi pedido.
- Use tom próximo e direto nos roteiros, como se falasse com o dono de um provedor.
- Fundamente suas sugestões citando padrões reais dos anúncios, mas de forma breve e natural dentro do texto.
- Nunca invente dados de performance. Use apenas o que está nas bases.
- Nunca inclua marcações como "[Baseado em: ...]" na resposta.
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

    return list(dict.fromkeys(campaigns))


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

    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=gemini_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                ),
            )
            reply = response.text
            break
        except Exception as e:
            last_error = e
            if attempt < 2 and ("503" in str(e) or "UNAVAILABLE" in str(e) or "overloaded" in str(e).lower()):
                time.sleep(2 ** attempt)
                continue
            raise
    else:
        raise last_error  # type: ignore[misc]

    campaigns_used = _extract_campaigns(reply, anuncios)
    return reply, campaigns_used
