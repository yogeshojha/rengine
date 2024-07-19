
import openai
import re
from reNgine.common_func import get_open_ai_key, parse_llm_vulnerability_report
from reNgine.definitions import VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE, ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT, OLLAMA_INSTANCE
from langchain_community.llms import Ollama

from dashboard.models import OllamaSettings


class LLMVulnerabilityReportGenerator:

	def __init__(self, logger):
		selected_model = OllamaSettings.objects.first()
		self.model_name = selected_model.selected_model if selected_model else 'gpt-3.5-turbo'
		self.use_ollama = selected_model.use_ollama if selected_model else False
		self.openai_api_key = None
		self.logger = logger
	
	def get_vulnerability_description(self, description):
		"""Generate Vulnerability Description using GPT.

		Args:
			description (str): Vulnerability Description message to pass to GPT.

		Returns:
			(dict) of {
				'description': (str)
				'impact': (str),
				'remediation': (str),
				'references': (list) of urls
			}
		"""
		self.logger.info(f"Generating Vulnerability Description for: {description}")
		if self.use_ollama:
			prompt = VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE + "\nUser: " + description
			prompt = re.sub(r'\t', '', prompt)
			self.logger.info(f"Using Ollama for Vulnerability Description Generation")
			llm = Ollama(
				base_url=OLLAMA_INSTANCE, 
				model=self.model_name
			)
			response_content = llm.invoke(prompt)
			# self.logger.info(response_content)
		else:
			self.logger.info(f'Using OpenAI API for Vulnerability Description Generation')
			openai_api_key = get_open_ai_key()
			if not openai_api_key:
				return {
					'status': False,
					'error': 'OpenAI API Key not set'
				}
			try:
				prompt = re.sub(r'\t', '', VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE)
				openai.api_key = openai_api_key
				gpt_response = openai.ChatCompletion.create(
				model=self.model_name,
				messages=[
						{'role': 'system', 'content': prompt},
						{'role': 'user', 'content': description}
					]
				)

				response_content = gpt_response['choices'][0]['message']['content']
			except Exception as e:
				return {
					'status': False,
					'error': str(e)
				}
			
		response = parse_llm_vulnerability_report(response_content)

		if not response:
			return {
				'status': False,
				'error': 'Failed to parse LLM response'
			}

		return {
			'status': True,
			'description': response.get('description', ''),
			'impact': response.get('impact', ''),
			'remediation': response.get('remediation', ''),
			'references': response.get('references', []),
		}


class LLMAttackSuggestionGenerator:

	def __init__(self, logger):
		selected_model = OllamaSettings.objects.first()
		self.model_name = selected_model.selected_model if selected_model else 'gpt-3.5-turbo'
		self.use_ollama = selected_model.use_ollama if selected_model else False
		self.openai_api_key = None
		self.logger = logger

	def get_attack_suggestion(self, user_input):
		'''
			user_input (str): input for gpt
		'''
		if self.use_ollama:
			self.logger.info(f"Using Ollama for Attack Suggestion Generation")
			prompt = ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT + "\nUser: " + user_input	
			prompt = re.sub(r'\t', '', prompt)
			llm = Ollama(
				base_url=OLLAMA_INSTANCE, 
				model=self.model_name
			)
			response_content = llm.invoke(prompt)
			self.logger.info(response_content)
		else:
			self.logger.info(f'Using OpenAI API for Attack Suggestion Generation')
			openai_api_key = get_open_ai_key()
			if not openai_api_key:
				return {
					'status': False,
					'error': 'OpenAI API Key not set'
				}
			try:
				prompt = re.sub(r'\t', '', ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT)
				openai.api_key = openai_api_key
				gpt_response = openai.ChatCompletion.create(
				model=self.model_name,
				messages=[
						{'role': 'system', 'content': prompt},
						{'role': 'user', 'content': user_input}
					]
				)
				response_content = gpt_response['choices'][0]['message']['content']
			except Exception as e:
				return {
					'status': False,
					'error': str(e),
					'input': user_input
				}
		return {
			'status': True,
			'description': response_content,
			'input': user_input
		}
		