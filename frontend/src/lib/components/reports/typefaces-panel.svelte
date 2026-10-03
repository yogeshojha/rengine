<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import LibraryToolbar from './library-toolbar.svelte';
	import FacetFilter from './facet-filter.svelte';
	import LibraryEmpty from './library-empty.svelte';
	import FontRow from './font-row.svelte';
	import { TYPEFACE_COLUMNS } from './typeface-columns';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { LibraryOrigin, LibraryTab, inLibraryTab, libraryCounts } from '$lib/config/reports';
	import type { ReportFont } from '$lib/types/report';

	let { fonts, onDelete }: { fonts: ReportFont[]; onDelete: (font: ReportFont) => void } = $props();

	let tab = $state<string>(LibraryTab.ALL);
	let search = $state('');
	let roles = $state<string[]>([]);

	const builtin = (f: ReportFont) => f.origin === LibraryOrigin.BUILTIN;
	const counts = $derived(libraryCounts(fonts.map(builtin)));
	const roleOptions = $derived(
		(reportCatalog.catalog?.font_roles ?? [])
			.map((r) => ({ ...r, count: fonts.filter((f) => f.role === r.key).length }))
			.filter((r) => r.count)
	);
	const visible = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return fonts.filter(
			(f) =>
				inLibraryTab(tab, builtin(f)) &&
				(!roles.length || roles.includes(f.role)) &&
				(!q || `${f.name} ${f.slug} ${f.note}`.toLowerCase().includes(q))
		);
	});
	const filtered = $derived(Boolean(search || roles.length));

	function clear() {
		search = '';
		roles = [];
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<LibraryToolbar bind:tab bind:search {counts} placeholder="Search typefaces">
		<FacetFilter label="Role" options={roleOptions} bind:selected={roles} />
	</LibraryToolbar>

	{#if visible.length}
		<div
			class="hidden gap-4 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase lg:grid {TYPEFACE_COLUMNS}"
		>
			<span>Typeface</span>
			<span>Role</span>
			<span>Weights</span>
			<span class="text-right">Faces</span>
			<span class="text-right">Size</span>
			<span>Note</span>
			<span></span>
		</div>
		{#each visible as font (font.slug)}
			<FontRow {font} onDelete={() => onDelete(font)} />
		{/each}
	{:else}
		<LibraryEmpty title="No matching typefaces" onClear={filtered ? clear : undefined} />
	{/if}
</Card.Root>
