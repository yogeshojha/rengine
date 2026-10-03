import { describe, expect, it } from 'vitest';
import { CONTEXT_NOUN, credentialLaunchRefusal, launchLocked } from './launch';

const owner = { id: 'owner', is_superuser: false };
const member = { id: 'member', is_superuser: false };
const admin = { id: 'admin', is_superuser: true };

describe('launchLocked', () => {
	const held = { carries_credentials: true, created_by: 'owner' };

	it('locks a context with credentials for another member', () => {
		expect(launchLocked(held, member)).toBe(true);
		expect(launchLocked(held, null)).toBe(true);
	});

	it('leaves it open to its creator and an administrator', () => {
		expect(launchLocked(held, owner)).toBe(false);
		expect(launchLocked(held, admin)).toBe(false);
	});

	it('never locks a context without credentials', () => {
		expect(launchLocked({ carries_credentials: false, created_by: 'owner' }, member)).toBe(false);
	});

	it('names the context in the refusal the api sends', () => {
		expect(credentialLaunchRefusal(CONTEXT_NOUN, 'prod')).toBe(
			'Context prod carries credentials. Its creator or an administrator can launch with it.'
		);
	});
});
