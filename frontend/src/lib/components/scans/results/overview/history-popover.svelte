<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Popover from '$lib/components/ui/popover';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { durationText, isLiveStatus, SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import { ROUTES } from '$lib/config/routes';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		history: ScanRead[];
		current: ScanRead;
		nounPlural: string;
	}

	let { history, current, nounPlural }: Props = $props();

	const GRID =
		'grid grid-cols-[minmax(0,1fr)_6rem] items-center gap-x-4 sm:grid-cols-[minmax(0,1fr)_6rem_5.5rem_5.5rem_5.5rem]';
	const fmt = (iso: string) =>
		new Date(iso).toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	const startedAt = (s: ScanRead) => new Date(s.started_at ?? s.created_at).getTime();

	let open = $state(false);
	let currentEl = $state<HTMLElement | null>(null);
	let target = $derived(current.execution_config.target_value);
	let nounTitle = $derived(nounPlural.charAt(0).toUpperCase() + nounPlural.slice(1));
	let description = $derived(`${history.length} scans of ${target}`);
	let currentAt = $derived(startedAt(current));
	let later = $derived(history.filter((s) => s.id !== current.id && startedAt(s) > currentAt));
	let earlier = $derived(history.filter((s) => s.id !== current.id && startedAt(s) <= currentAt));
	let selected = $derived(history.find((s) => s.id === current.id) ?? current);

	$effect(() => {
		if (open) currentEl?.scrollIntoView({ block: 'nearest' });
	});
</script>

{#snippet row(s: ScanRead, isCurrent: boolean)}
	{@const added =
		s.status === 'completed' && s.is_first_scan !== true ? (s.new_subdomains ?? 0) : 0}
	{@const dur =
		s.duration_seconds != null && !isLiveStatus(s.status) ? durationText(s.duration_seconds) : null}
	{@const state = s.status === 'completed' ? null : SCAN_STATUS_LABEL[s.status]}
	<span class="flex min-w-0 flex-col">
		<span class="flex items-center gap-1.5">
			<span class="truncate text-sm leading-5 {isCurrent ? 'font-medium' : ''}">
				{s.engine_name}
			</span>
			{#if isCurrent}
				<Badge class="h-4 px-1.5 text-[10px] font-normal">This scan</Badge>
			{/if}
		</span>
		<span class="truncate text-xs leading-4 text-muted-foreground">
			{[fmt(s.started_at ?? s.created_at), dur].filter(Boolean).join(' · ')}
			{#if state}
				· <span class={s.status === 'failed' ? 'text-destructive' : ''}>{state}</span>
			{/if}
		</span>
	</span>
	<span class="flex items-center justify-end gap-1.5 text-sm tabular-nums">
		<span class="font-medium">{s.subdomains_found.toLocaleString()}</span>
		{#if added > 0}
			<span class="inline-flex items-center text-xs text-success">
				<ArrowUpRight class="size-3" />{added}
			</span>
		{/if}
	</span>
	<span class="hidden text-right text-sm tabular-nums sm:block">
		{s.http_assets_found.toLocaleString()}
	</span>
	<span class="hidden text-right text-sm tabular-nums sm:block">{s.ips_found.toLocaleString()}</span
	>
	<span class="hidden text-right text-sm tabular-nums sm:block">
		{s.open_ports_found.toLocaleString()}
	</span>
{/snippet}

{#snippet group(label: string, scans: ScanRead[])}
	{#if scans.length}
		<li class="px-2.5 pt-2 pb-1 text-[11px] text-muted-foreground">{label}</li>
		{#each scans as s (s.id)}
			<li>
				<a
					href={ROUTES.scan(s.id)}
					class="{GRID} rounded-md px-2.5 py-2 transition-colors hover:bg-muted/50"
				>
					{@render row(s, false)}
				</a>
			</li>
		{/each}
	{/if}
{/snippet}

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				type="button"
				class="inline-flex h-6 items-center gap-2 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60 data-[state=open]:border-primary/40 data-[state=open]:bg-accent/60"
				aria-label="Scan history, {history.length} scans"
			>
				Scan history
				<span class="text-muted-foreground tabular-nums">{history.length}</span>
				<ChevronDown class="size-3 text-muted-foreground" />
			</button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content align="start" class="w-[44rem] max-w-[calc(100vw-2rem)] p-0">
		<PanelHead title="Scan history" {description} />
		<div class="flex flex-col p-2">
			<div class="{GRID} px-2.5 pt-1 pb-2 text-xs text-muted-foreground">
				<span>Scan</span>
				<span class="text-right">{nounTitle}</span>
				<span class="hidden text-right sm:block">HTTP services</span>
				<span class="hidden text-right sm:block">IP addresses</span>
				<span class="hidden text-right sm:block">Open ports</span>
			</div>
			<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
				<ul class="flex flex-col gap-0.5">
					{@render group('Later scans', later)}
					<li>
						<div
							bind:this={currentEl}
							class="{GRID} relative rounded-md bg-muted/60 px-2.5 py-2 before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-primary before:content-['']"
						>
							{@render row(selected, true)}
						</div>
					</li>
					{@render group('Earlier scans', earlier)}
				</ul>
			</ScrollArea>
			<Button
				variant="link"
				size="sm"
				class="mt-2 h-auto gap-1 self-start px-2.5 text-xs"
				href={ROUTES.target(current.target_id)}
			>
				View all scans <ChevronRight class="size-3.5" />
			</Button>
		</div>
	</Popover.Content>
</Popover.Root>
