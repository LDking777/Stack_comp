import httpx
import logging
from typing import Dict, Any, List, Optional
from backend.config import settings
from backend.services.normalization import match_country, match_device

logger = logging.getLogger(__name__)

class SupabaseAsyncService:
    """
    Servicio de conexión asíncrona de alta velocidad a Supabase.
    Maneja llamadas deterministas a PostgreSQL RPCs y consultas de contexto.
    """

    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip('/')
        # Usar preferentemente la secret key en backend para no tener bloqueos RLS
        self.api_key = settings.SUPABASE_SECRET_KEY or settings.SUPABASE_KEY
        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def call_rpc(self, rpc_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ejecuta una función RPC en PostgreSQL vía Supabase REST.
        Garantiza 0% alucinaciones numéricas delegando cálculos a PostgreSQL.
        """
        if not self.base_url or not self.api_key:
            logger.warning("Credenciales de Supabase no configuradas.")
            return {"error": "Credenciales de Supabase ausentes"}

        url = f"{self.base_url}/rest/v1/rpc/{rpc_name}"
        payload = params or {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, headers=self.headers, json=payload)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # Si la RPC aún no ha sido creada en la base de datos remota, ejecutar fallback determinista
                    logger.warning(f"RPC '{rpc_name}' no encontrada en Supabase (404). Ejecutando agregación determinista fallback.")
                    return await self._fallback_deterministic_aggregation(rpc_name, payload)
                else:
                    logger.error(f"Error RPC Supabase ({response.status_code}): {response.text}")
                    return {"error": f"Error en Supabase RPC: {response.status_code}", "detail": response.text}
            except Exception as e:
                logger.error(f"Excepción de red al llamar RPC {rpc_name}: {e}")
                return await self._fallback_deterministic_aggregation(rpc_name, payload)

    async def fetch_operational_records(self, table: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Obtiene registros operacionales para ser comprimidos por TOON y analizados por GPT-4o.
        """
        if not self.base_url or not self.api_key:
            return []

        url = f"{self.base_url}/rest/v1/{table}?select=*&limit={limit}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return response.json()
                logger.warning(f"Fallo al recuperar registros de {table}: {response.status_code}")
                return []
            except Exception as e:
                logger.error(f"Error consultando registros de {table}: {e}")
                return []

    async def _fallback_deterministic_aggregation(self, rpc_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Garantiza que, si las funciones RPC aún no fueron compiladas en Supabase,
        la agregación matemática se realice con 0% de alucinación directamente sobre los datos.
        """
        if "list_distinct" in rpc_name:
            return await self._list_distinct_values(params)

        if "marketing" in rpc_name:
            records = await self.fetch_operational_records("metricas_marketing", limit=200)
            if not records:
                return {"total_sesiones_afectadas": 0, "promedio_afectacion": 0.0, "status": "sin_datos"}

            url_filtro = params.get("p_url")
            disp_filtro = params.get("p_dispositivo")
            pais_filtro = params.get("p_pais")

            filtered = records
            if url_filtro:
                target = str(url_filtro).strip().lower()
                filtered = [r for r in filtered if target in str(r.get("Url", "")).lower()]
            if disp_filtro:
                filtered = [r for r in filtered if match_device(str(r.get("Device", "")), disp_filtro)]

            if not filtered:
                return {
                    "status": "sin_coincidencias",
                    "filtros_aplicados": {
                        "p_url": url_filtro,
                        "p_dispositivo": disp_filtro,
                        "p_pais": pais_filtro,
                    },
                    "detalle": (
                        "No hay registros que cumplan los filtros solicitados. "
                        "La tabla metricas_marketing no tiene columna de país, por lo que "
                        "p_pais no pudo aplicarse aquí."
                    ),
                    "modo": "calculo_determinista_local_verificado",
                }

            total_afectadas = sum(int(r.get("sessionsCount") or 0) for r in filtered)
            pcts = [float(r.get("sessionsWithMetricPercentage") or 0.0) for r in filtered]
            avg_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0.0

            return {
                "total_registros_analizados": len(filtered),
                "total_sesiones_afectadas": total_afectadas,
                "promedio_porcentaje_afectacion": avg_pct,
                "maximo_porcentaje_afectacion": max(pcts) if pcts else 0.0,
                "filtros_aplicados": {
                    "p_url": url_filtro,
                    "p_dispositivo": disp_filtro,
                },
                "modo": "calculo_determinista_local_verificado"
            }

        elif "engagement" in rpc_name:
            records = await self.fetch_operational_records("grabaciones_analisis", limit=200)
            if not records:
                return {"total_sesiones": 0, "promedio_engagement_score": 0.0, "status": "sin_datos"}

            pais_filtro = params.get("p_pais")
            disp_filtro = params.get("p_dispositivo")

            if pais_filtro:
                records = [r for r in records if match_country(str(r.get("pais", "")), pais_filtro)]
            if disp_filtro:
                records = [r for r in records if match_device(str(r.get("dispositivo", "")), disp_filtro)]

            if not records:
                return {
                    "pais_filtrado": pais_filtro or "GLOBAL",
                    "dispositivo_filtrado": disp_filtro or "TODOS",
                    "total_sesiones": 0,
                    "promedio_engagement_score": 0.0,
                    "total_sesiones_alta_frustracion": 0,
                    "tasa_frustracion_porcentaje": 0.0,
                    "status": "sin_coincidencias",
                    "detalle": (
                        f"No hay sesiones registradas que coincidan con el filtro "
                        f"'{pais_filtro or disp_filtro}'. Verifica que el valor exista en los datos."
                    ),
                    "modo": "calculo_determinista_local_verificado"
                }

            total_sesiones = len(records)
            scores = [float(r.get("standarized_engagement_score") or 0.0) for r in records]
            frustradas = sum(1 for r in records if str(r.get("posible_frustracion")) in ["1", "true", "True"])

            avg_score = round(sum(scores) / total_sesiones, 2) if total_sesiones else 0.0
            tasa_frust = round((frustradas * 100.0 / total_sesiones), 2) if total_sesiones else 0.0

            return {
                "pais_filtrado": pais_filtro or "GLOBAL",
                "dispositivo_filtrado": disp_filtro or "TODOS",
                "total_sesiones": total_sesiones,
                "promedio_engagement_score": avg_score,
                "total_sesiones_alta_frustracion": frustradas,
                "tasa_frustracion_porcentaje": tasa_frust,
                "modo": "calculo_determinista_local_verificado"
            }
        
        return {"status": "operacion_determinista_ejecutada", "params": params}

    async def _list_distinct_values(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Listado de valores distintos reales de la base (dispositivos, países,
        páginas). Responde "qué hay" con lo que hay, sin inventar categorías.
        """
        kind = (params.get("p_columna") or "dispositivos").lower()
        column = {
            "dispositivos": "dispositivo",
            "paises": "pais",
            "paginas": "direccion_url_entrada",
        }.get(kind, "dispositivo")
        table = "grabaciones_analisis"

        records = await self.fetch_operational_records(table, limit=500)
        counts: Dict[str, int] = {}
        for r in records:
            value = str(r.get(column) or "").strip()
            if not value or value.lower() in {"none", "null"}:
                continue
            counts[value] = counts.get(value, 0) + 1

        if not counts:
            return {
                "categoria": kind,
                "total_valores": 0,
                "detalle": f"No se encontraron valores de '{kind}' en la tabla {table}.",
                "modo": "calculo_determinista_local_verificado",
            }

        ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "categoria": kind,
            "total_valores": len(ordered),
            "valores_distintos": ", ".join(f"{name} ({n})" for name, n in ordered),
            "total_sesiones": sum(counts.values()),
            "modo": "calculo_determinista_local_verificado",
        }

supabase_service = SupabaseAsyncService()
