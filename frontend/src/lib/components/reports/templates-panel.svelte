<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import LibraryToolbar from './library-toolbar.svelte';
	import FacetFilter from './facet-filter.svelte';
	import LibraryEmpty from './library-empty.svelte';
	import TemplateRow from './template-row.svelte';
	import { TEMPLATE_COLUMNS } from './template-columns';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { LibraryTab, inLibraryTab, libraryCounts } from '$lib/config/reports';
	import type { ReportTemplate } from '$lib/types/report';

	let {
		templates,
		onDuplicate,
		onDelete,
		onGenerate
	}: {
		templates: ReportTemplate[];
		onDuplicate: (t: ReportTemplate) => void;
		onDelete: (t: ReportTemplate) => void;
		onGenerate: (t: ReportTemplate) => void;
	} = $props();

	let tab = $state<string>(LibraryTab.ALL);
	let search = $state('');
	let audiences = $state<string[]>([]);
	let scopes = $state<string[]>([]);

	const counts = $derived(libraryCounts(templates.map((t) => t.is_builtin)));

	function facet(key: (t: ReportTemplate) => string, options: { key: string; label: string }[]) {
		return options
			.map((o) => ({ ...o, count: templates.filter((t) => key(t) === o.key).length }))
			.filter((o) => o.count);
	}

	const audienceOptions = $derived(
		facet((t) => t.narrative.audience, reportCatalog.catalog?.audiences ?? [])
	);
	const scopeOptions = $derived(facet((t) => t.scope, reportCatalog.catalog?.scopes ?? []));

	const visible = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return templates.filter(
			(t) =>
				inLibraryTab(tab, t.is_builtin) &&
				(!audiences.length || audiences.includes(t.narrative.audience)) &&
				(!scopes.length || scopes.includes(t.scope)) &&
				(!q || `${t.name} ${t.description}`.toLowerCase().includes(q))
		);
	});

	const filtered = $derived(Boolean(search || audiences.length || scopes.length));

	function clear() {
		search = '';
		audiences = [];
		scopes = [];
	}
</script>

<Card.Root class="gap-0 py-0">
	<LibraryToolbar bind:tab bind:search {counts} placeholder="Search templates">
		<FacetFilter label="Audience" options={audienceOptions} bind:selected={audiences} />
		<FacetFilter label="Scope" options={scopeOptions} bind:selected={scopes} />
	</LibraryToolbar>

	{#if visible.length}
		<div
			class="hidden gap-4 border-b bg-muted/30 px-4 py-2 text-2xs font-medium text-muted-foreground uppercase lg:grid {TEMPLATE_COLUMNS}"
		>
			<span></span>
			<span>Template</span>
			<span>Sections</span>
			<span>Audience</span>
			<span>Scope</span>
			<span>Formats</span>
			<span class="text-right">Used</span>
			<span></span>
		</div>
		{#each visible as template (template.id)}
			<TemplateRow {template} {onDuplicate} {onDelete} {onGenerate} />
		{/each}
	{:else}
		<LibraryEmpty title="No matching templates" onClear={filtered ? clear : undefined} />
	{/if}
</Card.Root>
