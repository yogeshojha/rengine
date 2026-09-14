<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Info from '@lucide/svelte/icons/info';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { SvelteMap } from 'svelte/reactivity';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { COVERAGE_STATUS_LABELS } from '$lib/config/vulnerabilities';
	import { TIER_HELP, TIER_LABELS, TIER_ORDER } from '$lib/config/scan-surface';
	import type { CoverageRead } from '$lib/utilities/vulns';

	interface Props {
		coverage: CoverageRead[];
		projectWide?: boolean;
		compact?: boolean;
	}

	let { coverage, projectWide = false, compact = false }: Props = $props();

	interface TierRow {
		key: string;
		label: string;
		help: string | null;
		status: string;
		batches: number;
		checks: number;
		targets: number;
		covered: number;
		requests: number | null;
		errors: number | null;
		dropped: number;
		unloaded: number;
		error: string | null;
		sample: string | null;
	}

	const n = (value: number | null | undefined) =>
		value === null || value === undefined ? null : value.toLocaleString();

	const sum = (values: (number | null)[]): number | null => {
		const known = values.filter((v): v is number => v !== null);
		return known.length ? known.reduce((a, b) => a + b, 0) : null;
	};

	const worst = (statuses: string[]): string => {
		if (statuses.every((s) => s === 'skipped')) return 'skipped';
		if (statuses.some((s) => s === 'failed')) return 'failed';
		if (statuses.some((s) => s === 'partial' || s === 'skipped')) return 'partial';
		return 'completed';
	};

	let ran = $derived(coverage.some((c) => c.status !== 'skipped'));
	let tiers = $derived.by((): TierRow[] => {
		const groups = new SvelteMap<string, CoverageRead[]>();
		for (const row of coverage) {
			const key = row.tier ?? row.group;
			groups.set(key, [...(groups.get(key) ?? []), row]);
		}
		const order = (key: string) => {
			const i = TIER_ORDER.indexOf(key);
			return i === -1 ? TIER_ORDER.length : i;
		};
		return [...groups.entries()]
			.sort((a, b) => order(a[0]) - order(b[0]))
			.map(([key, rows]) => {
				const dropped = rows.reduce((a, c) => a + c.hosts_dropped_count, 0);
				const unloaded = rows.reduce(
					(a, c) =>
						a +
						(c.templates_selected != null && c.templates_loaded != null
							? Math.max(0, c.templates_selected - c.templates_loaded)
							: 0),
					0
				);
				return {
					key,
					label: TIER_LABELS[key] ?? key,
					help: TIER_HELP[key] ?? null,
					status: worst(rows.map((r) => r.status)),
					batches: rows.length,
					checks: Math.max(0, ...rows.map((r) => r.templates_selected ?? 0)),
					targets: rows.reduce((a, c) => a + c.hosts_total, 0),
					covered: rows.reduce((a, c) => a + c.hosts_covered, 0),
					requests: sum(rows.map((r) => r.requests_sent)),
					errors: sum(rows.map((r) => r.errors)),
					dropped,
					unloaded,
					error: rows.find((r) => r.error)?.error ?? null,
					sample: rows.find((r) => r.hosts_dropped.length)?.hosts_dropped[0]?.host ?? null
				};
			});
	});
	let checks = $derived(Math.max(0, ...coverage.map((c) => c.templates_selected ?? 0)));
	let targets = $derived(
		Math.max(0, ...tiers.filter((t) => t.key !== 'replay').map((t) => t.targets))
	);
	let covered = $derived(Math.max(0, ...tiers.map((t) => t.covered)));
	let requests = $derived(sum(coverage.map((c) => c.requests_sent)));
	let errors = $derived(sum(coverage.map((c) => c.errors)));
	let dropped = $derived(coverage.reduce((a, c) => a + c.hosts_dropped_count, 0));
	let partial = $derived(coverage.some((c) => c.status === 'partial' || c.status === 'failed'));
	let Icon = $derived(!ran ? CircleSlash : partial ? TriangleAlert : CircleCheck);
	let tone = $derived(
		!ran ? 'text-muted-foreground' : partial ? 'text-warning' : 'text-muted-foreground'
	);
	let summary = $derived.by(() => {
		if (!ran) return projectWide ? 'No vulnerability scan has run.' : 'No vulnerability scan ran.';
		const parts = [
			`${n(checks)} ${checks === 1 ? 'check' : 'checks'} against ${n(targets)} ${
				targets === 1 ? 'target' : 'targets'
			}`
		];
		if (covered) parts.push(`${n(covered)} covered by an equivalent`);
		if (requests !== null) parts.push(`${n(requests)} ${requests === 1 ? 'request' : 'requests'}`);
		if (dropped) parts.push(`${n(dropped)} ${dropped === 1 ? 'target' : 'targets'} dropped`);
		else if (errors) parts.push(`${n(errors)} request ${errors === 1 ? 'error' : 'errors'}`);
		return parts.join(' · ');
	});
