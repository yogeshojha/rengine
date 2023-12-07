import openai
import re
import os
from reNgine.common_func import get_open_ai_key, extract_between
from reNgine.definitions import VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE, ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT

#sets custom api base url if provided in .env to enable users to use their own openai instance
custom_api_base_url = os.getenv('OPENAI_API_BASE_URL')
if custom_api_base_url:
    openai.api_base = custom_api_base_url

class GPTVulnerabilityReportGenerator:

	def __init__(self):
		self.api_key = get_open_ai_key()
		self.model_name = 'gpt-3.5-turbo'

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
		if not self.api_key:
			return {
				'status': False,
				'error': 'No OpenAI keys provided.'
			}
		openai.api_key = self.api_key
		try:
			gpt_response = openai.ChatCompletion.create(
			model=self.model_name,
			messages=[
					{'role': 'system', 'content': VULNERABILITY_DESCRIPTION_SYSTEM_MESSAGE},
					{'role': 'user', 'content': description}
				]
			)

			response_content = gpt_response['choices'][0]['message']['content']

			vuln_description_pattern = re.compile(
				r"[Vv]ulnerability [Dd]escription:(.*?)(?:\n\n[Ii]mpact:|$)",
				re.DOTALL
			)
			impact_pattern = re.compile(
				r"[Ii]mpact:(.*?)(?:\n\n[Rr]emediation:|$)",
				re.DOTALL
			)
			remediation_pattern = re.compile(
				r"[Rr]emediation:(.*?)(?:\n\n[Rr]eferences:|$)",
				re.DOTALL
			)

			description_section = extract_between(response_content, vuln_description_pattern)
			impact_section = extract_between(response_content, impact_pattern)
			remediation_section = extract_between(response_content, remediation_pattern)
			references_start_index = response_content.find("References:")
			references_section = response_content[references_start_index + len("References:"):].strip()

			url_pattern = re.compile(r'https://\S+')
			urls = url_pattern.findall(references_section)

			return {
				'status': True,
				'description': description_section,
				'impact': impact_section,
				'remediation': remediation_section,
				'references': urls,
			}
		except Exception as e:
			return {
				'status': False,
				'error': str(e)
			}


class GPTAttackSuggestionGenerator:

	def __init__(self):
		self.api_key = get_open_ai_key()
		self.model_name = 'gpt-3.5-turbo'

	def get_attack_suggestion(self, input):
		'''
			input (str): input for gpt
		'''
		if not self.api_key:
			return {
				'status': False,
				'error': 'No OpenAI keys provided.',
				'input': input
			}
		openai.api_key = self.api_key
		print(input)
		try:
			gpt_response = openai.ChatCompletion.create(
			model=self.model_name,
			messages=[
					{'role': 'system', 'content': ATTACK_SUGGESTION_GPT_SYSTEM_PROMPT},
					{'role': 'user', 'content': input}
				]
			)
			response_content = gpt_response['choices'][0]['message']['content']
			return {
				'status': True,
				'description': response_content,
				'input': input
			}
		except Exception as e:
			return {
				'status': False,
				'error': str(e),
				'input': input
			}
