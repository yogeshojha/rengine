import type { AuthType } from '$lib/types/scan-context';

export const AUTH_TYPE_LABELS: Record<AuthType, string> = {
	none: 'None',
	bearer: 'Bearer token',
	basic: 'Basic auth',
	header: 'Custom header',
	cookie: 'Cookie',
	api_key: 'API key'
};

export const NO_AUTH_LABEL = 'No auth';
