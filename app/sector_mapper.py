import json
from collections import Counter
from pathlib import Path

MAPPINGS_PATH = Path(__file__).resolve().parent.parent / "sector_mappings.json"

SETOR_NAO_IDENTIFICADO = "Setor Não Identificado"


def load_mappings() -> tuple[dict[str, str], dict[str, str]]:
    """Carrega mapeamentos do JSON: normalização de serviços + palavras-chave."""
    if not MAPPINGS_PATH.exists():
        print(f"   ⚠️  Arquivo {MAPPINGS_PATH} não encontrado. Usando mapeamento vazio.")
        return {}, {}

    with open(MAPPINGS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    keywords = data.get("keywords", {})
    service_norm = data.get("service_normalization", {})
    print(f"   📂 Mapeamento: {len(keywords)} palavras-chave, {len(service_norm)} normalizações de serviço")
    return keywords, service_norm


def _infer_sector_from_campaign(campaign_name: str, mappings: dict[str, str]) -> str:
    """Tenta inferir o setor a partir do nome da campanha usando palavras-chave."""
    if not campaign_name:
        return SETOR_NAO_IDENTIFICADO

    campaign_upper = campaign_name.upper()
    sorted_keys = sorted(mappings.keys(), key=len, reverse=True)
    for keyword in sorted_keys:
        if keyword.upper() in campaign_upper:
            return mappings[keyword]

    return SETOR_NAO_IDENTIFICADO


def _normalize_service(service: str, service_norm: dict[str, str]) -> str:
    """Normaliza o nome do serviço usando mapeamento ou case-insensitive match."""
    if service in service_norm:
        return service_norm[service]
    for key, normalized in service_norm.items():
        if service.upper().strip() == key.upper().strip():
            return normalized
    return service


def map_sectors(leads: list[dict]) -> list[dict]:
    """
    Preenche 'sector' e 'sector_source' em cada lead.

    Prioridade:
    1. servicesContracted normalizado (fonte de verdade quando preenchido)
    2. Inferir de campaignName via mapeamento de palavras-chave
    3. "Setor Não Identificado"
    """
    keywords, service_norm = load_mappings()

    print("🏷️  Mapeando setores dos leads...")
    contagem_fonte = Counter()

    for lead in leads:
        services = lead.get("services_contracted")
        campaign = lead.get("campaign_name", "")

        if services:
            normalized = _normalize_service(services, service_norm)
            lead["sector"] = normalized
            lead["sector_source"] = "servicesContracted"
            contagem_fonte[f"servicesContracted → {normalized}"] += 1
        else:
            sector = _infer_sector_from_campaign(campaign, keywords)
            lead["sector"] = sector
            if sector == SETOR_NAO_IDENTIFICADO:
                lead["sector_source"] = "nao_identificado"
                contagem_fonte["não identificado"] += 1
            else:
                lead["sector_source"] = "inferido_campanha"
                contagem_fonte[f"campanha → {sector}"] += 1

    print("   Fontes de mapeamento:")
    for fonte, qtd in contagem_fonte.most_common():
        print(f"   - {fonte}: {qtd}")
    print()

    return leads


def get_unmapped_report(leads: list[dict]) -> list[dict]:
    """Retorna leads que ficaram como 'Setor Não Identificado'."""
    return [
        {
            "campaign_name": l.get("campaign_name"),
            "lead_name": l.get("name"),
            "status": l.get("status"),
            "services_contracted": l.get("services_contracted"),
        }
        for l in leads
        if l.get("sector") == SETOR_NAO_IDENTIFICADO
    ]


def get_unique_services_contracted(leads: list[dict]) -> list[tuple[str, int]]:
    """Lista valores únicos de services_contracted com contagem."""
    counter: Counter = Counter()
    for lead in leads:
        val = lead.get("services_contracted")
        if val:
            counter[val] += 1
    return counter.most_common()
