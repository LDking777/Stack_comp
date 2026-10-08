import logging
from typing import List, Dict, Any
import toon

logger = logging.getLogger(__name__)

class ToonContextCompressor:
    """
    Capa de Compresión de Contexto utilizando TOON (Token-Oriented Object Notation).
    Comprime registros tabulares y objetos antes de ser enviados a GPT-4o,
    reduciendo drásticamente la huella de tokens frente a JSON estándar.
    """

    @staticmethod
    def compress_records(records: List[Dict[str, Any]]) -> str:
        """
        Serializa una lista de diccionarios en formato TOON tabular compacto.
        """
        if not records:
            return "[]"
        
        try:
            # python-toon encode genera notación token-eficiente tipo:
            # [N]{col1,col2}:
            #   val1,val2
            toon_encoded = toon.encode(records)
            return toon_encoded
        except Exception as e:
            logger.warning(f"Fallo en serializador oficial toon, aplicando fallback determinista: {e}")
            return ToonContextCompressor._fallback_toon_encode(records)

    @staticmethod
    def _fallback_toon_encode(records: List[Dict[str, Any]]) -> str:
        """Fallback determinista de formato TOON en caso de estructura no estándar"""
        if not records:
            return "[]"
        keys = list(records[0].keys())
        header = f"[{len(records)}]{{{','.join(keys)}}}:"
        rows = []
        for r in records:
            vals = [str(r.get(k, '')).replace(',', ';') for k in keys]
            rows.append(f"  {','.join(vals)}")
        return header + "\n" + "\n".join(rows)

toon_compressor = ToonContextCompressor()
