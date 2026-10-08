import asyncio
from backend.services.intent_router import intent_router
from backend.services.supabase_service import supabase_service
from backend.services.toon_service import toon_compressor
from backend.services.insights_service import insights_generator
from backend.schemas.router_schemas import IntentTrigger

async def test_suite():
    print("=" * 60)
    print("🧪 INICIANDO TEST DEL FLUJO DE INTENCIONES")
    print("=" * 60)

    test_queries = [
        "¿Cuáles son los RageClicks y DeadClicks en /checkout/pago-tarjeta?",
        "Analiza por qué los usuarios de México tienen tanta frustración y qué podemos hacer",
        "Calcula la suma total de sesiones afectadas por métricas"
    ]

    for q in test_queries:
        print(f"\n💬 Consulta: \"{q}\"")
        decision, lat_ms = await intent_router.route_intent(q)
        print(f"  ⚡ Fast Path Router: {decision.trigger.value} (Latencia: {lat_ms:.1f}ms, Confianza: {decision.confidence_score})")
        print(f"  🎯 RPC Mapeada: {decision.rpc_intent.rpc_name} | Heavy Path Requerido: {decision.requires_heavy_path}")

        # Deterministic RPC execution
        rpc_result = await supabase_service.call_rpc(
            decision.rpc_intent.rpc_name or "rpc_get_marketing_kpis",
            {"p_pais": decision.rpc_intent.country_filter, "p_url": decision.rpc_intent.url_filter}
        )
        print(f"  🗄️ Resultado Determinista: {list(rpc_result.keys()) if isinstance(rpc_result, dict) else rpc_result}")

        # TOON compression test
        if decision.requires_heavy_path or decision.trigger == IntentTrigger.TRIGGER_INSIGHTS:
            records = await supabase_service.fetch_operational_records("grabaciones_analisis", limit=3)
            toon_out = toon_compressor.compress_records(records)
            print(f"  📦 Contexto TOON:\n{toon_out}")

            # Heavy Path
            insight, h_lat = await insights_generator.generate_insight(q, rpc_result, toon_out)
            print(f"  🧠 Heavy Path (GPT-4o, {h_lat:.1f}ms): {insight.executive_summary[:90]}...")

    print("\n✅ Suite de pruebas ejecutada con éxito.")

if __name__ == "__main__":
    asyncio.run(test_suite())
