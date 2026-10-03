<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { compareApi } from '$lib/api/compare';
	import ChangeBar from '$lib/components/scans/compare/change-bar.svelte';
	import { COMPARABILITY_LABEL } from '$lib/config/compare';
	import { ROUTES } from '$lib/config/routes';
	import { COMPARABILITY, type RunSide, type ScanComparison } from '$lib/types/compare';
	import { formatDateTime } from '$lib/utilities/dates';
	import { SCAN_STATUS_LABEL, formatSeconds } from '$lib/utilities/scan-status';
	import type { ScanStatus } from '$lib/types/scan';

	interface Props {
		projectId: string;
		current: string | null;
		baseline: string | null;
		onClose: () => void;
	}

	let { projectId, current, baseline, onClose }: Props = $props();

	let data = $state<ScanComparison | null>(null);
	let failed = $state(false);
	let error = $state<string | undefined>(undefined);
	let attempt = $state(0);

	$effect(() => {
		const c = current;
		const b = baseline;
		void attempt;
		if (!c) return;
		let live = true;
		data = null;
		failed = false;
		error = undefined;
		compareApi
			.comparison(projectId, c, b)
			.then((r) => {
				if (live) data = r;
			})
			.catch((e) => {
				if (!live) return;
				failed = true;
				error = e instanceof Error ? e.message : undefined;
			});
		return () => {
			live = false;
		};
	});

	const n = (v: number) => v.toLocaleString();
	const delta = (a: number, b: number) =>
		b - a > 0 ? `+${n(b - a)}` : b - a < 0 ? `−${n(a - b)}` : '0';
	const side = (r: RunSide) =>
		`${r.engine_name} · ${r.started_at ? formatDateTime(r.started_at) : 'not started'} · ${SCAN_STATUS_LABEL[r.status as ScanStatus]}${r.duration_seconds != null ? ` · ${formatSeconds(r.duration_seconds)}` : ''}`;
</script>

<Sheet.Root open={!!current} onOpenChange={(o) => !o && onClose()}>
	<Sheet.Content side="bottom" class="max-h-[70vh] gap-0 bg-card">
		<Sheet.Header class="border-b pb-3">
			<Sheet.Title class="flex flex-wrap items-center gap-2 text-base">
				Compare runs
				{#if data}
					<span class="font-mono text-sm font-normal text-muted-foreground"
						>{data.target_value}</span
					>
					<span
						class="rounded border px-1.5 py-0.5 text-2xs font-normal {data.comparability ===
						COMPARABILITY.LIKE_FOR_LIKE
							? 'border-border text-muted-foreground'
							: 'border-warning/40 text-warning'}">{COMPARABILITY_LABEL[data.comparability]}</span
					>
				{/if}
			</Sheet.Title>
			<Sheet.Description>{data?.headline ?? ''}</Sheet.Description>
		</Sheet.Header>
		<ScrollArea class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(70vh-9rem)]">
			<div class="px-4 py-3">
				{#if failed}
					<EmptyState
						compact
						icon={TriangleAlert}
						title="Comparison not loaded"
						description={error}
					>
						<Button size="sm" variant="outline" onclick={() => attempt++}>Retry</Button>
					</EmptyState>
				{:else if !data}
					<div class="space-y-2">
						{#each { length: 5 } as _, i (i)}<Skeleton class="h-6 rounded" />{/each}
					</div>
				{:else}
					{@const material = data.run_diff.filter((d) => d.material)}
					{#if material.length}
						<div class="mb-3 rounded-md border border-warning/30 bg-warning/5 px-3 py-2 text-xs">
							{#each material as d (d.key)}
								<div>
									<span class="font-medium">{d.label}:</span>
									{d.baseline ?? 'none'} → {d.current ?? 'none'}
								</div>
							{/each}
						</div>
					{/if}
					<div class="mb-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
						<div>
							<span class="font-medium text-foreground">Earlier</span> · {side(data.baseline)}
						</div>
						<div><span class="font-medium text-foreground">Later</span> · {side(data.current)}</div>
					</div>
					<ScrollArea orientation="horizontal">
						<table class="w-full min-w-[560px] text-xs">
							<thead>
								<tr class="text-left text-2xs tracking-wide text-muted-foreground uppercase">
									<th class="py-1.5 pr-3 font-medium">Dimension</th>
									<th class="py-1.5 pr-3 text-right font-medium">Earlier</th>
									<th class="py-1.5 pr-3 text-right font-medium">Later</th>
									<th class="py-1.5 pr-3 text-right font-medium">Delta</th>
									<th class="w-40 py-1.5 pr-3 font-medium"></th>
									<th class="py-1.5 font-medium">Note</th>
								</tr>
							</thead>
							<tbody>
								{#each data.dimensions as d (d.dimension)}
									<tr class="border-t border-border/50">
										<td class="py-1.5 pr-3">{d.label}</td>
										<td class="py-1.5 pr-3 text-right font-mono tabular-nums text-muted-foreground"
											>{d.verdict.covered_baseline ? n(d.total_baseline) : 'Not scanned'}</td
										>
										<td class="py-1.5 pr-3 text-right font-mono tabular-nums"
											>{d.verdict.covered_current ? n(d.total_current) : 'Not scanned'}</td
										>
										<td class="py-1.5 pr-3 text-right font-mono font-semibold tabular-nums"
											>{d.verdict.covered_baseline && d.verdict.covered_current
												? delta(d.total_baseline, d.total_current)
												: ''}</td
										>
										<td class="py-1.5 pr-3"><ChangeBar delta={d} /></td>
										<td class="py-1.5 text-2xs text-muted-foreground">
											{d.verdict.comparability === COMPARABILITY.LIKE_FOR_LIKE
												? ''
												: d.verdict.note}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</ScrollArea>
				{/if}
			</div>
		</ScrollArea>
		{#if data}
			<Sheet.Footer class="flex-row justify-end border-t py-3">
				<Button
					size="sm"
					class="gap-1.5"
					href={ROUTES.compare(data.current.scan_id, data.baseline.scan_id)}
				>
					Open comparison <ExternalLink class="size-3.5" />
				</Button>
			</Sheet.Footer>
		{/if}
	</Sheet.Content>
</Sheet.Root>
