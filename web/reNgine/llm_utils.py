import requests
import json
import logging
from reNgine.definitions import OLLAMA_INSTANCE, SUGGESTED_OLLAMA_MODELS, OLLAMA, OPENAI, ANTHROPIC, GEMINI

logger = logging.getLogger(__name__)

class LLMModelManager:
    def __init__(self):
        self.timeout = 10

    def get_models(self, provider, api_key=None):
        """Routes to specific provider fetchers."""
        if provider == OLLAMA:
            return self.fetch_ollama_models(api_key)
        elif provider == OPENAI:
            return self.fetch_openai_models(api_key)
        elif provider == ANTHROPIC:
            return self.fetch_anthropic_models(api_key)
        elif provider == GEMINI:
            return self.fetch_gemini_models(api_key)
        return []

    def fetch_ollama_models(self, api_key=None):
        """Combines local tags with suggested models."""
        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = requests.get(f'{OLLAMA_INSTANCE}/api/tags', headers=headers, timeout=self.timeout)
            local_models = []
            if response.status_code == 200:
                data = response.json()
                for m in data.get('models', []):
                    local_models.append({
                        'name': m['name'],
                        'is_local': True,
                        'size': f"{round(m.get('size', 0) / (1024**3), 2)} GB" if m.get('size') else 'Unknown',
                        'expertise': 'Local Model',
                        'description': f"Model installed locally in Ollama container. Modified at: {m.get('modified_at', 'Unknown')}"
                    })

            # Combine with suggested models
            all_models = local_models.copy()
            local_names = [m['name'].split(':')[0] for m in local_models]
            
            for suggested in SUGGESTED_OLLAMA_MODELS:
                if suggested['name'] not in local_names:
                    all_models.append({
                        **suggested,
                        'is_local': False
                    })
            
            return all_models
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {str(e)}")
            return SUGGESTED_OLLAMA_MODELS # Return suggestions even if Ollama is down

    def fetch_openai_models(self, api_key):
        """Lists models via OpenAI API."""
        if not api_key:
            return []
        try:
            response = requests.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=self.timeout
            )
            if response.status_code == 200:
                models = response.json().get('data', [])
                # Filter for chat models
                chat_models = [m['id'] for m in models if 'gpt' in m['id']]
                return [{'name': m, 'is_local': True, 'expertise': 'Summarization & Analysis'} for m in sorted(chat_models)]
        except Exception as e:
            logger.error(f"Error fetching OpenAI models: {str(e)}")
        return []

    def fetch_anthropic_models(self, api_key):
        """Lists models via Anthropic API (Hardcoded for now as Anthropic doesn't have a public 'list models' endpoint like OpenAI)."""
        if not api_key:
            return []
        # Anthropic doesn't currently provide a standard model list endpoint that is easily accessible without versioning
        # Providing standard Claude 3 models
        return [
            {'name': 'claude-3-5-sonnet-20240620', 'is_local': True, 'expertise': 'Advanced Summarization & Reasoning'},
            {'name': 'claude-3-opus-20240229', 'is_local': True, 'expertise': 'Highest Intelligence'},
            {'name': 'claude-3-sonnet-20240229', 'is_local': True, 'expertise': 'Balanced Performance'},
            {'name': 'claude-3-haiku-20240307', 'is_local': True, 'expertise': 'Fast Summarization'}
        ]

    def fetch_gemini_models(self, api_key):
        """Lists models via Gemini/Google API."""
        if not api_key:
            return []
        try:
            response = requests.get(
                f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}',
                timeout=self.timeout
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                gemini_models = [m['name'].replace('models/', '') for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
                return [{'name': m, 'is_local': True, 'expertise': 'Multimodal Analysis'} for m in sorted(gemini_models)]
        except Exception as e:
            logger.error(f"Error fetching Gemini models: {str(e)}")
        return []
