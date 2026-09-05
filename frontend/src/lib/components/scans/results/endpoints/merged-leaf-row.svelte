<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Rows3 from '@lucide/svelte/icons/rows-3';

	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Popover from '$lib/components/ui/popover';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import SourceMarks from './source-marks.svelte';
	import StatusBar from './status-bar.svelte';
	import StatusMark from './status-mark.svelte';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { OUTLINE_LEAD_COLUMNS } from './columns';
	import { GUIDE_WIDTH, OUTLINE_ROW_ATTR } from './outline-context';
	import {
		ENDPOINT_CLASS_ICONS,
		ENDPOINT_CLASS_LABELS,
		ENDPOINT_CLASS_TONE,
		INTEREST_LABELS,
		SENSITIVE_INTEREST,
		STATIC_CLASSES
	} from '$lib/config/endpoints';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import type { MergedLeaf } from '$lib/utilities/endpoints';

	interface Props {
		leaf: MergedLeaf;
		depth: number;
		columns: TableColumn[];
		terms?: string[];
		pad?: string;
		focused?: boolean;
		active?: boolean;
		onOpen: (leaf: MergedLeaf) => void;
		onFilter: (token: string) => void;
		onHost: (host: string) => void;
	}

	let {
		leaf,
		depth,
		columns,
		terms = [],
		pad = 'py-3',
		focused = false,
		active = false,
		onOpen,
		onFilter,
		onHost
	}: Props = $props();

	let ClassIcon = $derived(ENDPOINT_CLASS_ICONS[leaf.endpoint_class]);
	let classTone = $derived(ENDPOINT_CLASS_TONE[leaf.endpoint_class] ?? 'text-muted-foreground');
	let dim = $derived(STATIC_CLASSES.has(leaf.endpoint_class));
	let isIndex = $derived(leaf.name === '/');
	let sensitive = $derived(leaf.interest.filter((i) => SENSITIVE_INTEREST.has(i)));
	let testable = $derived(leaf.interest.filter((i) => !SENSITIVE_INTEREST.has(i)));
	let verified = $derived(leaf.endpoints - leaf.unprobed);
	let verifiedMix = $derived(
		Object.fromEntries(Object.entries(leaf.status_mix).filter(([k]) => k !== 'none'))
	);
	let attrs = $derived({ [OUTLINE_ROW_ATTR]: leaf.key, 'data-outline-kind': 'leaf' });
</script>

<div
	class="group flex items-start gap-3 border-b px-4 text-sm transition-colors {pad} {rowTone(
		active,
		focused
	)}"
	role="button"
	tabindex="0"
	{...attrs}
	onclick={() => onOpen(leaf)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(leaf);
		}
	}}
