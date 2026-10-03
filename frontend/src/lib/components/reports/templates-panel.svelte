<script lang="ts">
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LibraryToolbar from './library-toolbar.svelte';
	import FacetFilter from './facet-filter.svelte';
	import LibraryEmpty from './library-empty.svelte';
	import TemplateRow from './template-row.svelte';
	import { TEMPLATE_COLUMNS } from './template-columns';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { LibraryTab, inLibraryTab, libraryCounts } from '$lib/config/reports';
	import type { ReportTemplate } from '$lib/types/report';

	const SKELETON_ROWS = 4;
	const NAME = ['w-40', 'w-32', 'w-48', 'w-36'];

	let {
		templates,
		loading = false,
		error = null,
		onRetry,
		onDuplicate,
		onDelete,
		onGenerate
	}: {
		templates: ReportTemplate[];
		loading?: boolean;
		error?: string | null;
		onRetry?: () => void;
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

{#snippet header()}
	<div
		class="hidden gap-4 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase lg:grid {TEMPLATE_COLUMNS}"
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
{/snippet}

<Card.Root class="gap-0 overflow-hidden py-0">
	<LibraryToolbar bind:tab bind:search {counts} placeholder="Search templates">
		<FacetFilter label="Audience" options={audienceOptions} bind:selected={audiences} />
		<FacetFilter label="Scope" options={scopeOptions} bind:selected={scopes} />
	</LibraryToolbar>

	{#if visible.length}
		{@render header()}
		{#each visible as template (template.id)}
			<TemplateRow {template} {onDuplicate} {onDelete} {onGenerate} />
		{/each}
	{:else if loading && !templates.length}
		<div aria-busy="true">
			{@render header()}
			{#each { length: SKELETON_ROWS } as _, i (i)}
				<div
					class="grid grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 border-b px-4 py-3 last:border-b-0 {TEMPLATE_COLUMNS}"
				>
					<Skeleton
						class="row-span-2 aspect-[1/1.414] w-full self-start rounded-sm lg:row-span-1"
					/>
					<div class="flex min-w-0 flex-col gap-1.5">
						<Skeleton class="h-4 max-w-full {NAME[i % NAME.length]}" />
						<Skeleton class="h-3 w-56 max-w-full" />
					</div>
					<div class="hidden items-center gap-1 lg:flex">
						<Skeleton class="h-5 w-20 rounded-md" />
						<Skeleton class="h-5 w-16 rounded-md" />
					</div>
					<div
						class="col-span-2 col-start-2 flex flex-wrap items-center gap-x-4 gap-y-1 lg:contents"
					>
						<Skeleton class="h-4 w-16" />
						<Skeleton class="h-4 w-12" />
						<Skeleton class="h-5 w-24 rounded-md" />
						<Skeleton class="h-4 w-6 lg:justify-self-end" />
					</div>
					<div
						class="col-start-3 row-start-1 flex items-center justify-end gap-1 lg:col-start-auto lg:row-start-auto"
					>
						<Skeleton class="h-8 w-24 rounded-md" />
						<Skeleton class="size-7 rounded-md" />
					</div>
				</div>
			{/each}
		</div>
	{:else if error && !templates.length}
		<div class="p-6">
			<EmptyState icon={TriangleAlertIcon} title="Templates not loaded" description={error} compact>
				{#if onRetry}
					<Button variant="outline" size="sm" onclick={() => onRetry()}>Retry</Button>
				{/if}
			</EmptyState>
		</div>
	{:else}
		<LibraryEmpty title="No matching templates" onClear={filtered ? clear : undefined} />
	{/if}
</Card.Root>
