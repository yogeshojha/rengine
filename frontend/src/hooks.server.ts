import type { Handle } from '@sveltejs/kit';
import { createInitialModeExpression } from 'mode-watcher';

const MODE_SLOT = '%mode.init%';
const MODE_INIT = createInitialModeExpression();

export const handle: Handle = ({ event, resolve }) =>
	resolve(event, { transformPageChunk: ({ html }) => html.replace(MODE_SLOT, () => MODE_INIT) });