>
	<div class="min-w-0 flex-1 {OUTLINE_LEAD_COLUMNS[0].width}">
		<div class="flex items-start gap-x-1.5 leading-5">
			{#each Array(depth) as _, i (i)}
				<span class="{GUIDE_WIDTH} -ml-1.5 h-5 shrink-0 border-l border-border/70 ml-[7px]"></span>
			{/each}
			<span class="size-4 shrink-0"></span>
			<span class="flex h-5 shrink-0 items-center {dim ? 'text-muted-foreground/70' : classTone}">
				<ClassIcon class="size-4" />
			</span>
			<span class="flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-1">
				<span class="font-mono text-sm break-all {dim ? 'text-muted-foreground' : 'font-medium'}">
					<HighlightText text={leaf.name} {terms} />
				</span>
				{#if isIndex}
					<span class="text-[11px] text-muted-foreground italic">index</span>
				{/if}
				{#if leaf.param_count > 0}
					<span class="font-mono text-xs text-primary">?{leaf.params.join('&')}</span>
				{/if}
				{#if leaf.hosts > 1}
					<Popover.Root>
						<Popover.Trigger>
							{#snippet child({ props })}
								<button
									{...props}
									type="button"
									class="text-[11px] text-muted-foreground hover:text-primary hover:underline"
									onclick={(e) => e.stopPropagation()}
								>
									on {leaf.hosts} hosts
								</button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content class="w-72 p-0" align="start">
							<div class="border-b px-3 py-2">
								<p class="text-xs font-medium">
									{leaf.hosts} hosts serve <span class="font-mono">{leaf.path}</span>
								</p>
							</div>
							<div class="flex flex-wrap gap-1 p-3">
								{#each leaf.host_names as host (host)}
									<button
										type="button"
										class="rounded border px-1.5 py-0.5 font-mono text-[11px] hover:bg-accent"
										onclick={(e) => {
											e.stopPropagation();
											onHost(host);
										}}
									>
										{host}
									</button>
								{/each}
								{#if leaf.hosts > leaf.host_names.length}
									<span class="self-center text-[11px] text-muted-foreground">
										+{leaf.hosts - leaf.host_names.length} more
									</span>
								{/if}
							</div>
							<div class="border-t px-3 py-2">
								<Button
									variant="outline"
									size="sm"
									class="h-7 gap-1.5 text-xs"
									onclick={(e) => {
										e.stopPropagation();
										onFilter(leaf.query);
									}}
								>
									<Rows3 class="size-3" /> Show every host in list
								</Button>
							</div>
						</Popover.Content>
					</Popover.Root>
				{:else if leaf.host_names[0]}
					<button
						type="button"
						class="font-mono text-[11px] text-muted-foreground hover:text-primary hover:underline"
						onclick={(e) => {
							e.stopPropagation();
							onHost(leaf.host_names[0]);
						}}
					>
						{leaf.host_names[0]}
					</button>
				{/if}
				{#if sensitive.length || testable.length}
					<span class="flex flex-wrap items-center gap-1">
						{#each sensitive as key (key)}
							<Badge variant="destructive" class="h-4 gap-1 px-1.5 text-[10px]">
								<ShieldAlert class="size-2.5" />
								{INTEREST_LABELS[key] ?? key}
							</Badge>
						{/each}
						{#each testable as key (key)}
							<Badge variant="warning" class="h-4 px-1.5 text-[10px]">
								{INTEREST_LABELS[key] ?? key}
							</Badge>
						{/each}
					</span>
				{/if}
			</span>
		</div>
	</div>

	<div class="{OUTLINE_LEAD_COLUMNS[1].width} shrink-0">
		{#if leaf.endpoints === 1}
			<StatusMark status={leaf.sample_status} probed={verified > 0} />
		{:else if verified > 0}
			<div class="flex h-5 items-center">
				<StatusBar mix={verifiedMix} total={verified} />
			</div>
		{:else}
			<Hint text="No host was asked for this path in this scan.">
				{#snippet child(props)}
					<span
						{...props}
						class="flex h-5 shrink-0 items-center gap-1.5 text-xs text-muted-foreground"
					>
						<span class="size-1.5 rounded-full border border-dashed border-muted-foreground/60"
						></span>
						<span class="italic">not checked</span>
					</span>
				{/snippet}
			</Hint>
		{/if}
	</div>

	{#each columns as column (column.key)}
		<div class="{column.width} min-w-0 shrink-0 {column.align === 'right' ? 'text-right' : ''}">
			{#if column.key === 'kind'}
				<span class="flex h-5 items-center gap-1.5 text-xs text-muted-foreground">
					<ClassIcon class="size-3.5 shrink-0" />
					{ENDPOINT_CLASS_LABELS[leaf.endpoint_class] ?? leaf.endpoint_class}
				</span>
			{:else if column.key === 'params'}
				{#if leaf.param_count === 0}
					<span class="text-xs text-muted-foreground">—</span>
				{:else}
					<div class="flex flex-wrap gap-1">
						{#each leaf.params.slice(0, 3) as name (name)}
							<button
								type="button"
								class="rounded bg-muted px-1 font-mono text-[10px] hover:bg-muted/70"
								onclick={(e) => {
									e.stopPropagation();
									onFilter(`param:${name}`);
								}}
							>
								{name}
							</button>
						{/each}
						{#if leaf.params.length > 3}
							<span class="text-[10px] text-muted-foreground">+{leaf.params.length - 3}</span>
						{/if}
					</div>
				{/if}
			{:else if column.key === 'sources'}
				<SourceMarks sources={leaf.sources} />
			{:else if column.key === 'size' || column.key === 'title' || column.key === 'tech' || column.key === 'seen'}
				<span class="text-xs text-muted-foreground">—</span>
			{/if}
		</div>
	{/each}

	<div class="{ACTIONS_PIN} {pinTone(active, focused)}">
		<div class={ACTIONS_BODY}>
			<Hint text="Copy a sample URL">
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						onclick={(e) => {
							e.stopPropagation();
							void writeClipboard(leaf.sample_url);
						}}
					>
						<Copy class="size-3.5" />
					</Button>
				{/snippet}
			</Hint>
			<Hint text="Open a sample in a new tab">
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						href={leaf.sample_url}
						target="_blank"
						rel="noopener noreferrer"
						onclick={(e) => e.stopPropagation()}
					>
						<ExternalLink class="size-3.5" />
					</Button>
				{/snippet}
			</Hint>
		</div>
	</div>
</div>
