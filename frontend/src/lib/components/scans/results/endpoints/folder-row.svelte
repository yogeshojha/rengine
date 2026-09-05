<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Globe from '@lucide/svelte/icons/globe';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Filter from '@lucide/svelte/icons/filter';
	import Rows3 from '@lucide/svelte/icons/rows-3';

	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import SourceMarks from './source-marks.svelte';
	import StatusBar from './status-bar.svelte';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { OUTLINE_LEAD_COLUMNS } from './columns';
	import { GUIDE_WIDTH, OUTLINE_ROW_ATTR } from './outline-context';
	import {
		FOLDER_GLYPH_ICONS,
		FOLDER_GLYPH_LABELS,
		FOLDER_GLYPH_TONE,
		FOLDER_OPEN_ICON,
		FolderGlyph,
		INTEREST_LABELS,
		SENSITIVE_INTEREST
	} from '$lib/config/endpoints';
	import type { TreeNode } from '$lib/utilities/endpoints';

	interface Props {
		node: TreeNode;
		open: boolean;
		depth: number;
		columns: TableColumn[];
		terms?: string[];
		merged?: boolean;
		pad?: string;
		hint?: string;
		focused?: boolean;
		onToggle: () => void;
		onCopy: () => void;
		onOnly: () => void;
		onList: () => void;
	}

	let {
		node,
		open,
		depth,
		columns,
		terms = [],
		merged = false,
		pad = 'py-3',
		hint = '',
		focused = false,
		onToggle,
		onCopy,
		onOnly,
		onList
	}: Props = $props();

	const MAX_BADGES = 2;

	let isHost = $derived(node.kind === 'host');
	let glyph = $derived(node.glyph in FOLDER_GLYPH_ICONS ? node.glyph : FolderGlyph.FOLDER);
	let Icon = $derived(
		open && glyph === FolderGlyph.FOLDER ? FOLDER_OPEN_ICON : FOLDER_GLYPH_ICONS[glyph]
	);
	let tone = $derived(FOLDER_GLYPH_TONE[glyph] ?? 'text-muted-foreground');
	let sensitive = $derived(node.interest.filter((i) => SENSITIVE_INTEREST.has(i)));
	let testable = $derived(node.interest.filter((i) => !SENSITIVE_INTEREST.has(i)));
	let shownBadges = $derived([...sensitive, ...testable].slice(0, MAX_BADGES));
	let extraBadges = $derived(Math.max(0, node.interest.length - shownBadges.length));
	let verifiedMix = $derived(
		Object.fromEntries(Object.entries(node.status_mix).filter(([k]) => k !== 'none'))
	);
	let hostNote = $derived(merged && !isHost && node.hosts > 1 ? `on ${node.hosts} hosts` : '');
	let attrs = $derived({ [OUTLINE_ROW_ATTR]: node.key, 'data-outline-kind': 'folder' });
</script>

<div
	class="group flex items-start gap-3 border-b px-4 text-sm transition-colors {pad} {rowTone(
		false,
		focused
	)}"
	{...attrs}
>
	<div class="min-w-0 flex-1 {OUTLINE_LEAD_COLUMNS[0].width}">
		<div class="flex items-start gap-x-1.5 leading-5">
			{#each Array(depth) as _, i (i)}
				<span class="{GUIDE_WIDTH} -ml-1.5 h-5 shrink-0 border-l border-border/70 ml-[7px]"></span>
			{/each}
			<button
				type="button"
				class="flex size-4 shrink-0 items-center justify-center self-start rounded text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {node.child_count ||
				node.direct_count
					? ''
					: 'invisible'}"
				style="margin-top:2px"
				aria-label={open ? 'Collapse' : 'Expand'}
				aria-expanded={open}
				onclick={onToggle}
			>
				<ChevronRight class="size-3.5 transition-transform {open ? 'rotate-90' : ''}" />
			</button>
			{#if isHost}
				<span class="flex h-5 shrink-0 items-center text-foreground">
					<Globe class="size-4" />
				</span>
			{:else}
				<Hint text={FOLDER_GLYPH_LABELS[glyph] ?? ''}>
					{#snippet child(props)}
						<span {...props} class="flex h-5 shrink-0 items-center {tone}">
							<Icon class="size-4" />
						</span>
					{/snippet}
				</Hint>
			{/if}
			<button
				type="button"
				class="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1 text-left"
				onclick={onToggle}
			>
				<span class="font-mono {isHost ? 'text-sm' : 'text-sm'} font-medium break-all">
					<HighlightText text={node.name} {terms} />
				</span>
				{#if hostNote}
					<span class="text-[11px] text-muted-foreground">{hostNote}</span>
				{/if}
				{#if hint}
					<span class="font-mono text-[11px] text-muted-foreground">in {hint}</span>
				{/if}
				{#if shownBadges.length}
					<span class="flex flex-wrap items-center gap-1">
						{#each shownBadges as key (key)}
							<Badge
								variant={SENSITIVE_INTEREST.has(key) ? 'destructive' : 'warning'}
								class="h-4 gap-1 px-1.5 text-[10px]"
							>
								{#if SENSITIVE_INTEREST.has(key)}<ShieldAlert class="size-2.5" />{/if}
								{INTEREST_LABELS[key] ?? key}
							</Badge>
						{/each}
						{#if extraBadges}
							<span class="text-[10px] text-muted-foreground">+{extraBadges}</span>
						{/if}
					</span>
				{/if}
			</button>
			<span class="ml-auto shrink-0 pl-3 text-xs tabular-nums text-muted-foreground">
				<span class="font-medium text-foreground">{node.subtree_count.toLocaleString()}</span>
				{#if isHost && node.verified}
					· {node.verified.toLocaleString()} verified
				{/if}
			</span>
		</div>
	</div>

	<div class="{OUTLINE_LEAD_COLUMNS[1].width} shrink-0">
		{#if node.verified > 0}
			<div class="flex h-5 items-center">
				<StatusBar mix={verifiedMix} total={node.verified} />
			</div>
		{/if}
	</div>

	{#each columns as column (column.key)}
		<div class="{column.width} min-w-0 shrink-0 {column.align === 'right' ? 'text-right' : ''}">
			{#if column.key === 'params' && node.params > 0}
				<span class="flex h-5 items-center text-xs text-muted-foreground">
					{node.params.toLocaleString()} take input
				</span>
			{:else if column.key === 'sources'}
				<SourceMarks sources={node.sources} />
			{/if}
		</div>
	{/each}

	<div class="{ACTIONS_PIN} {pinTone(false, focused)}">
		<div class={ACTIONS_BODY}>
			<Hint text="Copy every URL in this branch">
				{#snippet child(props)}
					<Button {...props} variant="ghost" size="icon" class="size-7" onclick={onCopy}>
						<Copy class="size-3.5" />
					</Button>
				{/snippet}
			</Hint>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7" aria-label="More actions">
							<Ellipsis class="size-3.5" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-52">
					<DropdownMenu.Item onclick={onOnly}>
						<Filter class="size-3.5" /> Only this {isHost ? 'host' : 'folder'}
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={onList}>
						<Rows3 class="size-3.5" /> Show in list
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={onCopy}>
						<Copy class="size-3.5" /> Copy URLs in branch
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
