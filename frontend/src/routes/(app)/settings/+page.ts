import { redirect } from '@sveltejs/kit';
import { ROUTES } from '$lib/config/routes';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
	redirect(307, ROUTES.settings('general'));
};
