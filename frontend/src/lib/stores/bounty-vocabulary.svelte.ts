import { bountyProgramsApi } from '$lib/api/bounty-programs';
import type { BountyVocabulary, PlatformSpec } from '$lib/types/bounty-program';

class BountyVocabularyStore {
	vocabulary = $state<BountyVocabulary | null>(null);
	loading = $state(false);
	error = $state<string | null>(null);
	private fetched = false;

	get platforms(): PlatformSpec[] {
		return this.vocabulary?.platforms ?? [];
	}

	platform(key: string): PlatformSpec | undefined {
		return this.vocabulary?.platforms.find((p) => p.key === key);
	}

	label(key: string): string {
		return this.platform(key)?.label ?? key;
	}

	url(key: string): string {
		return this.platform(key)?.url ?? '';
	}

	async load(): Promise<void> {
		if (this.fetched || this.loading) return;
		this.loading = true;
		try {
			this.vocabulary = await bountyProgramsApi.vocabulary();
			this.fetched = true;
			this.error = null;
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Bounty vocabulary not loaded';
		} finally {
			this.loading = false;
		}
	}

	reset(): void {
		this.vocabulary = null;
		this.fetched = false;
		this.error = null;
	}
}

export const bountyVocabulary = new BountyVocabularyStore();
