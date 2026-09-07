<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import SearchX from '@lucide/svelte/icons/search-x';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CapabilityChips from './capability-chips.svelte';
	import ToolSheet from './tool-sheet.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { countByTool, schemaArgs } from '$lib/utilities/mcp';
	import {
		MCP_CAPABILITIES,
		MCP_CAPABILITY_LABELS,
		MCP_TOOL_GROUPS,
		type McpTool
	} from '$lib/types/mcp';
	import type { McpTab } from '$lib/config/routes';

	interface Props {
		canAdmin: boolean;
		onTab: (tab: McpTab) => void;
	}

	let { canAdmin, onTab }: Props = $props();

	const ALL = 'all';
	const TABS = [
		{ key: ALL, label: 'All' },
		...MCP_CAPABILITIES.map((c) => ({ key: c, label: MCP_CAPABILITY_LABELS[c] }))
	];

	let capability = $state<string>(ALL);
	let search = $state('');
	let selected = $state<string | null>(null);

	const tools = $derived(mcp.tools);
	const ceiling = $derived(mcp.status?.ceiling ?? {});
	const counts = $derived(
		Object.fromEntries(
			TABS.map((t) => [t.key, tools.filter((x) => t.key === ALL || x.capability === t.key).length])
		)
	);
	const callCounts = $derived(countByTool(mcp.calls));

	const filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return tools.filter(
			(t) =>
				(capability === ALL || t.capability === capability) &&
				(!q ||
					t.name.includes(q) ||
					t.title.toLowerCase().includes(q) ||
					t.description.toLowerCase().includes(q))
		);
	});
	const groups = $derived(
		MCP_TOOL_GROUPS.map((group) => ({
			group,
			tools: filtered.filter((t) => t.group === group)
		})).filter((g) => g.tools.length)
	);
	const ordered = $derived(groups.flatMap((g) => g.tools));
	const off = $derived(tools.filter((t) => !ceiling[t.capability]));
	const offCapabilities = $derived([...new Set(off.map((t) => t.capability))]);

	const selectedIndex = $derived(ordered.findIndex((t) => t.name === selected));
	const selectedTool = $derived<McpTool | null>(selectedIndex >= 0 ? ordered[selectedIndex] : null);

	function step(dir: -1 | 1) {
		const next = ordered[selectedIndex + dir];
		if (next) selected = next.name;
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b px-2">
		<CountTabs tabs={TABS} value={capability} {counts} onChange={(k) => (capability = k)} />
		<Input
			bind:value={search}
			placeholder="Filter tools"
			class="mr-1 mb-1.5 h-8 w-full sm:w-56"
			aria-label="Filter tools"
		/>
	</div>

	{#if off.length && capability === ALL && !search}
		<p class="border-b px-5 py-2 text-xs text-muted-foreground">
			{off.length} tools are off for this instance because {offCapabilities
				.map((c) => MCP_CAPABILITY_LABELS[c as (typeof MCP_CAPABILITIES)[number]] ?? c)
				.join(' and ')} is below the ceiling.
			{#if canAdmin}
				<button
					type="button"
					class="font-medium text-primary hover:underline"
					onclick={() => onTab('server')}
				>
					Change the ceiling
				</button>
			{/if}
		</p>
	{/if}

	{#each groups as entry, i (entry.group)}
		<div
			class="flex items-baseline gap-2 border-b bg-muted/30 px-5 py-1.5 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase {i
				? 'border-t'
				: ''}"
		>
			{entry.group}
			<span class="text-xs font-medium tracking-normal normal-case tabular-nums"
				>{entry.tools.length}</span
			>
		</div>
		<div class="divide-y">
			{#each entry.tools as tool (tool.name)}
				{@const available = ceiling[tool.capability] ?? false}
				{@const args = schemaArgs(tool.schema)}
				{@const calls = callCounts.get(tool.name) ?? 0}
				<button
					type="button"
					class="flex w-full items-center gap-3 px-5 py-2.5 text-left transition-colors hover:bg-muted/40 {available
						? ''
						: 'text-muted-foreground'}"
					onclick={() => (selected = tool.name)}
				>
					<span class="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2 gap-y-0.5">
						<span class="font-mono text-sm font-medium">{tool.name}</span>
						<span class="text-sm text-muted-foreground">{tool.title}</span>
					</span>
					<span class="hidden shrink-0 items-center gap-3 text-xs text-muted-foreground sm:flex">
						{#if calls}
							<span class="tabular-nums">{calls} calls</span>
						{/if}
						<span class="tabular-nums">
							{args.length === 0
								? 'no args'
								: `${args.length} ${args.length === 1 ? 'arg' : 'args'}`}
						</span>
					</span>
					<span class="flex shrink-0 items-center gap-1.5">
						{#if tool.destructive}
							<Badge variant="destructive" class="text-[10px]">Destructive</Badge>
						{/if}
						{#if !available}
							<Badge variant="outline" class="border-dashed text-[10px]">Off</Badge>
						{/if}
						<CapabilityChips granted={[tool.capability]} />
					</span>
					<ChevronRight class="size-4 shrink-0 text-muted-foreground/60" />
				</button>
			{/each}
		</div>
	{:else}
		<div class="p-5">
			<EmptyState
				compact
				icon={SearchX}
				title="No tools match"
				description="Widen the search or pick another capability."
			/>
		</div>
	{/each}
</Card.Root>

<ToolSheet
	tool={selectedTool}
	open={selectedTool !== null}
	onOpenChange={(v) => {
		if (!v) selected = null;
	}}
	{ceiling}
	calls={mcp.calls}
	index={selectedIndex}
	total={ordered.length}
	onStep={step}
	{canAdmin}
	onCeiling={() => onTab('server')}
/>
