import { describe, expect, it } from 'vitest';
import { errorMessage } from './errors';

describe('errorMessage', () => {
	it('takes the message of an Error', () => {
		expect(errorMessage(new Error('Scan not found'), 'Scan not loaded')).toBe('Scan not found');
	});

	it('falls back for anything else', () => {
		expect(errorMessage('boom', 'Scan not loaded')).toBe('Scan not loaded');
		expect(errorMessage(undefined, 'Scan not loaded')).toBe('Scan not loaded');
	});
});
