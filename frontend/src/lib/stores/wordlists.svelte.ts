import { wordlistsApi } from '$lib/api/wordlists';
import type { Wordlist, WordlistUpload, WordlistUploadResult } from '$lib/types/wordlist';
import { toast } from 'svelte-sonner';

function createWordlistsStore() {
	let wordlists = $state<Wordlist[]>([]);
	let isLoading = $state(false);
	let hasFetched = $state(false);

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

		byKind(kind: string): Wordlist[] {
			return wordlists.filter((w) => w.kind === kind);
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			try {
				wordlists = await wordlistsApi.list();
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Wordlists could not be loaded');
			} finally {
				isLoading = false;
			}
		},

		async upload(body: WordlistUpload): Promise<WordlistUploadResult | null> {
			try {
				const result = await wordlistsApi.upload(body);
				if (result.stored.length) await this.fetch(true);
				return result;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Upload failed');
				return null;
			}
		},

		async remove(id: string): Promise<boolean> {
			try {
				await wordlistsApi.remove(id);
				wordlists = wordlists.filter((w) => w.id !== id);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Wordlist could not be deleted');
				return false;
			}
		},

		reset() {
			wordlists = [];
			isLoading = false;
			hasFetched = false;
		}
	};
}

export const wordlists = createWordlistsStore();
