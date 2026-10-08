from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MCPTool(ABC):
    """Interfaz abstracta para una herramienta compatible con Model Context Protocol (MCP)"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la herramienta externa de forma asíncrona"""
        pass

class MCPResource(ABC):
    """Interfaz abstracta para un recurso de contexto externo expuesto vía MCP"""
    uri: str
    name: str

    @abstractmethod
    async def read(self) -> str:
        """Lee el contenido textual o serializado del recurso"""
        pass

class MCPConnectorRegistry:
    """
    Registro y orquestador central de conectores MCP (Model Context Protocol).
    Permite acoplar servidores MCP externos al Heavy Path de GPT-4o
    para extender la recuperación de contexto a CRMs, Analytics o APIs externas.
    """

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self.enabled: bool = True

    def register_tool(self, tool: MCPTool):
        self._tools[tool.name] = tool
        logger.info(f"Herramienta MCP registrada: {tool.name}")

    def register_resource(self, resource: MCPResource):
        self._resources[resource.uri] = resource
        logger.info(f"Recurso MCP registrado: {resource.uri}")

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if tool_name not in self._tools:
            logger.warning(f"Herramienta MCP no encontrada: {tool_name}")
            return None
        return await self._tools[tool_name].execute(arguments)

    async def get_all_context_resources(self) -> List[Dict[str, str]]:
        """Recupera el contexto agregado de todos los recursos MCP conectados"""
        results = []
        for uri, res in self._resources.items():
            try:
                content = await res.read()
                results.append({"uri": uri, "name": res.name, "content": content})
            except Exception as e:
                logger.error(f"Error leyendo recurso MCP {uri}: {e}")
        return results

mcp_registry = MCPConnectorRegistry()
