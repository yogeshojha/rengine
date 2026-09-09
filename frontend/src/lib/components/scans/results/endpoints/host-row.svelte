<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import Rows3 from '@lucide/svelte/icons/rows-3';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';
	import Send from '@lucide/svelte/icons/send';
	import ExternalLink from '@lucide/svelte/icons/external-link';

	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import SourceMarks from './source-marks.svelte';
	import StatusBar from './status-bar.svelte';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { HOST_LEAD_COLUMNS } from './columns';
	import { proxyLabel } from './proxy';
	import {
		FOLDER_GLYPH_LABELS,
		FolderGlyph,
		INTEREST_LABELS,
		INTEREST_TONE
	} from '$lib/config/endpoints';
	import { whyReasons, type FolderChip, type TreeNode } from '$lib/utilities/endpoints';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		node: TreeNode;
		columns: TableColumn[];
		terms?: string[];
		pad?: string;
		focused?: boolean;
		searching?: boolean;
		connectors?: Connector[];
		catalog?: ConnectorSpec[];
		onEnter: (host: string) => void;
		onEnterFolder: (host: string, chip: FolderChip) => void;
		onCopy: (node: TreeNode) => void;
		onWordlist: (node: TreeNode) => void;
		onList: (node: TreeNode) => void;
		onVerify?: (node: TreeNode) => void;
		onSend?: (node: TreeNode, connectorId: string) => void;
	}

	let {
		node,
		columns,
		terms = [],
		pad = 'py-3',
		focused = false,
		searching = false,
		connectors = [],
		catalog = [],
		onEnter,
		onEnterFolder,
		onCopy,
		onWordlist,
		onList,
		onVerify,
		onSend
	}: Props = $props();

	const CHIP_TONE: Record<string, string> = {
		[FolderGlyph.SENSITIVE]: 'border-destructive/40 bg-destructive/5 text-foreground',
		[FolderGlyph.ADMIN]: 'border-warning/45 bg-warning/10 text-foreground',
		[FolderGlyph.AUTH]: 'border-warning/45 bg-warning/10 text-foreground',
		[FolderGlyph.API]: 'border-info/40 bg-info/10 text-foreground'
	};

	let identity = $derived(node.identity);
	let firstTech = $derived(identity?.tech[0] ?? '');
	let verifiedMix = $derived(
		Object.fromEntries(Object.entries(node.status_mix).filter(([k]) => k !== 'none'))
	);
	let why = $derived(whyReasons(node.interest));
	let moreFolders = $derived(
		Math.max(0, node.folders - node.chips.filter((c) => c.path !== '/').length)
	);
	let openUrl = $derived(node.sample_url ?? `https://${node.name}/`);

	function chipClass(chip: FolderChip): string {
		const tone = CHIP_TONE[chip.glyph] ?? 'border-border/70 bg-muted/40';
		return chip.archive_only ? `${tone} border-dashed text-muted-foreground` : tone;
	}
	function chipHint(chip: FolderChip): string {
		const parts = [FOLDER_GLYPH_LABELS[chip.glyph] ?? 'Folder'];
		if (chip.archive_only) parts.push('Known only to an archive; nothing here answered.');
		return parts.join(' · ');
	}
	function stop(e: Event) {
		e.stopPropagation();
	}
</script>

<div
	class="group flex items-start gap-3 border-b px-4 text-sm transition-colors {pad} {rowTone(
		false,
		focused
	)}"
	role="button"
	tabindex="0"
	data-host-row={node.name}
	onclick={() => onEnter(node.name)}
	onkeydown={(e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			onEnter(node.name);
		}
	}}
