import { wordlistsApi } from '$lib/api/wordlists';
import type { Wordlist, WordlistUpload, WordlistUploadResult } from '$lib/types/wordlist';
import { toast } from 'svelte-sonner';

function createWordlistsStore() {
	let wordlists = $state<Wordlist[]>([]);
	let isLoading = $state(false);
	let hasFetched = $state(false);
	let error = $state<string | null>(null);

	return {
		get wordlists() {
			return wordlists;
		},
		get isLoading() {
			return isLoading;
		},
		get hasFetched() {
			return hasFetched;
		},
		get error() {
			return error;
		},

		byKind(kind: string): Wordlist[] {
			return wordlists.filter((w) => w.kind === kind);
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			try {
				wordlists = await wordlistsApi.list();
				hasFetched = true;
				error = null;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Wordlists not loaded';
			} finally {
				isLoading = false;
			}
		},

		async upload(body: WordlistUpload): Promise<WordlistUploadResult | null> {
			try {
				const result = await wordlistsApi.upload(body);
				if (result.stored.length) {
					await this.fetch(true);
					if (error) toast.error('Wordlists not refreshed');
				}
				return result;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Wordlists not uploaded');
				return null;
			}
		},

		async remove(id: string): Promise<boolean> {
			try {
				await wordlistsApi.remove(id);
				wordlists = wordlists.filter((w) => w.id !== id);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Wordlist not deleted');
				return false;
			}
		},

		reset() {
			wordlists = [];
			isLoading = false;
			hasFetched = false;
			error = null;
		}
	};
}

export const wordlists = createWordlistsStore();
