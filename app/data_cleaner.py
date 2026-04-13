from collections import Counter

STATUS_VENDAS = {"Vendido", "Negociação"}


def _normalize_status(raw: str | None) -> str:
    if not raw:
        return "(vazio)"
    s = raw.strip()
    if s in STATUS_VENDAS:
        return s
    if "Negocia" in s:
        return "Negociação"
    return s


def _safe(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def clean_leads(raw_leads: list[dict]) -> tuple[list[dict], dict]:
    """
    Filtra leads Vendido/Negociação e normaliza campos.
    Retorna (leads_filtrados, resumo).
    """
    total = len(raw_leads)
    status_counter: Counter = Counter()

    for lead in raw_leads:
        status_counter[_normalize_status(lead.get("status"))] += 1

    print("📋 Status encontrados:")
    for s, count in status_counter.most_common():
        marcador = " ✔" if s in STATUS_VENDAS else ""
        print(f"   - {s} ({count}){marcador}")

    filtered: list[dict] = []
    for lead in raw_leads:
        status = _normalize_status(lead.get("status"))
        if status not in STATUS_VENDAS:
            continue

        filtered.append({
            "name": _safe(lead.get("name")),
            "status": status,
            "campaign_name": _safe(lead.get("campaignName")),
            "ad_name": _safe(lead.get("adName")),
            "quality": _safe(lead.get("quality")),
            "services_contracted": _safe(lead.get("servicesContracted")),
            "service_type": _safe(lead.get("serviceType")),
            "sdr": _safe(lead.get("sdr")),
            "closer": _safe(lead.get("closer")),
            "implantation_value": lead.get("implantationValue"),
            "mrr_value": lead.get("mrrValue"),
            "product_value": lead.get("productValue"),
            "event_value": lead.get("eventValue"),
            "date_sold": lead.get("dateSold"),
            "raw_data": lead,
        })

    vendidos = sum(1 for l in filtered if l["status"] == "Vendido")
    negociacao = sum(1 for l in filtered if l["status"] == "Negociação")

    resumo = {
        "total_api": total,
        "total_vendido": vendidos,
        "total_negociacao": negociacao,
        "total_filtrados": len(filtered),
        "total_descartados": total - len(filtered),
        "status_encontrados": dict(status_counter.most_common()),
    }

    print(f"\n🔍 Filtrados: {vendidos} Vendidos + {negociacao} Negociação = {len(filtered)}")
    print(f"   Descartados: {total - len(filtered)}\n")

    return filtered, resumo
