"""Cliente para LMStudio (API compatible con OpenAI).

LMStudio expone una API REST compatible con OpenAI en http://localhost:1234/v1.
Este módulo proporciona una interfaz simple para interactuar con ella.
"""

import json
from typing import Any, Callable, Dict, Generator, List, Optional

from openai import OpenAI

from .. import config


class LMStudioClient:
    """Cliente para interactuar con LMStudio.
    
    Example:
        >>> client = LMStudioClient()
        >>> response = client.chat("¿Cuál es la población de Canarias?")
        >>> print(response)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Inicializa el cliente.
        
        Args:
            base_url: URL del servidor LMStudio (default: localhost:1234)
            model: Nombre del modelo (LMStudio usa el modelo cargado)
            temperature: Temperatura para generación
            max_tokens: Máximo de tokens en respuesta
        """
        llm_config = config.get_llm_config()
        
        self.base_url = base_url or llm_config.get('base_url', 'http://localhost:1234/v1')
        self.model = model or llm_config.get('model', 'local-model')
        self.temperature = temperature or llm_config.get('temperature', 0.7)
        self.max_tokens = max_tokens or llm_config.get('max_tokens', 4096)
        
        # Cliente OpenAI configurado para LMStudio
        self._client = OpenAI(
            base_url=self.base_url,
            api_key="not-needed"  # LMStudio no requiere API key
        )
        
        # Tools registrados
        self._tools: Dict[str, Callable] = {}
        self._tool_definitions: List[Dict] = []
    
    def register_tool(self, name: str, func: Callable, description: str, parameters: Dict) -> None:
        """Registra una función como tool disponible para el LLM.
        
        Args:
            name: Nombre del tool
            func: Función a ejecutar
            description: Descripción para el LLM
            parameters: Esquema JSON de parámetros
        """
        self._tools[name] = func
        self._tool_definitions.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
    
    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        use_tools: bool = True,
        debug: bool = False,
    ) -> str:
        """Envía un mensaje y obtiene una respuesta.
        
        Args:
            message: Mensaje del usuario
            system_prompt: Prompt de sistema (opcional)
            history: Historial de conversación previo
            use_tools: Si usar los tools registrados
            debug: Si guardar llamadas a herramientas para debugging
        
        Returns:
            Respuesta del modelo como string.
        """
        # Inicializar lista de tool calls para debug
        self._last_tool_calls = []
        self._debug = debug
        messages = []
        
        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Historial
        if history:
            messages.extend(history)
        
        # Mensaje actual
        messages.append({"role": "user", "content": message})
        
        # Configuración de la llamada
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # Añadir tools si están disponibles y habilitados
        if use_tools and self._tool_definitions:
            kwargs["tools"] = self._tool_definitions
            kwargs["tool_choice"] = "auto"
        
        try:
            response = self._client.chat.completions.create(**kwargs)
            
            # Procesar respuesta
            choice = response.choices[0]
            
            # Si hay tool calls estructurados, ejecutarlos
            if choice.message.tool_calls:
                return self._handle_tool_calls(choice.message, messages)
            
            # Verificar si hay tool calls en el texto (algunos modelos lo hacen así)
            content = choice.message.content or ""
            text_tool_call = self._extract_tool_call_from_text(content)
            if text_tool_call and use_tools:
                return self._handle_text_tool_call(text_tool_call, messages)
            
            return content
            
        except Exception as e:
            config.logger.error(f"Error en LMStudio: {e}")
            raise
    
    def _extract_tool_call_from_text(self, content: str) -> Optional[Dict]:
        """Extrae un tool call del texto si el modelo lo devuelve como JSON."""
        import re
        
        # Limpiar el contenido - algunos modelos añaden espacios/newlines
        clean_content = content.strip()
        
        # Si el contenido parece ser solo un JSON, intentar parsearlo directamente
        if clean_content.startswith('{') and clean_content.endswith('}'):
            try:
                tool_data = json.loads(clean_content)
                if 'name' in tool_data:
                    return {
                        'name': tool_data['name'],
                        'arguments': tool_data.get('parameters', tool_data.get('arguments', {}))
                    }
            except json.JSONDecodeError:
                pass
        
        # Buscar JSON embebido en el texto
        # Encontrar la primera { y la última } balanceada
        json_start = -1
        for i, char in enumerate(content):
            if char == '{':
                json_start = i
                break
        
        if json_start == -1:
            return None
        
        # Encontrar el cierre balanceado
        brace_count = 0
        json_end = json_start
        for i, char in enumerate(content[json_start:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = json_start + i + 1
                    break
        
        if json_end <= json_start:
            return None
        
        json_str = content[json_start:json_end]
        
        try:
            tool_data = json.loads(json_str)
            
            # Verificar que tiene estructura de tool call
            if 'name' in tool_data:
                return {
                    'name': tool_data['name'],
                    'arguments': tool_data.get('parameters', tool_data.get('arguments', {}))
                }
            elif 'function' in tool_data and isinstance(tool_data['function'], dict):
                func = tool_data['function']
                return {
                    'name': func.get('name'),
                    'arguments': func.get('parameters', func.get('arguments', {}))
                }
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _normalize_tool_args(self, func_name: str, args: Dict) -> Dict:
        """Normaliza los nombres de parámetros para compatibilidad con variaciones del LLM."""
        normalized = {}
        
        # Mapeo de nombres alternativos a nombres correctos
        param_aliases = {
            'indicator_code': 'code',
            'indicatorCode': 'code',
            'indicator': 'code',
            'cod': 'code',
            'codigo': 'code',
            'busqueda': 'query',
            'search': 'query',
            'texto': 'query',
            'max': 'limit',
            'max_results': 'limit',
            'numero': 'limit',
            'geography': 'geo',
            'geographic': 'geo',
            'geografico': 'geo',
            'temporal': 'time',
            'periodo': 'time',
            'year': 'time',
        }
        
        for key, value in args.items():
            # Normalizar el nombre del parámetro
            normalized_key = param_aliases.get(key.lower(), key)
            normalized[normalized_key] = value
        
        return normalized
    
    def _handle_text_tool_call(self, tool_call: Dict, messages: List[Dict]) -> str:
        """Procesa un tool call extraído del texto."""
        func_name = tool_call.get('name')
        func_args = tool_call.get('arguments', {})
        
        if isinstance(func_args, str):
            try:
                func_args = json.loads(func_args)
            except json.JSONDecodeError:
                func_args = {}
        
        # Normalizar parámetros comunes (el LLM a veces usa nombres ligeramente diferentes)
        func_args = self._normalize_tool_args(func_name, func_args)
        
        config.logger.debug(f"Ejecutando tool desde texto: {func_name}({func_args})")
        
        if func_name in self._tools:
            try:
                result = self._tools[func_name](**func_args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
            except TypeError as e:
                # Si hay error de parámetros, intentar ejecutar sin los parámetros problemáticos
                config.logger.warning(f"Error de parámetros en {func_name}: {e}")
                try:
                    # Intentar solo con parámetros conocidos
                    result = self._tools[func_name]()
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                except Exception as e2:
                    result_str = json.dumps({"error": str(e2)})
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
        else:
            return f"Tool '{func_name}' no encontrado"
        
        # Añadir el resultado al contexto y pedir respuesta final
        messages.append({
            "role": "assistant",
            "content": f"Ejecutando herramienta {func_name}..."
        })
        messages.append({
            "role": "user", 
            "content": f"Resultado de la herramienta {func_name}:\n```json\n{result_str}\n```\n\nPor favor, interpreta estos datos y responde al usuario. Recuerda incluir el bloque de trazabilidad al final."
        })
        
        # Obtener respuesta final
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        
        return response.choices[0].message.content or ""
    
    def _handle_tool_calls(self, assistant_message, messages: List[Dict]) -> str:
        """Procesa las llamadas a tools y obtiene respuesta final."""
        # Añadir mensaje del asistente con tool calls
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in assistant_message.tool_calls
            ]
        })
        
        # Ejecutar cada tool
        for tool_call in assistant_message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            if func_name in self._tools:
                try:
                    result = self._tools[func_name](**func_args)
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})
                    result = {"error": str(e)}
            else:
                result_str = json.dumps({"error": f"Tool '{func_name}' not found"})
                result = {"error": f"Tool '{func_name}' not found"}
            
            # Guardar para debug
            self._last_tool_calls.append({
                "name": func_name,
                "args": func_args,
                "result": result
            })
            
            # Añadir resultado del tool
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str
            })
        
        # Obtener respuesta final del LLM
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        
        return response.choices[0].message.content or ""
    
    def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[str, None, None]:
        """Envía un mensaje y obtiene respuesta en streaming.
        
        Yields:
            Fragmentos de texto de la respuesta.
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": message})
        
        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            config.logger.error(f"Error en streaming: {e}")
            raise
    
    def is_available(self) -> bool:
        """Verifica si LMStudio está disponible."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


# Cliente singleton para uso global
_client: Optional[LMStudioClient] = None


def get_client() -> LMStudioClient:
    """Obtiene el cliente singleton de LMStudio."""
    global _client
    if _client is None:
        _client = LMStudioClient()
    return _client
