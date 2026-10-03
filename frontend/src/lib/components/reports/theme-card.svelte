<script lang="ts">
	import { SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import ThemePreview from './theme-preview.svelte';
	import OriginBadge from './origin-badge.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { downloadBlob } from '$lib/utilities/download';
	import { LibraryOrigin, fontStack } from '$lib/config/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { auth } from '$lib/stores/auth.svelte';
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
			toast.error(e instanceof Error ? e.message : 'Theme not exported');
		}
	}
</script>

<article class="flex flex-col overflow-hidden rounded-lg border bg-card">
	<div class="flex justify-center gap-2 border-b bg-muted/40 px-4 pt-4">
		<div class="w-20 translate-y-1">
			<ThemePreview {theme} variant="cover" class="rounded-b-none shadow-sm" />
		</div>
		<div class="w-20 translate-y-1">
			<ThemePreview {theme} variant="page" class="rounded-b-none shadow-sm" />
		</div>
	</div>

	<div class="flex flex-1 flex-col gap-2 p-3">
		<div class="flex items-start justify-between gap-2">
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<span class="truncate text-sm font-medium">{theme.name}</span>
					<OriginBadge builtin={theme.origin === LibraryOrigin.BUILTIN} />
				</div>
				<p class="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{theme.description}</p>
			</div>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							variant="ghost"
							size="icon"
							class="-mt-1 -mr-1.5 size-7 shrink-0"
							{...props}
							aria-label="Actions for {theme.name}"
						>
							<EllipsisIcon class="size-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end">
					<DropdownMenu.Item onSelect={exportTheme}>
						<DownloadIcon class="size-4" />
						Export as YAML
					</DropdownMenu.Item>
					{#if theme.origin === LibraryOrigin.CUSTOM && auth.user?.is_superuser}
						<DropdownMenu.Separator />
						<DropdownMenu.Item variant="destructive" onSelect={() => onDelete(theme.slug)}>
							<Trash2Icon class="size-4" />
							Delete
						</DropdownMenu.Item>
					{/if}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>

		<div class="mt-auto flex items-center justify-between gap-2 border-t pt-2">
			<span
				class="truncate text-xs text-muted-foreground"
				style="font-family:{fontStack(theme.heading_font, fonts)}"
			>
				{faces}
			</span>
			<span class="flex shrink-0 gap-1" aria-hidden="true">
				{#each SEVERITY_ORDER as key (key)}
					<span class="size-2 rounded-full" style="background:{theme.severity[key]}"></span>
				{/each}
			</span>
		</div>
	</div>
</article>
