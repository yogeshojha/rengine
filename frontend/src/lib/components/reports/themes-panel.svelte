<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import LibraryToolbar from './library-toolbar.svelte';
	import LibraryEmpty from './library-empty.svelte';
	import ThemeCard from './theme-card.svelte';
	import { LibraryOrigin, LibraryTab, inLibraryTab, libraryCounts } from '$lib/config/reports';
	import type { ThemeSummary } from '$lib/types/report';

	let { themes, onDelete }: { themes: ThemeSummary[]; onDelete: (theme: ThemeSummary) => void } =
		$props();

	let tab = $state<string>(LibraryTab.ALL);
	let search = $state('');

	const builtin = (t: ThemeSummary) => t.origin === LibraryOrigin.BUILTIN;
	const counts = $derived(libraryCounts(themes.map(builtin)));
	const visible = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return themes.filter(
			(t) =>
				inLibraryTab(tab, builtin(t)) &&
				(!q || `${t.name} ${t.description} ${t.author}`.toLowerCase().includes(q))
		);
	});
</script>

<Card.Root class="gap-0 py-0">
	<LibraryToolbar bind:tab bind:search {counts} placeholder="Search themes" />

	{#if visible.length}
		<div class="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
			{#each visible as theme (theme.slug)}
				<ThemeCard {theme} onDelete={() => onDelete(theme)} />
			{/each}
		</div>
	{:else}
		<LibraryEmpty title="No matching themes" onClear={search ? () => (search = '') : undefined} />
	{/if}
</Card.Root>
