<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import MoreHorizontalIcon from '@lucide/svelte/icons/more-horizontal';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import PlayIcon from '@lucide/svelte/icons/play';
	import PencilIcon from '@lucide/svelte/icons/pencil';
	import ThemePreview from './theme-preview.svelte';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { FORMAT_LABELS } from '$lib/config/reports';
	import { ROUTES } from '$lib/config/routes';
	import type { ReportTemplate } from '$lib/types/report';

	let {
		template,
		onDuplicate,
		onDelete,
		onGenerate
	}: {
		template: ReportTemplate;
		onDuplicate: (t: ReportTemplate) => void;
		onDelete: (t: ReportTemplate) => void;
		onGenerate: (t: ReportTemplate) => void;
	} = $props();

	const theme = $derived(reportCatalog.theme(template.theme));
	const enabled = $derived(template.sections.filter((s) => s.enabled).length);
	const scopeLabel = $derived(template.scope === 'target' ? 'A target' : 'One scan');
</script>

<Card.Root class="gap-0 py-0">
	<div class="flex items-start gap-3.5 p-3.5">
		{#if theme}
			<div class="w-14 shrink-0">
				<ThemePreview {theme} variant="cover" class="shadow-sm" />
			</div>
		{/if}
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<a href={ROUTES.reportTemplate(template.id)} class="truncate font-medium hover:underline">
					{template.name}
				</a>
				{#if template.is_builtin}<Badge variant="outline" class="text-[10px]">Shipped</Badge>{/if}
			</div>
			<p class="mt-1 line-clamp-2 text-xs text-muted-foreground">{template.description}</p>
			<div class="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-muted-foreground">
				<span>{enabled} sections</span>
				<span aria-hidden="true">·</span>
				<span>{scopeLabel}</span>
				<span aria-hidden="true">·</span>
				<span>{theme?.name ?? template.theme}</span>
			</div>
		</div>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						variant="ghost"
						size="icon"
						class="-mt-1 -mr-1 size-8"
						{...props}
						aria-label="Actions"
					>
						<MoreHorizontalIcon class="size-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Item onSelect={() => onGenerate(template)}>
					<PlayIcon class="size-4" />
					Generate from this
				</DropdownMenu.Item>
				<DropdownMenu.Item>
					{#snippet child({ props })}
						<a {...props} href={ROUTES.reportTemplate(template.id)}>
							<PencilIcon class="size-4" />
							Edit
						</a>
					{/snippet}
				</DropdownMenu.Item>
				<DropdownMenu.Item onSelect={() => onDuplicate(template)}>
					<CopyIcon class="size-4" />
					Duplicate
				</DropdownMenu.Item>
				{#if !template.is_builtin}
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onSelect={() => onDelete(template)}>
						<Trash2Icon class="size-4" />
						Delete
					</DropdownMenu.Item>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>

	<div class="flex items-center justify-between gap-2 border-t px-3.5 py-2 text-xs">
		<span class="flex flex-wrap gap-1">
			{#each template.formats as format (format)}
				<span class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
					{FORMAT_LABELS[format] ?? format}
				</span>
			{/each}
		</span>
		<span class="text-muted-foreground">
			{template.used_count ? `used ${template.used_count}×` : 'never used'}
		</span>
	</div>
</Card.Root>
