import { interestApi } from '$lib/api/interest';
import type { InterestCatalog, InterestKindEntry } from '$lib/types/interest';

class InterestCatalogStore {
	catalog = $state<InterestCatalog | null>(null);
	loading = $state(false);
	error = $state<string | null>(null);
	private fetched = false;

	get kinds(): InterestKindEntry[] {
		return this.catalog?.kinds ?? [];
	}

	kind(key: string): InterestKindEntry | undefined {
		return this.catalog?.kinds.find((k) => k.key === key);
	}

	label(key: string): string {
		return this.kind(key)?.label ?? key.replace(/_/g, ' ');
	}

	tone(key: string): string {
		return this.kind(key)?.tone ?? 'neutral';
	}

	sourceLabel(key: string): string {
		return this.catalog?.sources.find((s) => s.key === key)?.label ?? key;
	}

	bandLabel(key: string): string {
		return this.catalog?.bands.find((b) => b.key === key)?.label ?? key;
	}

	async load(): Promise<void> {
		if (this.fetched || this.loading) return;
		this.loading = true;
		try {
			this.catalog = await interestApi.catalog();
			this.fetched = true;
			this.error = null;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Could not load the interest catalog';
		} finally {
			this.loading = false;
		}
	}

	reset(): void {
		this.catalog = null;
		this.fetched = false;
		this.error = null;
	}
}

export const interestCatalog = new InterestCatalogStore();
