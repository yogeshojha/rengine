<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Filter from '@lucide/svelte/icons/filter';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import Send from '@lucide/svelte/icons/send';

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
	import { proxyLabel } from './proxy';
	import {
		FOLDER_GLYPH_ICONS,
		FOLDER_GLYPH_LABELS,
		FOLDER_GLYPH_TONE,
		FOLDER_OPEN_ICON,
		FolderGlyph,
		INTEREST_LABELS,
		INTEREST_TONE,
		SENSITIVE_INTEREST
	} from '$lib/config/endpoints';
	import { whyReasons, type TreeNode } from '$lib/utilities/endpoints';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

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
		unverified?: number;
		parentKey?: string;
		connectors?: Connector[];
		catalog?: ConnectorSpec[];
		onToggle: () => void;
		onCopy: () => void;
		onWordlist: () => void;
		onOnly: () => void;
		onList: () => void;
		onVerify?: () => void;
		onSend?: (connectorId: string) => void;
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
		unverified = 0,
		parentKey = '',
		connectors = [],
		catalog = [],
		onToggle,
		onCopy,
		onWordlist,
		onOnly,
		onList,
		onVerify,
		onSend
	}: Props = $props();

	let isGroup = $derived(node.kind === 'group');
	let glyph = $derived(node.glyph in FOLDER_GLYPH_ICONS ? node.glyph : FolderGlyph.FOLDER);
	let Icon = $derived(
		open && glyph === FolderGlyph.FOLDER ? FOLDER_OPEN_ICON : FOLDER_GLYPH_ICONS[glyph]
	);
	let tone = $derived(
		node.archive_only
			? 'text-muted-foreground/70'
			: (FOLDER_GLYPH_TONE[glyph] ?? 'text-muted-foreground')
	);
	// one reason per row: the most serious thing inside it, never a list
	let reason = $derived(whyReasons(node.interest, 1)[0] ?? '');
	let verifiedMix = $derived(
		Object.fromEntries(Object.entries(node.status_mix).filter(([k]) => k !== 'none'))
	);
	let hostNote = $derived(merged && !isGroup && node.hosts > 1 ? `on ${node.hosts} hosts` : '');
	let noun = $derived(isGroup ? 'group' : 'folder');
	let attrs = $derived({
		[OUTLINE_ROW_ATTR]: node.key,
		'data-outline-kind': 'folder',
		'data-outline-name': node.name,
		'data-outline-parent': parentKey
	});
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
			<Hint
				text={node.archive_only
					? 'Known only to an archive. Nothing in here answered this scan.'
					: (FOLDER_GLYPH_LABELS[glyph] ?? '')}
			>
				{#snippet child(props)}
					<span {...props} class="flex h-5 shrink-0 items-center {tone}">
						<Icon class="size-4 {node.archive_only ? '[stroke-dasharray:2_2]' : ''}" />
					</span>
				{/snippet}
			</Hint>
			<button
				type="button"
				class="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1 text-left"
				onclick={onToggle}
			>
				<span
					class="text-sm font-medium break-all {isGroup ? '' : 'font-mono'} {node.archive_only
						? 'text-muted-foreground'
						: ''}"
				>
					<HighlightText text={node.name} {terms} />
				</span>
				{#if node.archive_only}
					<span class="text-[11px] text-muted-foreground/80 italic">archived</span>
				{/if}
				{#if hostNote}
					<span class="text-[11px] text-muted-foreground">{hostNote}</span>
				{/if}
				{#if hint}
					<span class="font-mono text-[11px] text-muted-foreground">{hint}</span>
				{/if}
				{#if reason}
					<Badge variant={INTEREST_TONE[reason] ?? 'warning'} class="h-4 gap-1 px-1.5 text-[10px]">
						{#if SENSITIVE_INTEREST.has(reason)}<ShieldAlert class="size-2.5" />{/if}
						{INTEREST_LABELS[reason] ?? reason}
					</Badge>
				{/if}
				{#if node.anomaly}
					<span class="flex items-center gap-1 text-[11px] text-warning">
						<TriangleAlert class="size-3" />
						{node.anomaly}
					</span>
				{/if}
			</button>
			<span
				class="ml-auto flex shrink-0 items-center gap-1.5 pl-3 text-xs tabular-nums text-muted-foreground"
			>
				<span class="font-medium text-foreground">{node.subtree_count.toLocaleString()}</span>
				{#if node.new_count}
					<Hint
						text="{node.new_count.toLocaleString()} {node.new_count === 1
							? 'endpoint'
							: 'endpoints'} first seen in this scan"
					>
						{#snippet child(props)}
							<span {...props} class="font-medium text-success"
								>+{node.new_count.toLocaleString()}</span
							>
						{/snippet}
					</Hint>
				{/if}
				{#if node.gone_count}
					<Hint
						text="{node.gone_count.toLocaleString()} {node.gone_count === 1
							? 'endpoint'
							: 'endpoints'} from the previous scan {node.gone_count === 1
							? 'was'
							: 'were'} not found here"
					>
						{#snippet child(props)}
							<span {...props} class="font-medium text-muted-foreground"
								>−{node.gone_count.toLocaleString()}</span
							>
						{/snippet}
					</Hint>
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
				<DropdownMenu.Content align="end" class="w-60">
					<DropdownMenu.Item onclick={onOnly}>
						<Filter class="size-3.5" /> Only this {noun}
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={onList}>
						<Rows3 class="size-3.5" /> Show in list
					</DropdownMenu.Item>
					{#if (onVerify && unverified > 0) || (onSend && connectors.length)}
						<DropdownMenu.Separator />
					{/if}
					{#if onVerify && unverified > 0}
						<DropdownMenu.Item onclick={onVerify}>
							<ShieldCheck class="size-3.5" />
							Verify this {noun}
							<span class="ml-auto text-xs tabular-nums text-muted-foreground">
								{unverified.toLocaleString()} unchecked
							</span>
						</DropdownMenu.Item>
					{/if}
					{#if onSend}
						{#each connectors as c (c.id)}
							<DropdownMenu.Item onclick={() => onSend(c.id)}>
								<Send class="size-3.5" />
								Send to {proxyLabel(c, catalog)}
								{#if connectors.length > 1}
									<span class="ml-auto truncate text-xs text-muted-foreground">{c.name}</span>
								{/if}
							</DropdownMenu.Item>
						{/each}
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={onCopy}>
						<Copy class="size-3.5" /> Copy URLs in branch
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={onWordlist}>
						<ListOrdered class="size-3.5" /> Copy paths as wordlist
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
