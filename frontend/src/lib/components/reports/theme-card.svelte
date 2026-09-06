<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import { reportsApi } from '$lib/api/reports';
	import { downloadBlob } from '$lib/utilities/download';
	import { toast } from 'svelte-sonner';
	import type { ThemeSummary } from '$lib/types/report';

	let { theme, onDelete }: { theme: ThemeSummary; onDelete: (slug: string) => void } = $props();

	async function exportTheme() {
		try {
			const source = await reportsApi.themeSource(theme.slug);
			downloadBlob(`${theme.slug}.yaml`, source, 'text/yaml');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not read that theme');
		}
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="h-24 p-3" style="background:{theme.page}">
		<div
			class="flex h-full flex-col justify-between rounded-sm p-2"
			style="background:{theme.accent}"
		>
			<span class="h-1.5 w-10 rounded-full" style="background:{theme.page};opacity:.65"></span>
			<div class="flex gap-1">
				{#each theme.chart.slice(0, 5) as colour, i (i)}
					<span class="size-2 rounded-full" style="background:{colour}"></span>
				{/each}
			</div>
		</div>
	</div>
	<div class="space-y-1 px-4 pt-3">
		<div class="flex items-center gap-2">
			<span class="font-medium">{theme.name}</span>
			{#if theme.origin === 'custom'}<Badge variant="outline" class="text-[10px]">Yours</Badge>{/if}
		</div>
		<p class="line-clamp-2 text-xs text-muted-foreground">{theme.description}</p>
	</div>
	<div class="mt-3 flex items-center justify-between border-t px-4 py-2">
		<span class="font-mono text-[11px] text-muted-foreground">{theme.slug}</span>
		<div class="flex gap-1">
			<Button variant="ghost" size="icon" class="size-7" onclick={exportTheme} aria-label="Export">
				<DownloadIcon class="size-3.5" />
			</Button>
			{#if theme.origin === 'custom'}
				<Button
					variant="ghost"
					size="icon"
					class="size-7 text-destructive"
					onclick={() => onDelete(theme.slug)}
					aria-label="Delete"
				>
					<Trash2Icon class="size-3.5" />
				</Button>
			{/if}
		</div>
	</div>
</Card.Root>
