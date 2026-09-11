import { SvelteMap } from 'svelte/reactivity';
import type { SeedPick } from '$lib/types/recheck';

interface Row {
	id: string;
}

/** Selection state, independent of the current page. */
export class RowSelection<T extends Row> {
	private picked = new SvelteMap<string, SeedPick>();

	readonly size = $derived(this.picked.size);

	has(id: string): boolean {
		return this.picked.has(id);
	}

	picks(): SeedPick[] {
		return [...this.picked.values()];
	}

	values(): string[] {
		return this.picks().map((p) => p.value);
	}

	countOn(items: T[]): number {
		return items.reduce((n, item) => n + (this.picked.has(item.id) ? 1 : 0), 0);
	}

	allOn(items: T[]): boolean {
		return items.length > 0 && this.countOn(items) === items.length;
	}

	toggle(item: T, pick: SeedPick): void {
		if (this.picked.has(item.id)) this.picked.delete(item.id);
		else this.picked.set(item.id, pick);
	}

	toggleAll(items: T[], pick: (item: T) => SeedPick): void {
		if (this.allOn(items)) for (const item of items) this.picked.delete(item.id);
		else for (const item of items) this.picked.set(item.id, pick(item));
	}

	clear(): void {
		this.picked.clear();
	}
}
