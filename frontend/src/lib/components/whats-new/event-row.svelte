<script lang="ts">
	import Award from '@lucide/svelte/icons/award';
	import Library from '@lucide/svelte/icons/library';
	import Target from '@lucide/svelte/icons/target';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ItemRow from './item-row.svelte';
	import SevCounts from './sev-counts.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { getTargetTypeIcon } from '$lib/config/icons';
	import { SEVERITY_CHIP, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import {
		KIND_NOUN,
		NEW_FINDINGS_QUERY,
		NewKind,
		RUN_VERBS,
		SELECTABLE_KINDS,
		SubjectKind,
		type NewKindKey
	} from '$lib/config/whats-new';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import type { ScanStatus } from '$lib/types/scan';
	import type { TargetType } from '$lib/types/target';
	import type { NewGroup, NewItem } from '$lib/types/whats-new';

	interface Props {
		group: NewGroup;
		index: number;
		cursor: boolean;
		unseen: boolean;
		expanded: boolean;
		isChecked: (id: string) => boolean;
		isBusy: (id: string) => boolean;
		addingAll?: boolean;
		onToggle: () => void;
		onPick: (index: number) => void;
		onCompare: (current: string, baseline: string) => void;
		onAddTargets: (items: NewItem[]) => void;
		onOpen: (item: NewItem) => void;
		onCheck: (item: NewItem, shift: boolean) => void;
		onAddTarget: (item: NewItem) => void;
		onWatch: (item: NewItem) => void;
		onMute: (item: NewItem) => void;
		onScan: (item: NewItem) => void;
		onRemoveTarget: (item: NewItem) => void;
	}

	let {
		group,
		index,
		cursor,
		unseen,
		expanded,
		isChecked,
		isBusy,
		addingAll = false,
		onToggle,
		onPick,
		onCompare,
		onAddTargets,
		onOpen,
		onCheck,
		onAddTarget,
		onWatch,
		onMute,
		onScan,
		onRemoveTarget
	}: Props = $props();

	const PREVIEW = 3;
	const SHEET_KINDS = new Set<string>([NewKind.CERT_HOST]);
	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];

	let subject = $derived(group.subject);
	let isRun = $derived(subject.kind === SubjectKind.RUN && !!group.scan_id);
	let items = $derived(group.sections.flatMap((s) => s.items));
	let shown = $derived(expanded ? items : items.slice(0, PREVIEW));
	let hiddenItems = $derived(group.sections.reduce((n, s) => n + s.total, 0) - shown.length);
	let addable = $derived(
		items.filter((i) => i.kind === NewKind.SCOPE && i.importable && !i.target_exists)
	);
	let found = $derived(group.counts[NewKind.FINDING] ?? 0);
	let status = $derived(
		group.scan_status && group.scan_status !== 'completed'
			? (RUN_VERBS[group.scan_status as ScanStatus] ?? group.scan_status)
			: null
	);
	let time = $derived(
		new Date(group.at).toLocaleTimeString('en-US', {
			hour: '2-digit',
			minute: '2-digit',
			hour12: false
		})
	);
	let Icon = $derived(
		isRun && subject.target_type
			? getTargetTypeIcon(subject.target_type as TargetType)
			: subject.kind === SubjectKind.PROGRAM
				? Award
				: subject.kind === SubjectKind.TARGETS
					? Target
					: Library
	);
	let programHref = $derived(
		subject.handle ? ROUTES.bountyHub(subject.handle, subject.platform ?? undefined) : null
	);
	let headline = $derived.by(() => {
		if (subject.kind === SubjectKind.LIBRARY) {
			const n = group.counts[NewKind.PROGRAM] ?? 0;
			return n === 1 && items[0] ? `New program: ${items[0].value}` : `${n} new programs`;
		}
		if (subject.kind === SubjectKind.TARGETS) {
			const n = group.counts[NewKind.TARGET] ?? 0;
			return `${n} ${n === 1 ? 'target' : 'targets'} added from program scope`;
		}
		return subject.label;
	});

	function vulnsHref(query: string): string {
		return ROUTES.scanTab(group.scan_id ?? '', VULNS.tab, { [VULNS.queryParam]: query });
	}
	function sentence(kind: string, n: number): string {
		if (kind === NewKind.SCOPE) return `${n} ${n === 1 ? 'asset' : 'assets'} added to scope`;
		if (kind === NewKind.OUT_OF_SCOPE) return `${n} ${n === 1 ? 'asset' : 'assets'} left scope`;
		if (kind === NewKind.CERT_HOST)
			return `${n} new ${n === 1 ? 'host' : 'hosts'} in certificate logs`;
		if (kind === NewKind.BOUNTY_TABLE)
			return n === 1 ? 'Bounty table changed' : `${n} bounty changes`;
		if (kind === NewKind.RULES) return n === 1 ? 'Rules changed' : `${n} rule changes`;
		return `${n} ${KIND_NOUN[kind as NewKindKey]?.[n === 1 ? 0 : 1] ?? ''}`;
	}
	function stop(e: Event) {
		e.stopPropagation();
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
<li
	class="grid grid-cols-[3rem_1rem_minmax(0,1fr)] gap-x-3 px-4 transition-colors hover:bg-muted/20 sm:grid-cols-[3rem_1rem_minmax(0,1fr)_auto] {cursor
		? 'bg-muted/40'
		: ''}"
	data-event-row={index}
	onclick={() => onPick(index)}
