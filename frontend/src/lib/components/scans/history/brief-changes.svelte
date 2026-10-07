<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { compareApi } from '$lib/api/compare';
	import ChangeBar from '$lib/components/scans/compare/change-bar.svelte';
	import { COMPARABILITY_LABEL } from '$lib/config/compare';
	import { ROUTES } from '$lib/config/routes';
	import { COMPARABILITY, type ScanComparison } from '$lib/types/compare';
	import { formatDateTime } from '$lib/utilities/dates';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import type { ScanRead, ScanStatus } from '$lib/types/scan';

	interface Props {
		projectId: string;
		scan: ScanRead;
	}

	let { projectId, scan }: Props = $props();

	let data = $state<ScanComparison | null>(null);
	let error = $state<string | null>(null);
	let baseline = $state<string | null>(null);
	let attempt = $state(0);

	$effect(() => {
		const id = scan.id;
		const against = baseline;
		void attempt;
		if (scan.is_first_scan) return;
		let live = true;
		data = null;
		error = null;
		compareApi
			.comparison(projectId, id, against)
			.then((c) => {
				if (live) data = c;
			})
			.catch((e) => {
				if (live) error = e instanceof Error ? e.message : 'Comparison not loaded.';
			});
		return () => {
			live = false;
		};
	});

	const n = (v: number) => v.toLocaleString();
</script>

{#if scan.is_first_scan}
	<p class="px-1 py-6 text-sm text-muted-foreground">First run</p>
{:else if error}
	<div class="flex items-center gap-3 px-1 py-6 text-sm text-muted-foreground">
		<span>{error}</span>
		<button type="button" class="text-primary hover:text-primary/80" onclick={() => attempt++}>
			Retry
		</button>
	</div>
{:else if !data}
	<div class="space-y-2 py-3">
		{#each { length: 4 } as _, i (i)}
			<Skeleton class="h-7 rounded" />
		{/each}
	</div>
{:else}
	<div class="flex flex-col gap-3 py-2">
		<div class="flex flex-wrap items-baseline justify-between gap-2 px-1">
			<div class="min-w-0">
				<div class="text-sm font-medium">{data.headline}</div>
				<div class="text-xs text-muted-foreground">
					Against {data.baseline.engine_name}
					{#if data.baseline.started_at}· {formatDateTime(data.baseline.started_at)}{/if}
					· {SCAN_STATUS_LABEL[data.baseline.status as ScanStatus]}
				</div>
			</div>
			<span
				class="rounded border px-1.5 py-0.5 text-2xs {data.comparability ===
				COMPARABILITY.LIKE_FOR_LIKE
					? 'border-border text-muted-foreground'
					: 'border-warning/40 text-warning'}"
			>
				{COMPARABILITY_LABEL[data.comparability]}
			</span>
		</div>
		{#if data.suggestion}
			<div
				class="flex flex-wrap items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs"
			>
				<span class="text-muted-foreground">
					Comparable run: {data.suggestion.engine_name}{data.suggestion.started_at
						? ` · ${formatDateTime(data.suggestion.started_at)}`
						: ''}
				</span>
				<button
					type="button"
					class="font-medium text-primary hover:text-primary/80"
					onclick={() => (baseline = data?.suggestion?.scan_id ?? null)}
				>
					Compare with this run
				</button>
			</div>
		{/if}
		{#if data.run_diff.some((d) => d.material)}
			<div class="rounded-md border border-warning/30 bg-warning/5 px-3 py-2 text-xs">
				{#each data.run_diff.filter((d) => d.material) as d (d.key)}
					<div>
						<span class="font-medium">{d.label}:</span>
						{d.baseline ?? 'none'} → {d.current ?? 'none'}
					</div>
				{/each}
			</div>
		{/if}
		<Table.Root class="min-w-[520px] text-xs">
			<Table.Header>
				<Table.Row>
					<Table.Head>Dimension</Table.Head>
					<Table.Head class="w-40"><span class="sr-only">Change</span></Table.Head>
					<Table.Head class="text-right">Appeared</Table.Head>
					<Table.Head class="text-right">Changed</Table.Head>
					<Table.Head class="text-right">Gone</Table.Head>
					<Table.Head class="text-right">Now</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each data.dimensions as d (d.dimension)}
					<Table.Row>
						<Table.Cell class="whitespace-normal">
							<a href={ROUTES.compare(scan.id, data.baseline.scan_id)} class="hover:text-primary"
								>{d.label}</a
							>
							{#if d.verdict.comparability !== COMPARABILITY.LIKE_FOR_LIKE}
								<div class="text-2xs text-muted-foreground">{d.verdict.note}</div>
							{/if}
						</Table.Cell>
						<Table.Cell><ChangeBar delta={d} /></Table.Cell>
						<Table.Cell
							class="text-right font-mono tabular-nums {d.appeared
								? 'font-semibold'
								: 'text-muted-foreground'}">{d.appeared ? `+${n(d.appeared)}` : '0'}</Table.Cell
						>
						<Table.Cell class="text-right font-mono text-muted-foreground tabular-nums"
							>{n(d.changed)}</Table.Cell
						>
						<Table.Cell class="text-right font-mono text-muted-foreground tabular-nums"
							>{d.disappeared ? `−${n(d.disappeared)}` : '0'}</Table.Cell
						>
						<Table.Cell class="text-right font-mono tabular-nums">{n(d.total_current)}</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
		<a
			href={ROUTES.compare(scan.id, data.baseline.scan_id)}
			class="px-1 text-xs text-primary hover:text-primary/80"
		>
			Open comparison
		</a>
	</div>
{/if}
