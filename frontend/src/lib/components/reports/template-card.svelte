<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import MoreHorizontalIcon from '@lucide/svelte/icons/more-horizontal';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import PlayIcon from '@lucide/svelte/icons/play';
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
</script>

<Card.Root class="gap-0 py-0">
	<div class="flex items-start gap-3 px-4 pt-4">
		<span
			class="mt-0.5 size-9 shrink-0 rounded-md border"
			style="background:{theme?.page ?? 'var(--muted)'};border-color:{theme?.accent ??
				'var(--border)'}"
		>
			<span class="block h-1.5 w-full rounded-t-[5px]" style="background:{theme?.accent}"></span>
		</span>
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<a href={ROUTES.reportTemplate(template.id)} class="truncate font-medium hover:underline">
					{template.name}
				</a>
				{#if template.is_builtin}<Badge variant="outline" class="text-[10px]">Shipped</Badge>{/if}
			</div>
			<p class="mt-1 line-clamp-2 text-xs text-muted-foreground">{template.description}</p>
		</div>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button variant="ghost" size="icon" class="size-8" {...props} aria-label="Actions">
						<MoreHorizontalIcon class="size-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Item onSelect={() => onGenerate(template)}>
					<PlayIcon class="size-4" />
					Generate from this
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

	<div
		class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-4 py-2.5 text-xs text-muted-foreground"
	>
		<span>{enabled} sections</span>
		<span>{theme?.name ?? template.theme}</span>
		<span>{template.formats.map((f) => FORMAT_LABELS[f] ?? f).join(', ')}</span>
		{#if template.used_count}<span>used {template.used_count}×</span>{/if}
	</div>
</Card.Root>
