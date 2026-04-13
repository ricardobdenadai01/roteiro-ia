from supabase import create_client, Client
from app.config import settings

BATCH_SIZE = 500

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def _insert_batch(table: str, data: list[dict]) -> None:
    client = get_client()
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i : i + BATCH_SIZE]
        client.table(table).insert(batch).execute()
        print(f"   💾 {table}: {min(i + BATCH_SIZE, len(data))}/{len(data)}")


def insert_leads(data: list[dict]) -> None:
    if not data:
        return
    print(f"\n📥 Inserindo {len(data)} leads...")
    _insert_batch("leads", data)
    print(f"   ✅ {len(data)} leads inseridos!")


def insert_campaign_sales(data: list[dict]) -> None:
    if not data:
        return
    print(f"\n📥 Inserindo {len(data)} campanhas (vendas)...")
    _insert_batch("campaign_sales", data)
    print(f"   ✅ OK!")


def insert_ad_sales(data: list[dict]) -> None:
    if not data:
        return
    print(f"\n📥 Inserindo {len(data)} ads (vendas)...")
    _insert_batch("ad_sales", data)
    print(f"   ✅ OK!")


def insert_campaign_engagement(data: list[dict]) -> None:
    if not data:
        return
    print(f"\n📥 Inserindo {len(data)} campanhas (engajamento)...")
    _insert_batch("campaign_engagement", data)
    print(f"   ✅ OK!")


def insert_ad_engagement(data: list[dict]) -> None:
    if not data:
        return
    print(f"\n📥 Inserindo {len(data)} ads (engajamento)...")
    _insert_batch("ad_engagement", data)
    print(f"   ✅ OK!")


def clear_tables() -> None:
    resposta = input(
        "\n⚠️  Limpar dados anteriores antes de inserir? (s/n): "
    ).strip().lower()

    if resposta != "s":
        print("❌ Abortando para evitar duplicatas.")
        raise SystemExit(1)

    client = get_client()
    tabelas = ["ad_engagement", "campaign_engagement", "ad_sales", "campaign_sales", "leads"]

    for tabela in tabelas:
        client.table(tabela).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"   🗑️  {tabela} limpa.")

    print("   ✅ Tabelas limpas!\n")
