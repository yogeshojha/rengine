<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Info from '@lucide/svelte/icons/info';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { COVERAGE_STATUS_LABELS } from '$lib/config/vulnerabilities';
	import type { CoverageRead } from '$lib/utilities/vulns';

	interface Props {
		coverage: CoverageRead[];
		compact?: boolean;
	}

	let { coverage, compact = false }: Props = $props();

	const n = (value: number | null | undefined) =>
		value === null || value === undefined ? null : value.toLocaleString();

	let ran = $derived(coverage.some((c) => c.status !== 'skipped'));
	let checks = $derived(Math.max(0, ...coverage.map((c) => c.templates_selected ?? 0)));
	// every group scans a different slice of the surface, but all of them run the same check set
	let targets = $derived(coverage.reduce((n, c) => n + c.hosts_total, 0));
	let requests = $derived.by(() => {
		const known = coverage.map((c) => c.requests_sent).filter((v): v is number => v !== null);
		return known.length ? known.reduce((a, b) => a + b, 0) : null;
	});
	let errors = $derived.by(() => {
		const known = coverage.map((c) => c.errors).filter((v): v is number => v !== null);
		return known.length ? known.reduce((a, b) => a + b, 0) : null;
	});
	let dropped = $derived(coverage.reduce((a, c) => a + c.hosts_dropped.length, 0));
	let partial = $derived(coverage.some((c) => c.status === 'partial' || c.status === 'failed'));
	let Icon = $derived(!ran ? CircleSlash : partial ? TriangleAlert : CircleCheck);
	let tone = $derived(
		!ran ? 'text-muted-foreground' : partial ? 'text-warning' : 'text-muted-foreground'
	);
	let summary = $derived.by(() => {
		if (!ran) return 'No vulnerability scan ran on this scan.';
		const parts = [
			`${n(checks)} ${checks === 1 ? 'check' : 'checks'} against ${n(targets)} ${
				targets === 1 ? 'target' : 'targets'
			}`
		];
		if (requests !== null) parts.push(`${n(requests)} ${requests === 1 ? 'request' : 'requests'}`);
		if (dropped) parts.push(`${n(dropped)} ${dropped === 1 ? 'host' : 'hosts'} dropped`);
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
						Checks selected, loaded and sent by each scanner. A blank number means the scanner did
						not report it.
					</p>
				</div>
				<div class="divide-y">
					{#each coverage as row (row.id)}
						<div class="space-y-2 px-3 py-2.5">
							<div class="flex items-baseline justify-between gap-2">
								<span class="text-xs font-medium">{row.group}</span>
								<span
									class="text-[10px] tracking-wide uppercase {row.status === 'completed'
										? 'text-success'
										: row.status === 'skipped'
											? 'text-muted-foreground'
											: 'text-warning'}"
								>
									{COVERAGE_STATUS_LABELS[row.status] ?? row.status}
								</span>
							</div>
							<dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Selected</dt>
									<dd class="font-mono tabular-nums">{n(row.templates_selected) ?? '—'}</dd>
								</div>
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Loaded</dt>
									<dd class="font-mono tabular-nums">{n(row.templates_loaded) ?? '—'}</dd>
								</div>
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Targets</dt>
									<dd class="font-mono tabular-nums">{n(row.hosts_total)}</dd>
								</div>
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Requests</dt>
									<dd class="font-mono tabular-nums">{n(row.requests_sent) ?? '—'}</dd>
								</div>
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Rate</dt>
									<dd class="font-mono tabular-nums">
										{row.rate_limit ? `${row.rate_limit}/s` : '—'}
									</dd>
								</div>
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Errors</dt>
									<dd class="font-mono tabular-nums">{n(row.errors) ?? '—'}</dd>
								</div>
							</dl>
							{#if row.templates_selected != null && row.templates_loaded != null && row.templates_loaded < row.templates_selected}
								<p class="text-[11px] text-warning">
									{n(row.templates_selected - row.templates_loaded)} of the selected checks were not loaded
									by the scanner.
								</p>
							{/if}
							{#if row.hosts_dropped.length}
								<p class="text-[11px] text-warning">
									Stopped testing {row.hosts_dropped.length}
									{row.hosts_dropped.length === 1 ? 'host' : 'hosts'} after repeated errors:
									<span class="font-mono">{row.hosts_dropped[0].host}</span>
									{#if row.hosts_dropped.length > 1}and {row.hosts_dropped.length - 1} more{/if}
								</p>
							{/if}
							{#if row.error}
								<p class="text-[11px] text-muted-foreground">{row.error}</p>
							{/if}
						</div>
					{/each}
				</div>
			</Popover.Content>
		</Popover.Root>
	{/if}
</div>
