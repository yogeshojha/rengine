import openai
import re
import requests
from reNgine.common_func import parse_llm_vulnerability_report
from reNgine.definitions import (
    VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE, 
    ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT, 
    OLLAMA_INSTANCE,
    OLLAMA, OPENAI, ANTHROPIC, GEMINI
)
from langchain_community.llms import Ollama
from dashboard.models import LLMConfig

class LLMBaseGenerator:
    def __init__(self, logger):
        self.logger = logger
        self.config = LLMConfig.objects.filter(is_active=True).first()
        if not self.config:
            self.logger.warning("No active LLM configuration found. Defaulting to Ollama/llama3.")
            # Fallback or create a dummy config if needed
            self.model_name = 'llama3'
            self.provider = OLLAMA
            self.api_key = None
        else:
            self.model_name = self.config.selected_model
            self.provider = self.config.provider
            self.api_key = self.config.api_key

    def _call_llm(self, system_message, user_message):
        """Unified method to call the configured LLM provider."""
        if self.provider == OLLAMA:
            return self._call_ollama(system_message, user_message)
        elif self.provider == OPENAI:
            return self._call_openai(system_message, user_message)
        elif self.provider == ANTHROPIC:
            return self._call_anthropic(system_message, user_message)
        elif self.provider == GEMINI:
            return self._call_gemini(system_message, user_message)
        return "Error: Unsupported LLM Provider"

    def _call_ollama(self, system_message, user_message):
        try:
            prompt = system_message + "\nUser: " + user_message
            prompt = re.sub(r'\t', '', prompt)
            llm = Ollama(base_url=OLLAMA_INSTANCE, model=self.model_name)
            return llm.invoke(prompt)
        except Exception as e:
            self.logger.error(f"Ollama Error: {str(e)}")
            return f"Error: {str(e)}"

    def _call_openai(self, system_message, user_message):
        if not self.api_key:
            return "Error: OpenAI API Key not set"
        try:
            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': user_message}
                ]
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            self.logger.error(f"OpenAI Error: {str(e)}")
            return f"Error: {str(e)}"

    def _call_anthropic(self, system_message, user_message):
        if not self.api_key:
            return "Error: Anthropic API Key not set"
        try:
            # Using requests for Anthropic to avoid adding SDK dependency
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": self.model_name,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": f"{system_message}\n\n{user_message}"}]
            }
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
            return response.json()['content'][0]['text']
        except Exception as e:
            self.logger.error(f"Anthropic Error: {str(e)}")
            return f"Error: {str(e)}"

    def _call_gemini(self, system_message, user_message):
        if not self.api_key:
            return "Error: Gemini API Key not set"
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            data = {
                "contents": [{
                    "parts": [{"text": f"{system_message}\n\n{user_message}"}]
                }]
            }
            response = requests.post(url, json=data)
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            self.logger.error(f"Gemini Error: {str(e)}")
            return f"Error: {str(e)}"

class LLMVulnerabilityReportGenerator(LLMBaseGenerator):
    def get_vulnerability_description(self, description):
        self.logger.info(f"Generating Vulnerability Description for: {description}")
        response_content = self._call_llm(VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE, description)
        
        if response_content.startswith("Error:"):
            return {'status': False, 'error': response_content}

        response = parse_llm_vulnerability_report(response_content)
        if not response:
            return {'status': False, 'error': 'Failed to parse LLM response'}

        return {
            'status': True,
            'description': response.get('description', ''),
            'impact': response.get('impact', ''),
            'remediation': response.get('remediation', ''),
            'references': response.get('references', []),
        }

class LLMAttackSuggestionGenerator(LLMBaseGenerator):
    def get_attack_suggestion(self, user_input):
        self.logger.info(f"Generating Attack Suggestion for: {user_input}")
        response_content = self._call_llm(ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT, user_input)
        
        if response_content.startswith("Error:"):
            return {'status': False, 'error': response_content, 'input': user_input}
            
        return {
            'status': True,
            'description': response_content,
            'input': user_input
        }

class LLMReportGenerator(LLMBaseGenerator):
    def _generate_section(self, system_prompt, context):
        return self._call_llm(system_prompt, context)

    def generate_overview(self, context):
        from reNgine.definitions import LLM_REPORT_OVERVIEW_SYSTEM_PROMPT
        return self._generate_section(LLM_REPORT_OVERVIEW_SYSTEM_PROMPT, context)

    def generate_executive_brief(self, context):
        from reNgine.definitions import LLM_REPORT_EXECUTIVE_BRIEF_SYSTEM_PROMPT
        return self._generate_section(LLM_REPORT_EXECUTIVE_BRIEF_SYSTEM_PROMPT, context)

    def generate_conclusion(self, context):
        from reNgine.definitions import LLM_REPORT_CONCLUSION_SYSTEM_PROMPT
        return self._generate_section(LLM_REPORT_CONCLUSION_SYSTEM_PROMPT, context)
		