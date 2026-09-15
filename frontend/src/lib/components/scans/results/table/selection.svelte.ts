import { SvelteMap } from 'svelte/reactivity';

interface Row {
	id: string;
}

/** Selection state, independent of the current page. */
export class RowSelection<T extends Row> {
	private picked = new SvelteMap<string, T>();

	readonly size = $derived(this.picked.size);

	has(id: string): boolean {
		return this.picked.has(id);
	}

	rows(): T[] {
		return [...this.picked.values()];
	}

	ids(): string[] {
		return [...this.picked.keys()];
	}

	countOn(items: T[]): number {
		return items.reduce((n, item) => n + (this.picked.has(item.id) ? 1 : 0), 0);
	}

	allOn(items: T[]): boolean {
		return items.length > 0 && this.countOn(items) === items.length;
	}

	toggle(item: T): void {
		if (this.picked.has(item.id)) this.picked.delete(item.id);
		else this.picked.set(item.id, item);
	}

	toggleAll(items: T[]): void {
		if (this.allOn(items)) for (const item of items) this.picked.delete(item.id);
		else for (const item of items) this.picked.set(item.id, item);
	}

	clear(): void {
		this.picked.clear();
	}
}
