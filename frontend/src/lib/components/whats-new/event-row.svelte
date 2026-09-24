<script lang="ts">
	import Award from '@lucide/svelte/icons/award';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Library from '@lucide/svelte/icons/library';
	import Target from '@lucide/svelte/icons/target';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ItemRow from './item-row.svelte';
	import RunFindings from './run-findings.svelte';
	import SevCounts from './sev-counts.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { getTargetTypeIcon } from '$lib/config/icons';
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
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import type { NewGroup, NewItem } from '$lib/types/whats-new';

	interface Props {
		group: NewGroup;
		projectId: string;
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
		onFinding: (vuln: VulnerabilityRead, scanId: string) => void;
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
		projectId,
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
		onFinding,
		onAddTargets,
		onOpen,
		onCheck,
		onAddTarget,
		onWatch,
		onMute,
		onScan,
		onRemoveTarget
	}: Props = $props();

	const SUMMARY_NAMES = 3;
	const SHEET_KINDS = new Set<string>([NewKind.CERT_HOST]);
	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];

	let subject = $derived(group.subject);
	let isRun = $derived(subject.kind === SubjectKind.RUN && !!group.scan_id);
	let items = $derived(group.sections.flatMap((s) => s.items));
	let total = $derived(group.sections.reduce((n, s) => n + s.total, 0));
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
	let summary = $derived.by(() => {
		if (isRun) {
			const names = group.evidence.map((e) => e.label);
			const more = names.length + group.more - SUMMARY_NAMES;
			return [
				...names.slice(0, SUMMARY_NAMES),
				...(more > 0 ? [`${more} more ${more === 1 ? 'check' : 'checks'}`] : [])
			].join(' · ');
		}
		if (subject.kind === SubjectKind.PROGRAM) {
			return group.sections.map((s) => sentence(s.kind, s.total)).join(' · ');
		}
		const names = items.slice(0, SUMMARY_NAMES).map((i) => i.value);
		const more = total - names.length;
		return [...names, ...(more > 0 ? [`${more.toLocaleString()} more`] : [])].join(' · ');
	});

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

<li
	class="group/ev grid grid-cols-[1rem_minmax(0,1fr)] gap-x-3 px-4 transition-colors sm:grid-cols-[3rem_1rem_minmax(0,1fr)_auto] {cursor
		? 'bg-muted/40'
		: expanded
			? 'bg-muted/20'
			: 'hover:bg-muted/30'}"
	data-event-row={index}
>
	<span
		class="hidden h-6 items-center pt-3 font-mono text-xs text-muted-foreground tabular-nums sm:flex"
	>
		{time}
	</span>

	<span class="relative row-span-3 flex justify-center">
		<span class="absolute inset-y-0 w-px bg-border"></span>
		<span class="relative mt-3 flex h-6 items-center">
			<span
				class="size-2.5 rounded-full {unseen
					? 'bg-foreground'
					: 'border-2 border-muted-foreground/50 bg-card'}"
			></span>
		</span>
	</span>

	<div class="flex min-w-0 flex-col gap-2 py-3">
		<button
			type="button"
			class="flex min-w-0 flex-col gap-1 rounded-sm text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			aria-expanded={expanded}
			onclick={() => {
				onPick(index);
				onToggle();
			}}
		>
			<span class="flex min-h-6 min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm">
				<ChevronRight
					class="size-3.5 shrink-0 text-muted-foreground transition-transform {expanded
						? 'rotate-90'
						: ''}"
				/>
				<Icon class="size-3.5 shrink-0 text-muted-foreground" />
				<span class="font-mono text-xs text-muted-foreground tabular-nums sm:hidden">{time}</span>
				{#if isRun}
					<span class="text-muted-foreground">Rescan of</span>
					<span class="font-mono font-medium wrap-anywhere">{subject.label}</span>
					<SevCounts severities={group.severities} labelled />
					<span class="text-muted-foreground">new {found === 1 ? 'finding' : 'findings'}</span>
					{#if status}<span class="text-xs text-muted-foreground">Run {status}</span>{/if}
				{:else}
					<span class="font-medium wrap-anywhere">{headline}</span>
					{#if subject.platform}
						<Badge variant="outline">{bountyVocabulary.label(subject.platform)}</Badge>
					{/if}
					{#if subject.watched}<Badge variant="info">Watched</Badge>{/if}
				{/if}
			</span>
			{#if summary && !expanded}
				<span class="pl-[1.375rem] text-xs text-muted-foreground wrap-anywhere">{summary}</span>
			{/if}
		</button>
	</div>

	<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
	<div
		class="col-start-2 flex items-start gap-1 pb-3 transition-opacity sm:col-start-auto sm:justify-end sm:pt-3 sm:pb-0 sm:opacity-0 sm:group-hover/ev:opacity-100 sm:focus-within:opacity-100 {cursor ||
		expanded
			? 'sm:opacity-100'
			: ''}"
		onclick={stop}
	>
		{#if isRun && group.scan_id}
			<Button
				variant="outline"
				size="sm"
				class="h-7 px-2.5 text-xs"
				href={ROUTES.scanTab(group.scan_id, VULNS.tab, { [VULNS.queryParam]: NEW_FINDINGS_QUERY })}
			>
				Open in scan
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
	{#if expanded}
		<div class="col-start-2 min-w-0 pb-3 sm:col-start-3 sm:col-end-5 flex flex-col gap-2">
			{#if isRun && group.scan_id}
				<RunFindings
					{projectId}
					scanId={group.scan_id}
					count={found}
					onOpen={(v) => onFinding(v, group.scan_id ?? '')}
				/>
			{:else if items.length}
				<div class="divide-y divide-border/50 overflow-clip rounded-md border bg-card">
					{#each items as item (item.id)}
						<ItemRow
							{item}
							checked={isChecked(item.id)}
							selectable={SELECTABLE_KINDS.has(item.kind)}
							busy={isBusy(item.id)}
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
				{#if total > items.length}
					<span class="text-xs text-muted-foreground">
						{items.length} of {total.toLocaleString()} shown
					</span>
				{/if}
			{/if}
		</div>
	{/if}
</li>
