<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import MoreHorizontalIcon from '@lucide/svelte/icons/more-horizontal';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import PlayIcon from '@lucide/svelte/icons/play';
	import PencilIcon from '@lucide/svelte/icons/pencil';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import ThemePreview from './theme-preview.svelte';
	import OriginBadge from './origin-badge.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { TEMPLATE_COLUMNS } from './template-columns';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { FORMAT_LABELS, SectionRole } from '$lib/config/reports';
	import { ROUTES } from '$lib/config/routes';
	import type { ReportTemplate } from '$lib/types/report';

	const OUTLINE = 2;

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

	const href = $derived(ROUTES.reportTemplate(template.id));
	const theme = $derived(reportCatalog.theme(template.theme));
	const content = $derived(
		template.sections
			.filter((s) => s.enabled)
			.map((s) => reportCatalog.section(s.section))
			.filter((s) => s && s.role !== SectionRole.FURNITURE)
			.map((s) => s!.title)
	);
	const scopeLabel = $derived(
		reportCatalog.catalog?.scopes.find((s) => s.key === template.scope)?.label ?? template.scope
	);
	const audienceLabel = $derived(
		reportCatalog.catalog?.audiences.find((a) => a.key === template.narrative.audience)?.label ??
			template.narrative.audience
	);
</script>

{#snippet chip(label: string)}
	<Badge variant="outline" class="text-xs font-normal">{label}</Badge>
{/snippet}

{#snippet cell(label: string)}
	<span class="text-2xs text-muted-foreground lg:hidden">{label}</span>
{/snippet}

<div
	class="grid grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 border-b px-4 py-3 last:border-b-0 {TEMPLATE_COLUMNS}"
>
	<a {href} class="row-span-2 self-start lg:row-span-1" aria-label={template.name}>
		{#if theme}
			<ThemePreview {theme} variant="cover" class="rounded-sm" />
		{/if}
	</a>

	<div class="min-w-0">
		<div class="flex items-center gap-2">
			<a {href} class="truncate text-sm font-medium hover:text-primary">{template.name}</a>
			<OriginBadge builtin={template.is_builtin} />
		</div>
		<p class="line-clamp-1 text-xs text-muted-foreground">{template.description}</p>
	</div>

	<div class="hidden min-w-0 flex-wrap items-center gap-1 lg:flex">
		{#each content.slice(0, OUTLINE) as title (title)}
			{@render chip(title)}
		{/each}
		{#if content.length > OUTLINE}
			<HoverCard.Root>
				<HoverCard.Trigger>
					<Badge variant="outline" class="shrink-0 cursor-default text-xs font-normal">
						+{content.length - OUTLINE}
					</Badge>
				</HoverCard.Trigger>
				<HoverCard.Content class="w-56 p-1" align="start">
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-72">
						<ol>
							{#each content.slice(OUTLINE) as title (title)}
								<li class="flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm">
									<span class="truncate">{title}</span>
								</li>
							{/each}
						</ol>
					</ScrollArea>
				</HoverCard.Content>
			</HoverCard.Root>
		{/if}
	</div>

	<div class="col-span-2 col-start-2 flex flex-wrap gap-x-4 gap-y-1 text-xs lg:contents lg:text-sm">
		<div class="flex flex-col">
			{@render cell('Audience')}
			<span>{audienceLabel}</span>
		</div>
		<div class="flex flex-col">
			{@render cell('Scope')}
			<span>{scopeLabel}</span>
		</div>
		<div class="flex flex-col">
			{@render cell('Formats')}
			<div class="flex flex-wrap gap-1">
				{#each template.formats as format (format)}
					{@render chip(FORMAT_LABELS[format] ?? format)}
				{/each}
			</div>
		</div>
		<div class="flex flex-col lg:items-end">
			{@render cell('Used')}
			<span
				class="font-mono text-xs tabular-nums {template.used_count ? '' : 'text-muted-foreground'}"
			>
				{template.used_count || '—'}
			</span>
		</div>
	</div>

	<div
		class="col-start-3 row-start-1 flex items-center justify-end gap-1 lg:col-start-auto lg:row-start-auto"
	>
		<Button variant="outline" size="sm" class="h-8" onclick={() => onGenerate(template)}>
			<PlayIcon class="mr-1 size-3.5" />
			Generate
		</Button>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button variant="ghost" size="icon" class="size-8" {...props} aria-label="Actions">
						<MoreHorizontalIcon class="size-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Item>
					{#snippet child({ props })}
						<a {...props} {href}>
							{#if template.is_builtin}
								<EyeIcon class="size-4" />
								View
							{:else}
								<PencilIcon class="size-4" />
								Edit
							{/if}
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
</div>
