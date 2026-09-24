<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import OriginBadge from './origin-badge.svelte';
	import { TYPEFACE_COLUMNS } from './typeface-columns';
	import { LibraryOrigin, formatBytes } from '$lib/config/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import type { ReportFont } from '$lib/types/report';

	let { font, onDelete }: { font: ReportFont; onDelete: (slug: string) => void } = $props();

	const roleLabel = $derived(
		reportCatalog.catalog?.font_roles.find((r) => r.key === font.role)?.label ?? font.role
	);
</script>

{#snippet cell(label: string)}
	<span class="text-2xs text-muted-foreground lg:hidden">{label}</span>
{/snippet}

<div
	class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 border-b px-4 py-3 last:border-b-0 {TYPEFACE_COLUMNS}"
>
	<div class="min-w-0">
		<div class="flex items-center gap-2">
			<span class="truncate text-sm font-medium">{font.name}</span>
			<OriginBadge builtin={font.origin === LibraryOrigin.BUILTIN} />
		</div>
		<span class="font-mono text-2xs text-muted-foreground">{font.slug}</span>
	</div>

	<div class="col-span-2 row-start-2 flex flex-wrap gap-x-5 gap-y-1 text-xs lg:contents lg:text-sm">
		<div class="flex flex-col">
			{@render cell('Role')}
			<span>{roleLabel}</span>
		</div>
		<div class="flex flex-col">
			{@render cell('Weights')}
			<span class="font-mono text-xs text-muted-foreground tabular-nums">
				{font.weights.length ? font.weights.join(', ') : '—'}
			</span>
		</div>
		<div class="flex flex-col lg:items-end">
			{@render cell('Faces')}
			<span class="font-mono text-xs tabular-nums">{font.faces.length || '—'}</span>
		</div>
		<div class="flex flex-col lg:items-end">
			{@render cell('Size')}
			<span class="font-mono text-xs text-muted-foreground tabular-nums">
				{font.bytes ? formatBytes(font.bytes) : '—'}
			</span>
		</div>
		<div class="flex min-w-0 flex-col">
			{@render cell('Note')}
			<span class="text-xs text-muted-foreground">{font.note || '—'}</span>
		</div>
	</div>

	<div class="col-start-2 row-start-1 flex justify-end lg:col-start-auto lg:row-start-auto">
		{#if font.origin === LibraryOrigin.CUSTOM}
			<Button
				variant="ghost"
				size="icon"
				class="size-8 text-muted-foreground hover:text-destructive"
				onclick={() => onDelete(font.slug)}
				aria-label="Delete {font.name}"
			>
				<Trash2Icon class="size-3.5" />
			</Button>
		{/if}
	</div>
</div>
