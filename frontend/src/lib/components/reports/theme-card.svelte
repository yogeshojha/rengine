<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import MoreHorizontalIcon from '@lucide/svelte/icons/more-horizontal';
	import ThemePreview from './theme-preview.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { downloadBlob } from '$lib/utilities/download';
	import { fontStack } from '$lib/config/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { toast } from 'svelte-sonner';
	import type { ThemeSummary } from '$lib/types/report';

	let { theme, onDelete }: { theme: ThemeSummary; onDelete: (slug: string) => void } = $props();

	const fonts = $derived(reportCatalog.catalog?.fonts ?? []);
	const heading = $derived(
		fonts.find((f) => f.slug === theme.heading_font)?.name ?? theme.heading_font
	);
	const body = $derived(fonts.find((f) => f.slug === theme.body_font)?.name ?? theme.body_font);
	const faces = $derived(heading === body ? heading : `${heading} · ${body}`);

	async function exportTheme() {
		try {
			const source = await reportsApi.themeSource(theme.slug);
			downloadBlob(`${theme.slug}.yaml`, source, 'text/yaml');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'That theme could not be read');
		}
	}
</script>

<Card.Root class="group gap-0 overflow-hidden py-0">
	<div class="grid grid-cols-2 gap-1.5 bg-muted/40 p-1.5">
		<ThemePreview {theme} variant="cover" class="shadow-sm" />
		<ThemePreview {theme} variant="page" class="shadow-sm" />
	</div>

	<div class="flex items-start gap-2 border-t px-3.5 pt-3">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<span class="truncate font-medium">{theme.name}</span>
				{#if theme.origin === 'custom'}
					<Badge variant="outline" class="text-[10px]">Yours</Badge>
				{/if}
			</div>
			<p class="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{theme.description}</p>
		</div>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button variant="ghost" size="icon" class="-mr-1 size-7" {...props} aria-label="Actions">
						<MoreHorizontalIcon class="size-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Item onSelect={exportTheme}>
					<DownloadIcon class="size-4" />
					Export as YAML
				</DropdownMenu.Item>
				{#if theme.origin === 'custom'}
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onSelect={() => onDelete(theme.slug)}>
						<Trash2Icon class="size-4" />
						Delete
					</DropdownMenu.Item>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>

	<div class="mt-2.5 flex items-center justify-between gap-2 border-t px-3.5 py-2">
		<span
			class="truncate text-xs text-muted-foreground"
			style="font-family:{fontStack(theme.heading_font, fonts)}"
		>
			{faces}
		</span>
		<span class="flex shrink-0 gap-1" aria-hidden="true">
			{#each ['critical', 'high', 'medium', 'low', 'info'] as key (key)}
				<span class="size-2 rounded-full" style="background:{theme.severity[key]}"></span>
			{/each}
		</span>
	</div>
</Card.Root>
