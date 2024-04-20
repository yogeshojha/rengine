from reNgine.definitions import OLLAMA_INSTANCE
from ollama import Client

class CustomOllamaClient:

	def __init__(self, ):
		self.instance_url = OLLAMA_INSTANCE
		self.client = None

	def connect(self):
		try:
			self.client = Client(
				host=self.instance_url
			)
			return {
				'status': True
			}
		except Exception as e:
			return {
				'status': False,
				'error': str(e)
			}
		
	def list_models(self,):
		return self.client.list()
	
	def pull_model(self, model_name):
		return self.client.pull(model_name)