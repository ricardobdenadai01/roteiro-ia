import httpx
from app.config import settings

TIMEOUT_SECONDS = 60


def fetch_crm_data(start_date: str, end_date: str) -> dict:
    """
    Busca dados completos da API do CRM.

    Retorna dict com:
    - leads: lista rica de mondayLeadsList (com adName, servicesContracted, valores, etc.)
    - campaigns: lista de campanhas com spend, metaLeads, mondayLeads
    - top_creatives: ranking de ads por leads gerados (engajamento)
    - top_creatives_by_sales: ranking de ads por valor de vendas
    - totals: totais gerais (spend, metaLeads, mondayLeads)
    """
    url = settings.CRM_API_URL
    params = {"startDate": start_date, "endDate": end_date}
    headers = {
        "x-api-key": settings.CRM_API_KEY,
        "Content-Type": "application/json",
    }

    print(f"\n📡 Buscando dados da API do CRM...")
    print(f"   URL: {url}")
    print(f"   Período: {start_date} → {end_date}")

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.get(url, params=params, headers=headers)

        if response.status_code == 401:
            raise RuntimeError("❌ Erro 401 — API Key inválida. Verifique CRM_API_KEY no .env")
        if response.status_code == 404:
            raise RuntimeError(f"❌ Erro 404 — Endpoint não encontrado: {url}")
        if response.status_code >= 500:
            raise RuntimeError(f"❌ Erro {response.status_code} — Erro interno do servidor.")

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or "data" not in data:
            raise RuntimeError(f"❌ Formato inesperado. Tipo: {type(data)}")

        api_data = data["data"]
        funnel = api_data.get("funnelMetrics", {})
        totals = api_data.get("totals", {})

        leads = funnel.get("mondayLeadsList", [])
        campaigns = api_data.get("campaigns", [])
        top_creatives = funnel.get("topCreatives", [])
        top_creatives_by_sales = funnel.get("topCreativesBySales", [])

        print(f"   ✅ {len(leads)} leads com dados completos")
        print(f"   ✅ {len(campaigns)} campanhas")
        print(f"   ✅ {len(top_creatives)} ads no ranking de engajamento")
        print(f"   ✅ Spend total: R$ {totals.get('spend', 0):,.2f}\n")

        return {
            "leads": leads,
            "campaigns": campaigns,
            "top_creatives": top_creatives,
            "top_creatives_by_sales": top_creatives_by_sales,
            "totals": totals,
            "funnel": funnel,
        }

    except httpx.TimeoutException:
        raise RuntimeError(f"❌ Timeout — a API não respondeu em {TIMEOUT_SECONDS}s.")
    except httpx.ConnectError:
        raise RuntimeError("❌ Erro de conexão — não foi possível conectar à API.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"❌ Erro HTTP {e.response.status_code}: {e.response.text[:300]}")