>
	<span class="flex h-6 items-center pt-3 font-mono text-xs text-muted-foreground tabular-nums">
		{time}
	</span>

	<span class="relative flex justify-center">
		<span class="absolute inset-y-0 w-px bg-border"></span>
		<span class="relative mt-3 flex h-6 items-center">
			<span
				class="size-2.5 rounded-full {unseen
					? 'bg-foreground'
					: 'border-2 border-muted-foreground/50 bg-card'}"
			></span>
		</span>
	</span>

	<div class="flex min-w-0 flex-col gap-1.5 py-3">
		<div class="flex min-h-6 min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm">
			<Icon class="size-3.5 shrink-0 text-muted-foreground" />
			{#if isRun}
				<span class="text-muted-foreground">Rescan of</span>
				<a
					href={ROUTES.target(subject.target_id ?? '')}
					class="font-mono font-medium wrap-anywhere hover:underline"
					onclick={stop}>{subject.label}</a
				>
				<a
					href={vulnsHref(NEW_FINDINGS_QUERY)}
					class="inline-flex items-center gap-1.5 hover:underline"
					onclick={stop}
				>
					<SevCounts severities={group.severities} labelled />
					<span class="text-muted-foreground">new {found === 1 ? 'finding' : 'findings'}</span>
				</a>
				{#if status}<span class="text-xs text-warning">Run {status}</span>{/if}
			{:else}
				<span class="font-medium wrap-anywhere">{headline}</span>
				{#if subject.platform}
					<Badge variant="outline">{bountyVocabulary.label(subject.platform)}</Badge>
				{/if}
				{#if subject.watched}<Badge variant="info">Watched</Badge>{/if}
			{/if}
		</div>

		{#if isRun}
			{#if group.evidence.length}
				<ul class="flex flex-col gap-1">
					{#each group.evidence as e (e.query)}
						<li>
							<a
								href={vulnsHref(e.query)}
								class="flex min-w-0 items-center gap-2 text-xs hover:underline"
								onclick={stop}
							>
								{#if e.severity && SEVERITY_CHIP[e.severity]}
									<span
										class="inline-flex h-5 w-16 shrink-0 items-center justify-center rounded px-1 text-2xs font-medium {SEVERITY_CHIP[
											e.severity
										].chip}">{SEVERITY_LABELS[e.severity]}</span
									>
								{/if}
								<span class="min-w-0 wrap-anywhere">{e.label}</span>
								{#if e.kev}<Badge variant="destructive">KEV</Badge>{/if}
								<span class="shrink-0 font-mono text-muted-foreground tabular-nums">
									{e.count.toLocaleString()}
									{e.count === 1 ? 'instance' : 'instances'}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
			{#if group.more}
				<a
					href={vulnsHref(NEW_FINDINGS_QUERY)}
					class="w-fit text-xs text-muted-foreground hover:text-foreground hover:underline"
					onclick={stop}
				>
					{group.more} more {group.more === 1 ? 'check' : 'checks'}
				</a>
			{/if}
		{:else}
			{#if subject.kind === SubjectKind.PROGRAM}
				<span class="text-xs text-muted-foreground">
					{group.sections.map((s) => sentence(s.kind, s.total)).join(' · ')}
				</span>
			{/if}
			{#if shown.length}
				<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
				<div class="divide-y divide-border/50 rounded-md border bg-card" onclick={stop}>
					{#each shown as item (item.id)}
						<ItemRow
							{item}
							index={-1}
							checked={isChecked(item.id)}
							selectable={SELECTABLE_KINDS.has(item.kind)}
							busy={isBusy(item.id)}
							showTime={false}
							sheet={SHEET_KINDS.has(item.kind) && !!item.scan_id}
							{onOpen}
							{onCheck}
							{onAddTarget}
							{onWatch}
							{onMute}
							{onScan}
							{onRemoveTarget}
						/>
					{/each}
				</div>
			{/if}
			{#if hiddenItems > 0 || (expanded && items.length > PREVIEW)}
				<button
					type="button"
					class="w-fit text-xs text-muted-foreground hover:text-foreground"
					onclick={(e) => {
						stop(e);
						onToggle();
					}}
				>
					{expanded ? 'Show less' : `${hiddenItems.toLocaleString()} more`}
				</button>
			{/if}
		{/if}
	</div>

	<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
	<div
		class="col-start-3 flex items-start gap-1 pb-3 sm:col-start-auto sm:justify-end sm:pt-3 sm:pb-0"
		onclick={stop}
	>
		{#if isRun}
			<Button
				variant="outline"
				size="sm"
				class="h-7 px-2.5 text-xs"
				href={vulnsHref(NEW_FINDINGS_QUERY)}
			>
				Triage
			</Button>
			{#if group.previous_scan_id}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 px-2 text-xs"
					onclick={() => onCompare(group.scan_id ?? '', group.previous_scan_id ?? '')}
				>
					Compare
				</Button>
			{/if}
		{:else if addable.length}
			<LoadingButton
				size="sm"
				class="h-7 px-2.5 text-xs"
				loading={addingAll}
				loadingLabel="Adding"
				onclick={() => onAddTargets(addable)}
			>
				{addable.length === 1 ? 'Add target' : `Add ${addable.length} targets`}
			</LoadingButton>
		{:else if programHref}
			<Button variant="outline" size="sm" class="h-7 px-2.5 text-xs" href={programHref}>
				Program
			</Button>
		{:else if subject.kind === SubjectKind.LIBRARY}
			<Button
				variant="outline"
				size="sm"
				class="h-7 px-2.5 text-xs"
				href={ROUTES.bountyHubTab('updates')}
			>
				Bounty Hub
			</Button>
		{/if}
	</div>
</li>
