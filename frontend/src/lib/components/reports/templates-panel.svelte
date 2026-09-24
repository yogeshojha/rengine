<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import * as Card from '$lib/components/ui/card';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import TemplateRow from './template-row.svelte';
	import { TEMPLATE_COLUMNS } from './template-columns';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
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

	const TABS = [
		{ key: 'all', label: 'All' },
		{ key: 'default', label: 'Default' },
		{ key: 'custom', label: 'Custom' }
	];

	let tab = $state('all');
	let search = $state('');
	let audiences = $state<string[]>([]);
	let scopes = $state<string[]>([]);

	const counts = $derived({
		all: templates.length,
		default: templates.filter((t) => t.is_builtin).length,
		custom: templates.filter((t) => !t.is_builtin).length
	});

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
				(tab === 'all' || t.is_builtin === (tab === 'default')) &&
				(!audiences.length || audiences.includes(t.narrative.audience)) &&
				(!scopes.length || scopes.includes(t.scope)) &&
				(!q || `${t.name} ${t.description}`.toLowerCase().includes(q))
		);
	});

	const filtered = $derived(Boolean(search || audiences.length || scopes.length));

	function toggle(list: string[], key: string): string[] {
		return list.includes(key) ? list.filter((k) => k !== key) : [...list, key];
	}

	function clear() {
		search = '';
		audiences = [];
		scopes = [];
	}
</script>

{#snippet filter(
	label: string,
	options: { key: string; label: string; count: number }[],
	selected: string[],
	set: (next: string[]) => void
)}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					class="h-9 gap-1.5 {selected.length ? 'border-primary/50 bg-primary/5' : ''}"
				>
					{label}
					{#if selected.length}
						<span class="text-xs text-muted-foreground tabular-nums">{selected.length}</span>
					{/if}
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-48">
			{#each options as o (o.key)}
				<DropdownMenu.CheckboxItem
					checked={selected.includes(o.key)}
					onCheckedChange={() => set(toggle(selected, o.key))}
				>
					<span class="flex-1 truncate">{o.label}</span>
					<span class="font-mono text-2xs text-muted-foreground">{o.count}</span>
				</DropdownMenu.CheckboxItem>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/snippet}

<Card.Root class="gap-0 py-0">
	<div class="border-b px-2">
		<CountTabs tabs={TABS} value={tab} {counts} onChange={(k) => (tab = k)} />
	</div>

	<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
		<div
			class="flex h-9 min-w-[240px] flex-1 items-center gap-2 rounded-md border bg-background px-2.5 focus-within:ring-2 focus-within:ring-ring/50"
		>
			<Search class="size-4 shrink-0 text-muted-foreground" />
			<input
				class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
				placeholder="Search templates"
				bind:value={search}
				aria-label="Search templates"
			/>
			{#if search}
				<button
					type="button"
					class="rounded text-muted-foreground hover:text-foreground"
					aria-label="Clear search"
					onclick={() => (search = '')}><X class="size-3.5" /></button
				>
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-2">
			{#if audienceOptions.length > 1}
				{@render filter('Audience', audienceOptions, audiences, (v) => (audiences = v))}
			{/if}
			{#if scopeOptions.length > 1}
				{@render filter('Scope', scopeOptions, scopes, (v) => (scopes = v))}
			{/if}
		</div>
	</div>

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
		<div class="p-6">
			<EmptyState icon={FileTextIcon} title="No matching templates">
				{#if filtered}
					<Button variant="outline" size="sm" onclick={clear}>Clear filters</Button>
				{/if}
			</EmptyState>
		</div>
	{/if}
</Card.Root>
