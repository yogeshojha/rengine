// placeholders mirror shared/definitions/api_reference.py

export const EXAMPLE_BASE_URL = 'https://rengine.example.com';
export const EXAMPLE_KEY_VARIABLE = 'RENGINE_KEY';
export const PROJECT_VARIABLE = '$PROJECT_ID';

export const METHOD_TONE: Readonly<Record<string, string>> = {
	GET: 'text-info',
	POST: 'text-success',
	DELETE: 'text-destructive'
};
