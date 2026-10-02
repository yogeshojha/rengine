<script lang="ts">
	import { untrack } from 'svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Badge } from '$lib/components/ui/badge';
	import SectionHead from '$lib/components/section-head.svelte';
	import { tripwiresApi } from '$lib/api/tripwires';
	import {
		CHECK_STATUS_VARIANT,
		CheckStatus,
		FIRE_ON_VERB,
		FireOn,
		checkStatusLabel,
		dimensionSpec
	} from '$lib/config/tripwires';
	import type { QueryError } from '$lib/types/asset-query';
	import type { TripwirePreview, TripwirePreviewRequest } from '$lib/types/tripwire';

	interface Props {
		projectId: string;
		request: TripwirePreviewRequest;
		enabled?: boolean;
		onError?: (error: QueryError | null) => void;
		onBusy?: (busy: boolean) => void;
	}

	let { projectId, request, enabled = true, onError, onBusy }: Props = $props();

	const DEBOUNCE_MS = 500;
	const SHOWN_TARGETS = 6;
	const SHOWN_ROWS = 6;

	let preview = $state<TripwirePreview | null>(null);
	let loading = $state(false);
	let seq = 0;

	let spec = $derived(dimensionSpec(request.dimension));
	let verb = $derived(FIRE_ON_VERB[request.fire_on as FireOn] ?? 'fired');
	let signature = $derived(JSON.stringify(request));
	let noun = $derived((n: number) => (n === 1 ? spec.noun : spec.nounPlural));
	let count = $derived((n: number, capped: boolean) => `${n.toLocaleString()}${capped ? '+' : ''}`);

	$effect(() => {
		void signature;
		const on = enabled;
		untrack(() => {
			if (!on) {
				preview = null;
				return;
			}
			const mine = ++seq;
			loading = true;
			onBusy?.(true);
			const timer = setTimeout(async () => {
				try {
					const result = await tripwiresApi.preview(projectId, request);
					if (mine !== seq) return;
					preview = result;
					onError?.(result.error);
				} catch {
					if (mine !== seq) return;
					preview = null;
				} finally {
					if (mine === seq) {
						loading = false;
						onBusy?.(false);
					}
				}
			}, DEBOUNCE_MS);
			return () => {
				clearTimeout(timer);
				if (mine === seq) onBusy?.(false);
			};
		});
	});
</script>

<div class="flex flex-col gap-3 rounded-lg border bg-muted/20 p-4">
	<SectionHead title="Latest run per target" />
	{#if !enabled}
		<p class="text-xs text-muted-foreground">Not evaluated until the query is valid.</p>
	{:else if loading && !preview}
		<Skeleton class="h-4 w-40" />
		<Skeleton class="h-4 w-full" />
		<Skeleton class="h-4 w-2/3" />
	{:else if preview?.error}
		<p class="text-xs text-destructive">{preview.error.message}</p>
	{:else if preview}
		<p class="text-sm">
			<span class="font-semibold tabular-nums">{count(preview.fired, preview.capped)}</span>
			<span class="text-muted-foreground">
				{noun(preview.fired)} would have {verb} · {count(preview.matched, preview.capped)} matching{#if preview.scanned > preview.targets.length}
					· {preview.targets.length} of {preview.scanned} targets{/if}
			</span>
		</p>
		{#if preview.targets.length === 0}
			<p class="text-xs text-muted-foreground">No settled scan in scope.</p>
		{:else}
			<div class="grid gap-3 sm:grid-cols-2">
				<div class="flex flex-col divide-y divide-border/60 rounded-md border bg-background">
					{#each preview.targets.slice(0, SHOWN_TARGETS) as row (row.scan_id)}
						<div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-2.5 py-1.5">
							<span class="truncate font-mono text-2xs">{row.target_value}</span>
							{#if row.status === CheckStatus.Fired || row.status === CheckStatus.Quiet}
								<span class="text-2xs text-muted-foreground tabular-nums">
									{count(row.fired, row.capped)} of {count(row.matched, row.capped)}
								</span>
							{:else}
								<Badge
									variant={CHECK_STATUS_VARIANT[row.status as CheckStatus] ?? 'outline'}
									class="text-2xs"
								>
									{checkStatusLabel(row.status)}
								</Badge>
							{/if}
						</div>
					{/each}
					{#if preview.targets.length > SHOWN_TARGETS}
						<div class="px-2.5 py-1.5 text-2xs text-muted-foreground">
							and {preview.targets.length - SHOWN_TARGETS} more
						</div>
					{/if}
				</div>
				<div class="flex min-w-0 flex-col gap-1.5">
					{#each preview.rows.slice(0, SHOWN_ROWS) as row, i (i)}
						<div class="flex min-w-0 flex-col">
							<span class="truncate font-mono text-2xs">{row.label}</span>
							{#if row.detail}
								<span class="truncate text-2xs text-muted-foreground">{row.detail}</span>
							{/if}
						</div>
					{/each}
					{#if preview.rows.length === 0}
						<span class="text-2xs text-muted-foreground">No row {verb}</span>
					{/if}
				</div>
			</div>
		{/if}
		{#if preview.unscanned > 0}
			<p class="text-xs text-muted-foreground">
				{preview.unscanned}
				{preview.unscanned === 1 ? 'target' : 'targets'} not scanned
			</p>
		{/if}
	{/if}
</div>