</script>

<div
	class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs {tone} {compact
		? ''
		: 'border-b bg-muted/10 px-4 py-2'}"
>
	<Icon class="size-3.5 shrink-0" />
	<span>{summary}</span>
	{#if coverage.length}
		<Popover.Root>
			<Popover.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="sm"
						class="h-6 gap-1 px-1.5 text-xs font-normal text-muted-foreground hover:text-foreground"
					>
						<Info class="size-3" /> What ran
					</Button>
				{/snippet}
			</Popover.Trigger>
			<Popover.Content class="w-96 p-0" align="start">
				<div class="border-b px-3 py-2">
					<p class="text-sm font-medium">Scanner coverage</p>
					<p class="text-xs text-muted-foreground">
						Checks and targets per tier. Blank counts were not reported.
					</p>
				</div>
				<ScrollArea class="max-h-96">
					<div class="divide-y">
						{#each tiers as row (row.key)}
							<div class="space-y-2 px-3 py-2.5">
								<div class="flex items-baseline justify-between gap-2">
									<span class="text-xs font-medium">{row.label}</span>
									<span
										class="text-2xs tracking-wide uppercase {row.status === 'completed'
											? 'text-success'
											: row.status === 'skipped'
												? 'text-muted-foreground'
												: 'text-warning'}"
									>
										{COVERAGE_STATUS_LABELS[row.status] ?? row.status}
									</span>
								</div>
								{#if row.help}
									<p class="text-2xs text-muted-foreground">{row.help}</p>
								{/if}
								<dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-2xs">
									<div class="flex justify-between gap-2">
										<dt class="text-muted-foreground">Checks</dt>
										<dd class="font-mono tabular-nums">{n(row.checks) ?? '—'}</dd>
									</div>
									<div class="flex justify-between gap-2">
										<dt class="text-muted-foreground">Batches</dt>
										<dd class="font-mono tabular-nums">{n(row.batches)}</dd>
									</div>
									<div class="flex justify-between gap-2">
										<dt class="text-muted-foreground">Targets</dt>
										<dd class="font-mono tabular-nums">{n(row.targets)}</dd>
									</div>
									<div class="flex justify-between gap-2">
										<dt class="text-muted-foreground">Covered</dt>
										<dd class="font-mono tabular-nums">{n(row.covered)}</dd>
									</div>
									<div class="flex justify-between gap-2">
										<dt class="text-muted-foreground">Requests</dt>
										<dd class="font-mono tabular-nums">{n(row.requests) ?? '—'}</dd>
									</div>
									<div class="flex justify-between gap-2">
										<dt class="text-muted-foreground">Errors</dt>
										<dd class="font-mono tabular-nums">{n(row.errors) ?? '—'}</dd>
									</div>
								</dl>
								{#if row.unloaded}
									<p class="text-2xs text-warning">
										{n(row.unloaded)} selected checks not loaded.
									</p>
								{/if}
								{#if row.dropped && row.sample}
									<p class="text-2xs text-warning">
										Stopped testing {row.dropped}
										{row.dropped === 1 ? 'target' : 'targets'} after repeated errors:
										<span class="font-mono">{row.sample}</span>
										{#if row.dropped > 1}and {row.dropped - 1} more{/if}
									</p>
								{/if}
								{#if row.error}
									<p class="text-2xs text-muted-foreground">{row.error}</p>
								{/if}
							</div>
						{/each}
					</div>
				</ScrollArea>
			</Popover.Content>
		</Popover.Root>
	{/if}
</div>