>
	<div class="min-w-0 flex-1 {HOST_LEAD_COLUMNS[0].width}">
		<div class="flex items-center gap-2 leading-5">
			<span class="flex size-5 shrink-0 items-center justify-center rounded bg-muted/60">
				<TechIcon name={firstTech} class="size-3.5">
					{#snippet fallback()}
						<Globe class="size-3.5 text-muted-foreground" />
					{/snippet}
				</TechIcon>
			</span>
			<span class="min-w-0 font-mono text-sm font-medium break-all">
				<HighlightText text={node.name} {terms} />
			</span>
			<ArrowRight
				class="size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
			/>
		</div>
		{#if identity && (identity.status_code !== null || identity.title)}
			<div class="mt-0.5 ml-7 truncate text-xs text-muted-foreground">
				{#if identity.status_code !== null}
					<span class="font-mono tabular-nums">{identity.status_code}</span>
				{/if}
				{#if identity.title}
					<span class="text-muted-foreground/70"> · </span>{identity.title}
				{/if}
			</div>
		{/if}
		{#if node.chips.length}
			<div class="mt-1.5 ml-7 flex flex-wrap items-center gap-1">
				{#each node.chips as chip (chip.path)}
					<Hint text={chipHint(chip)}>
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="inline-flex h-5 items-center gap-1 rounded border px-1.5 font-mono text-[11px] leading-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {chipClass(
									chip
								)}"
								onclick={(e) => {
									stop(e);
									onEnterFolder(node.name, chip);
								}}
							>
								<HighlightText text={chip.name} {terms} />
								<span class="font-sans tabular-nums text-muted-foreground">
									{chip.count.toLocaleString()}
								</span>
							</button>
						{/snippet}
					</Hint>
				{/each}
				{#if moreFolders > 0}
					<span class="text-[11px] text-muted-foreground">+{moreFolders} folders</span>
				{/if}
			</div>
		{/if}
		{#if node.anomaly}
			<div class="mt-1 ml-7 flex items-center gap-1 text-[11px] text-warning">
				<TriangleAlert class="size-3" />
				{node.anomaly}
			</div>
		{/if}
	</div>

	<div class="{HOST_LEAD_COLUMNS[1].width} shrink-0 text-right">
		<div class="flex h-5 items-baseline justify-end gap-1.5 tabular-nums">
			<span class="text-sm font-semibold">{node.subtree_count.toLocaleString()}</span>
			{#if searching && node.unfiltered_count > node.subtree_count}
				<span class="text-xs text-muted-foreground"
					>of {node.unfiltered_count.toLocaleString()}</span
				>
			{:else if node.verified}
				<span class="text-xs text-muted-foreground">
					{node.verified.toLocaleString()} verified
				</span>
			{/if}
		</div>
		{#if node.verified > 0}
			<div class="mt-1.5 flex h-2 items-center">
				<StatusBar mix={verifiedMix} total={node.verified} />
			</div>
		{/if}
	</div>

	{#each columns as column (column.key)}
		<div class="{column.width} min-w-0 shrink-0 {column.align === 'right' ? 'text-right' : ''}">
			{#if column.key === 'input'}
				<span class="flex h-5 items-center justify-end text-sm tabular-nums">
					{#if node.params}{node.params.toLocaleString()}{:else}<span class="text-muted-foreground"
							>—</span
						>{/if}
				</span>
			{:else if column.key === 'api'}
				<span class="flex h-5 items-center justify-end text-sm tabular-nums">
					{#if node.api}{node.api.toLocaleString()}{:else}<span class="text-muted-foreground"
							>—</span
						>{/if}
				</span>
			{:else if column.key === 'why'}
				{#if why.length}
					<div class="flex min-h-5 flex-wrap items-center gap-1">
						{#each why as key (key)}
							<Badge variant={INTEREST_TONE[key] ?? 'warning'} class="h-4 px-1.5 text-[10px]">
								{INTEREST_LABELS[key] ?? key}
							</Badge>
						{/each}
					</div>
				{/if}
			{:else if column.key === 'new'}
				<span class="flex h-5 items-center justify-end text-sm tabular-nums">
					{#if node.new_count}
						<span class="font-medium text-success">+{node.new_count.toLocaleString()}</span>
					{:else}
						<span class="text-muted-foreground">—</span>
					{/if}
				</span>
			{:else if column.key === 'sources'}
				<SourceMarks sources={node.sources} />
			{/if}
		</div>
	{/each}

	<div class="{ACTIONS_PIN} {pinTone(false, focused)}">
		<div class={ACTIONS_BODY}>
			<Hint text="Copy every URL on this host">
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						onclick={(e) => {
							stop(e);
							onCopy(node);
						}}
					>
						<Copy class="size-3.5" />
					</Button>
				{/snippet}
			</Hint>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							aria-label="More actions"
							onclick={stop}
						>
							<Ellipsis class="size-3.5" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-60" onclick={stop}>
					<DropdownMenu.Item onclick={() => onEnter(node.name)}>
						<ArrowRight class="size-3.5" /> Open sitemap
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => onList(node)}>
						<Rows3 class="size-3.5" /> Show in list
					</DropdownMenu.Item>
					<DropdownMenu.Item>
						{#snippet child({ props })}
							<a {...props} href={openUrl} target="_blank" rel="noopener noreferrer">
								<ExternalLink class="size-3.5" /> Open in a new tab
							</a>
						{/snippet}
					</DropdownMenu.Item>
					{#if (onVerify && node.unprobed > 0) || (onSend && connectors.length)}
						<DropdownMenu.Separator />
					{/if}
					{#if onVerify && node.unprobed > 0}
						<DropdownMenu.Item onclick={() => onVerify(node)}>
							<ShieldCheck class="size-3.5" />
							Verify this host
							<span class="ml-auto text-xs tabular-nums text-muted-foreground">
								{node.unprobed.toLocaleString()} unchecked
							</span>
						</DropdownMenu.Item>
					{/if}
					{#if onSend}
						{#each connectors as c (c.id)}
							<DropdownMenu.Item onclick={() => onSend(node, c.id)}>
								<Send class="size-3.5" />
								Send to {proxyLabel(c, catalog)}
								{#if connectors.length > 1}
									<span class="ml-auto truncate text-xs text-muted-foreground">{c.name}</span>
								{/if}
							</DropdownMenu.Item>
						{/each}
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => onCopy(node)}>
						<Copy class="size-3.5" /> Copy URLs on this host
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => onWordlist(node)}>
						<ListOrdered class="size-3.5" /> Copy paths as wordlist
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
