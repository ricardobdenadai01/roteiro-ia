from collections import defaultdict


def _sum_values(lead: dict) -> float:
    total = 0
    for key in ("implantation_value", "mrr_value", "product_value", "event_value"):
        v = lead.get(key)
        if v is not None:
            total += v
    return total


# ═══════════════════════════════════════════════════════════
# ANÁLISE 1: PERFORMANCE DE VENDAS
# Quais campanhas e ads mais vendem?
# ═══════════════════════════════════════════════════════════


def rank_campaigns_by_sales(leads: list[dict]) -> list[dict]:
    """
    Ranking de campanhas por vendas (Vendido).
    Também conta Negociação como pipeline.
    """
    campanhas: dict[str, dict] = {}

    for lead in leads:
        camp = lead.get("campaign_name") or "(sem campanha)"
        status = lead.get("status")

        if camp not in campanhas:
            campanhas[camp] = {
                "campaign_name": camp,
                "vendidos": 0,
                "negociacao": 0,
                "valor_total": 0,
                "ads": defaultdict(lambda: {"vendidos": 0, "negociacao": 0, "valor": 0}),
                "servicos": defaultdict(int),
            }

        entry = campanhas[camp]
        ad = lead.get("ad_name") or "(sem anúncio)"

        if status == "Vendido":
            entry["vendidos"] += 1
            entry["valor_total"] += _sum_values(lead)
            entry["ads"][ad]["vendidos"] += 1
            entry["ads"][ad]["valor"] += _sum_values(lead)
            svc = lead.get("services_contracted")
            if svc:
                entry["servicos"][svc] += 1
        elif status == "Negociação":
            entry["negociacao"] += 1
            entry["ads"][ad]["negociacao"] += 1

    result = []
    for d in campanhas.values():
        ads_list = []
        for ad_name, ad_data in d["ads"].items():
            ads_list.append({
                "ad_name": ad_name,
                "vendidos": ad_data["vendidos"],
                "negociacao": ad_data["negociacao"],
                "valor": round(ad_data["valor"], 2),
            })
        ads_list.sort(key=lambda x: x["vendidos"], reverse=True)

        result.append({
            "campaign_name": d["campaign_name"],
            "vendidos": d["vendidos"],
            "negociacao": d["negociacao"],
            "valor_total": round(d["valor_total"], 2),
            "ads": ads_list,
            "servicos": dict(d["servicos"]),
        })

    result.sort(key=lambda x: x["vendidos"], reverse=True)
    print(f"📊 Ranking de vendas: {len(result)} campanhas analisadas.")
    return result


def rank_ads_by_sales(leads: list[dict]) -> list[dict]:
    """
    Ranking flat de ads por vendas (Vendido), independente de campanha.
    """
    ads: dict[str, dict] = {}

    for lead in leads:
        ad = lead.get("ad_name")
        if not ad:
            continue
        status = lead.get("status")
        camp = lead.get("campaign_name") or "(sem campanha)"

        if ad not in ads:
            ads[ad] = {
                "ad_name": ad,
                "vendidos": 0,
                "negociacao": 0,
                "valor": 0,
                "campanhas": set(),
            }

        entry = ads[ad]
        entry["campanhas"].add(camp)
        if status == "Vendido":
            entry["vendidos"] += 1
            entry["valor"] += _sum_values(lead)
        elif status == "Negociação":
            entry["negociacao"] += 1

    result = []
    for d in ads.values():
        result.append({
            "ad_name": d["ad_name"],
            "vendidos": d["vendidos"],
            "negociacao": d["negociacao"],
            "valor": round(d["valor"], 2),
            "campanhas": sorted(d["campanhas"]),
        })

    result.sort(key=lambda x: x["vendidos"], reverse=True)
    print(f"📊 Ranking de ads por vendas: {len(result)} anúncios analisados.")
    return result


# ═══════════════════════════════════════════════════════════
# ANÁLISE 2: PERFORMANCE DE ENGAJAMENTO
# Quais campanhas e ads geram mais atenção? (ignora status)
# ═══════════════════════════════════════════════════════════


def rank_campaigns_by_engagement(campaigns_raw: list[dict]) -> list[dict]:
    """
    Ranking de campanhas por volume de leads (engajamento/atenção).
    Usa dados de campanha da API (metaLeads, spend, mondayLeads).
    """
    result = []
    for c in campaigns_raw:
        name = c.get("campaignName", "")
        meta_leads = c.get("metaLeads", 0) or 0
        monday_leads = c.get("mondayLeads", 0) or 0
        spend = c.get("spend", 0) or 0

        if spend == 0:
            continue

        cpl = round(spend / monday_leads, 2) if monday_leads > 0 else 0

        vendidos = 0
        by_status = c.get("mondayByStatus", {})
        for status_name, count in by_status.items():
            if status_name == "Vendido":
                vendidos = count

        result.append({
            "campaign_name": name,
            "monday_leads": monday_leads,
            "meta_leads": meta_leads,
            "spend": round(spend, 2),
            "cpl": cpl,
            "vendidos": vendidos,
            "status_breakdown": by_status,
        })

    result.sort(key=lambda x: x["monday_leads"], reverse=True)
    print(f"📊 Ranking de engajamento: {len(result)} campanhas com leads.")
    return result


def rank_ads_by_engagement(top_creatives: list[dict]) -> list[dict]:
    """
    Ranking de ads por leads gerados (engajamento/atenção).
    Usa dados de funnelMetrics.topCreatives da API.
    """
    result = []
    for ad in top_creatives:
        result.append({
            "ad_name": ad.get("adName", ""),
            "leads": ad.get("leads", 0),
            "qualified": ad.get("qualified", 0),
            "sales": ad.get("sales", 0),
        })

    result.sort(key=lambda x: x["leads"], reverse=True)
    print(f"📊 Ranking de ads por engajamento: {len(result)} anúncios.")
    return result
