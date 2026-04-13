import argparse
import json
import sys

from app.config import settings
from app.api_client import fetch_crm_data
from app.data_cleaner import clean_leads
from app.ranking import (
    rank_campaigns_by_sales,
    rank_ads_by_sales,
    rank_campaigns_by_engagement,
    rank_ads_by_engagement,
)
from app.database import (
    clear_tables,
    insert_leads,
    insert_campaign_sales,
    insert_ad_sales,
    insert_campaign_engagement,
    insert_ad_engagement,
)


SEP = "═" * 62
THIN = "━" * 62


def _brl(value: float) -> str:
    if not value:
        return "R$ 0"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _print_header(start: str, end: str) -> None:
    print(f"\n{SEP}")
    print(f"  RELATÓRIO DE PERFORMANCE — {start} a {end}")
    print(f"{SEP}\n")


def _print_resumo(resumo: dict, totals: dict) -> None:
    print("📡 RESUMO GERAL:")
    print(f"   Leads totais na API: {resumo['total_api']}")
    print(f"   Vendidos: {resumo['total_vendido']}")
    print(f"   Em Negociação: {resumo['total_negociacao']}")
    print(f"   Spend total: {_brl(totals.get('spend', 0))}")
    print()


def _print_sales_campaigns(campaigns: list[dict]) -> None:
    print(f"\n{SEP}")
    print("🏆 CAMPANHAS POR VENDAS (qual roteiro/abordagem funciona)")
    print(f"{SEP}\n")

    for i, c in enumerate(campaigns, 1):
        if c["vendidos"] == 0 and c["negociacao"] == 0:
            continue

        print(f"  {i}. {c['campaign_name']}")
        print(f"     📈 {c['vendidos']} vendas | {c['negociacao']} em negociação | {_brl(c['valor_total'])}")

        if c.get("servicos"):
            svcs = ", ".join(f"{s} ({n})" for s, n in sorted(c["servicos"].items(), key=lambda x: -x[1]))
            print(f"     🏷️  Serviços: {svcs}")

        ads_with_sales = [a for a in c["ads"] if a["vendidos"] > 0]
        ads_negotiation = [a for a in c["ads"] if a["vendidos"] == 0 and a["negociacao"] > 0]

        if ads_with_sales:
            print(f"     🎬 Ads com vendas:")
            for a in ads_with_sales:
                print(f"        • {a['ad_name']} — {a['vendidos']}v / {a['negociacao']}n ({_brl(a['valor'])})")

        if ads_negotiation:
            print(f"     ⏳ Ads só com negociação:")
            for a in ads_negotiation[:3]:
                print(f"        • {a['ad_name']} — {a['negociacao']} em negociação")

        print()


def _print_sales_ads(ads: list[dict]) -> None:
    print(f"\n{SEP}")
    print("🎬 TOP ADS (VÍDEOS) POR VENDAS — ranking geral")
    print(f"{SEP}\n")

    for i, a in enumerate(ads, 1):
        if a["vendidos"] == 0:
            break
        camps = ", ".join(a["campanhas"])
        print(f"  {i}. {a['ad_name']}")
        print(f"     {a['vendidos']} vendas | {a['negociacao']} negociação | {_brl(a['valor'])}")
        print(f"     Campanhas: {camps}")
        print()

    negociacao_only = [a for a in ads if a["vendidos"] == 0 and a["negociacao"] > 0]
    if negociacao_only:
        print(f"  {THIN}")
        print(f"  ⏳ Ads só com negociação (potencial):")
        for a in negociacao_only[:5]:
            print(f"     • {a['ad_name']} — {a['negociacao']} em negociação")
        print()


def _print_engagement_campaigns(campaigns: list[dict]) -> None:
    print(f"\n{SEP}")
    print("📣 CAMPANHAS POR ENGAJAMENTO (atenção/divulgação de marca)")
    print(f"{SEP}\n")

    for i, c in enumerate(campaigns[:15], 1):
        name = c["campaign_name"]
        leads = c["monday_leads"]
        spend = _brl(c["spend"])
        cpl = _brl(c["cpl"])
        vendidos = c["vendidos"]

        print(f"  {i}. {name}")
        print(f"     {leads} leads | {spend} gasto | CPL: {cpl} | {vendidos} vendas")
        print()


def _print_engagement_ads(ads: list[dict]) -> None:
    print(f"\n{SEP}")
    print("🎬 TOP ADS POR ENGAJAMENTO (quais vídeos prendem atenção)")
    print(f"{SEP}\n")

    for i, a in enumerate(ads, 1):
        print(f"  {i}. {a['ad_name']}")
        print(f"     {a['leads']} leads | {a['qualified']} qualificados | {a['sales']} vendas")
        print()


