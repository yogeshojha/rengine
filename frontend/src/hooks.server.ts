import type { Handle } from '@sveltejs/kit';
import { createInitialModeExpression } from 'mode-watcher';

const MODE_SLOT = '%mode.init%';
const MODE_INIT = createInitialModeExpression();

const SECURITY_HEADERS: Record<string, string> = {
	'X-Content-Type-Options': 'nosniff',
	'Referrer-Policy': 'same-origin',
	'X-Frame-Options': 'DENY'
};

export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event, {
		transformPageChunk: ({ html }) => html.replace(MODE_SLOT, () => MODE_INIT)
	});
	for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
		if (!response.headers.has(name)) response.headers.set(name, value);
	}
	return response;
};
