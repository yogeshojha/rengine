import { describe, expect, it, vi } from 'vitest';
import { DiscardGuard } from './discard-guard.svelte';

describe('DiscardGuard', () => {
	it('closes a clean form', () => {
		const close = vi.fn();
		const guard = new DiscardGuard(() => false, close);
		guard.close();
		expect(close).toHaveBeenCalledTimes(1);
		expect(guard.asking).toBe(false);
	});

	it('asks before closing a dirty form', () => {
		const close = vi.fn();
		const guard = new DiscardGuard(() => true, close);
		guard.close();
		expect(close).not.toHaveBeenCalled();
		expect(guard.asking).toBe(true);
	});

	it('closes once the discard is confirmed', () => {
		const close = vi.fn();
		const guard = new DiscardGuard(() => true, close);
		guard.close();
		guard.discard();
		expect(close).toHaveBeenCalledTimes(1);
		expect(guard.asking).toBe(false);
	});

	it('reads the dirty state at close time', () => {
		let dirty = true;
		const close = vi.fn();
		const guard = new DiscardGuard(() => dirty, close);
		dirty = false;
		guard.close();
		expect(close).toHaveBeenCalledTimes(1);
	});
});
