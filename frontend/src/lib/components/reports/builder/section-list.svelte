<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import ChevronUpIcon from '@lucide/svelte/icons/chevron-up';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import SectionFieldControl from './section-field.svelte';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { SECTION_GROUP_ORDER } from '$lib/config/reports';
	import type { SectionEntry } from '$lib/types/report';

	let { sections = $bindable() }: { sections: SectionEntry[] } = $props();

	let openConfig = $state<number | null>(null);

	const usedOnce = $derived(
		new Set(
			sections.map((s) => s.section).filter((name) => !reportCatalog.section(name)?.repeatable)
		)
	);

	function move(index: number, delta: number) {
		const to = index + delta;
		if (to < 0 || to >= sections.length) return;
		const next = [...sections];
		[next[index], next[to]] = [next[to], next[index]];
		sections = next;
		if (openConfig === index) openConfig = to;
	}

	function remove(index: number) {
		sections = sections.filter((_, i) => i !== index);
		openConfig = null;
	}

	function add(name: string) {
		const spec = reportCatalog.section(name);
		if (!spec) return;
		sections = [
			...sections,
			{ section: name, enabled: true, title: '', config: { ...spec.defaults } }
		];
		openConfig = sections.length - 1;
	}

	function patch(index: number, key: string, value: unknown) {
		sections = sections.map((entry, i) =>
			i === index ? { ...entry, config: { ...entry.config, [key]: value } } : entry
		);
	}

	function setEntry(index: number, changes: Partial<SectionEntry>) {
		sections = sections.map((entry, i) => (i === index ? { ...entry, ...changes } : entry));
	}
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between">
		<p class="text-sm text-muted-foreground">
			{sections.filter((s) => s.enabled).length} of {sections.length} sections print, in this order.
		</p>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button variant="outline" size="sm" {...props}>
						<PlusIcon class="mr-1.5 size-3.5" />
						Add section
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="max-h-none w-80 overflow-visible">
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-96">
					{#each SECTION_GROUP_ORDER as group (group)}
						{@const items = reportCatalog.sectionsByGroup(group)}
						{#if items.length}
							<DropdownMenu.Label class="text-[11px] uppercase tracking-wide text-muted-foreground">
								{reportCatalog.catalog?.groups.find((g) => g.key === group)?.label ?? group}
							</DropdownMenu.Label>
							{#each items as item (item.name)}
								<DropdownMenu.Item
									disabled={usedOnce.has(item.name)}
									onSelect={() => add(item.name)}
								>
									<span class="flex flex-col items-start gap-0.5">
										<span>{item.title}</span>
										<span class="text-xs text-muted-foreground">{item.description}</span>
									</span>
								</DropdownMenu.Item>
							{/each}
						{/if}
					{/each}
				</ScrollArea>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>

	<div class="overflow-hidden rounded-lg border">
		{#each sections as entry, index (index)}
			{@const spec = reportCatalog.section(entry.section)}
			<Collapsible.Root open={openConfig === index} class="border-b last:border-b-0">
				<div class="flex items-center gap-3 px-3 py-2.5" class:opacity-60={!entry.enabled}>
					<span class="w-6 text-center font-mono text-xs text-muted-foreground">{index + 1}</span>
					<Switch
						checked={entry.enabled}
						onCheckedChange={(v) => setEntry(index, { enabled: v })}
					/>
					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<span class="truncate text-sm font-medium">
								{entry.title || spec?.title || entry.section}
							</span>
							{#if spec?.requires.length}
								<Badge variant="outline" class="text-[10px]">
									needs {spec.requires.join(', ').replaceAll('_', ' ')}
								</Badge>
							{/if}
							{#if !spec}
								<Badge variant="destructive" class="text-[10px]">unknown</Badge>
							{/if}
						</div>
						{#if spec}
							<p class="truncate text-xs text-muted-foreground">{spec.description}</p>
						{/if}
					</div>
					<div class="flex shrink-0 items-center gap-0.5">
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={index === 0}
							onclick={() => move(index, -1)}
							aria-label="Move up"
						>
							<ChevronUpIcon class="size-3.5" />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={index === sections.length - 1}
							onclick={() => move(index, 1)}
							aria-label="Move down"
						>
							<ChevronDownIcon class="size-3.5" />
						</Button>
						<Collapsible.Trigger>
							{#snippet child({ props })}
								<Button
									variant="ghost"
									size="icon"
									class="size-7"
									{...props}
									onclick={() => (openConfig = openConfig === index ? null : index)}
									aria-label="Settings"
								>
									<Settings2Icon class="size-3.5" />
								</Button>
							{/snippet}
						</Collapsible.Trigger>
						<Button
							variant="ghost"
							size="icon"
							class="size-7 text-destructive"
							onclick={() => remove(index)}
							aria-label="Remove"
						>
							<Trash2Icon class="size-3.5" />
						</Button>
					</div>
				</div>

				<Collapsible.Content>
					<div class="divide-y divide-border border-t bg-muted/30 px-4">
						<div class="space-y-2 py-3">
							<span class="text-sm">Heading in the document</span>
							<Input
								value={entry.title}
								placeholder={spec?.title ?? ''}
								class="h-9 max-w-md"
								oninput={(e) => setEntry(index, { title: e.currentTarget.value })}
							/>
						</div>
						{#each spec?.fields ?? [] as field (field.name)}
							<SectionFieldControl
								{field}
								value={entry.config[field.name] ?? field.default}
								onChange={(v) => patch(index, field.name, v)}
							/>
						{/each}
						{#if !spec?.fields.length}
							<p class="py-3 text-xs text-muted-foreground">
								This section has nothing to configure.
							</p>
						{/if}
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
		{/each}
	</div>
</div>
