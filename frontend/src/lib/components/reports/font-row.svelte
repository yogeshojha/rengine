<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import { formatBytes } from '$lib/config/reports';
	import type { ReportFont } from '$lib/types/report';

	let { font, onDelete }: { font: ReportFont; onDelete: (slug: string) => void } = $props();

	const ROLE_LABEL: Record<string, string> = {
		sans: 'Sans',
		serif: 'Serif',
		mono: 'Monospaced'
	};
</script>

<div class="flex items-center gap-3 border-b px-4 py-3 last:border-b-0">
	<div class="min-w-0 flex-1">
		<div class="flex flex-wrap items-center gap-2">
			<span class="truncate font-medium">{font.name}</span>
			<Badge variant="outline" class="text-[10px]">{ROLE_LABEL[font.role] ?? font.role}</Badge>
			{#if font.origin === 'custom'}<Badge variant="secondary" class="text-[10px]">Yours</Badge
				>{/if}
		</div>
		<div class="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
			<span class="font-mono">{font.slug}</span>
			{#if font.weights.length}
				<span>{font.weights.join(', ')}</span>
			{/if}
			{#if font.faces.length}
				<span>{font.faces.length} {font.faces.length === 1 ? 'face' : 'faces'}</span>
			{/if}
			{#if font.bytes}<span>{formatBytes(font.bytes)}</span>{/if}
			{#if font.note}<span>{font.note}</span>{/if}
		</div>
	</div>
	{#if font.origin === 'custom'}
		<Button
			variant="ghost"
			size="icon"
			class="size-8 shrink-0 text-destructive"
			onclick={() => onDelete(font.slug)}
			aria-label="Delete"
		>
			<Trash2Icon class="size-3.5" />
		</Button>
	{/if}
</div>