def _print_highlights(
    camp_sales: list[dict],
    ad_sales: list[dict],
    camp_engagement: list[dict],
    ad_engagement: list[dict],
) -> None:
    print(f"\n{SEP}")
    print("⭐ DESTAQUES — RESUMO RÁPIDO")
    print(f"{SEP}\n")

    # Top 3 Ads por vendas + negociação
    ads_combined = sorted(ad_sales, key=lambda a: a["vendidos"] + a["negociacao"], reverse=True)
    print("  🏆 TOP 3 ADS — VENDAS + NEGOCIAÇÃO (melhor conversão):")
    for i, a in enumerate(ads_combined[:3], 1):
        total = a["vendidos"] + a["negociacao"]
        print(f"     {i}. {a['ad_name']}")
        print(f"        {a['vendidos']}v + {a['negociacao']}n = {total} | {_brl(a['valor'])}")
    print()

    # Top 3 Ads por engajamento (visualização/cliques)
    print("  👁️  TOP 3 ADS — ENGAJAMENTO (mais atenção/cliques):")
    for i, a in enumerate(ad_engagement[:3], 1):
        print(f"     {i}. {a['ad_name']}")
        print(f"        {a['leads']} leads | {a['qualified']} qualificados | {a['sales']} vendas")
    print()

    # Melhor campanha para venda
    best_sale = camp_sales[0] if camp_sales else None
    if best_sale:
        print("  💰 MELHOR CAMPANHA PARA VENDA:")
        print(f"     {best_sale['campaign_name']}")
        print(f"     {best_sale['vendidos']} vendas | {best_sale['negociacao']} negociação | {_brl(best_sale['valor_total'])}")
    print()

    # Melhor campanha para engajamento
    best_eng = camp_engagement[0] if camp_engagement else None
    if best_eng:
        print("  📣 MELHOR CAMPANHA PARA ENGAJAMENTO:")
        print(f"     {best_eng['campaign_name']}")
        print(f"     {best_eng['monday_leads']} leads | {_brl(best_eng['spend'])} gasto | CPL: {_brl(best_eng['cpl'])}")
    print()


def _prepare_leads_for_db(leads: list[dict]) -> list[dict]:
    result = []
    for lead in leads:
        row = {k: v for k, v in lead.items() if k != "raw_data"}
        row["raw_data"] = json.loads(json.dumps(lead.get("raw_data", {}), default=str))
        result.append(row)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta e análise de dados do CRM")
    parser.add_argument("--start", default=settings.DEFAULT_START_DATE, help="Data início (YYYY-MM-DD)")
    parser.add_argument("--end", default=settings.DEFAULT_END_DATE, help="Data fim (YYYY-MM-DD)")
    args = parser.parse_args()

    start_date = args.start
    end_date = args.end

    try:
        # 1. Buscar dados
        api = fetch_crm_data(start_date, end_date)

        if not api["leads"]:
            print("❌ Nenhum dado retornado.")
            sys.exit(1)

        # 2. Filtrar leads Vendido + Negociação
        leads, resumo = clean_leads(api["leads"])

        # 3. Rankings de vendas (baseado em leads filtrados)
        camp_sales = rank_campaigns_by_sales(leads)
        ad_sales = rank_ads_by_sales(leads)

        # 4. Rankings de engajamento (baseado em dados brutos da API)
        camp_engagement = rank_campaigns_by_engagement(api["campaigns"])
        ad_engagement = rank_ads_by_engagement(api["top_creatives"])

        # 5. Relatório no terminal
        _print_header(start_date, end_date)
        _print_resumo(resumo, api["totals"])
        _print_highlights(camp_sales, ad_sales, camp_engagement, ad_engagement)
        _print_sales_campaigns(camp_sales)
        _print_sales_ads(ad_sales)
        _print_engagement_campaigns(camp_engagement)
        _print_engagement_ads(ad_engagement)

        # 6. Salvar no Supabase
        print(f"\n{SEP}")
        print("💾 SALVANDO NO SUPABASE")
        print(f"{SEP}")

        clear_tables()

        insert_leads(_prepare_leads_for_db(leads))
        insert_campaign_sales(camp_sales)
        insert_ad_sales(ad_sales)
        insert_campaign_engagement(camp_engagement)
        insert_ad_engagement(ad_engagement)

        print(f"\n✅ Dados salvos no Supabase com sucesso!")
        print(f"\n{SEP}")
        print("  COLETA FINALIZADA")
        print(f"{SEP}\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário.")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
