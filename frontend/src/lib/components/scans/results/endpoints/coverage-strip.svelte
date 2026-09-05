<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Info from '@lucide/svelte/icons/info';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { COVERAGE_STATUS_LABELS } from '$lib/config/vulnerabilities';
	import { PROBE_COVERAGE_SOURCE } from '$lib/config/endpoints';
	import type { EndpointCoverageRead, EndpointSummary } from '$lib/utilities/endpoints';

	interface Props {
		coverage: EndpointCoverageRead[];
		summary: EndpointSummary | null;
		compact?: boolean;
		hidden?: number;
		onShowStatic?: () => void;
	}

	let { coverage, summary, compact = false, hidden = 0, onShowStatic }: Props = $props();

	const n = (value: number | null | undefined) =>
		value === null || value === undefined ? null : value.toLocaleString();

	let ran = $derived(coverage.some((c) => c.status !== 'skipped'));
	// requested and got nothing back is not the same as never requested
	let noAnswer = $derived(
		coverage
			.filter((c) => c.source === PROBE_COVERAGE_SOURCE)
			.reduce((n, c) => n + (c.errors ?? 0), 0)
	);
	let unverified = $derived(Math.max(0, (summary?.total ?? 0) - (summary?.probed ?? 0) - noAnswer));
	let capped = $derived(coverage.some((c) => c.capped));
	let failed = $derived(coverage.some((c) => c.status === 'failed'));
	let Icon = $derived(!ran ? CircleSlash : failed || capped ? TriangleAlert : CircleCheck);
	let tone = $derived(
		!ran ? 'text-muted-foreground' : failed || capped ? 'text-warning' : 'text-muted-foreground'
	);
	let line = $derived.by(() => {
		if (!ran) return 'No URL discovery ran on this scan.';
		const parts: string[] = [];
		if (summary) {
			parts.push(
				`${n(summary.total)} ${summary.total === 1 ? 'endpoint' : 'endpoints'} across ${n(
					summary.hosts
				)} ${summary.hosts === 1 ? 'host' : 'hosts'}`
			);
			parts.push(`${n(summary.probed)} verified`);
			if (noAnswer) parts.push(`${n(noAnswer)} no answer`);
			if (unverified) parts.push(`${n(unverified)} not checked`);
		}
		return parts.join(' · ');
	});
</script>

<div
	class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs {tone} {compact
		? ''
		: 'border-b bg-muted/10 px-4 py-2'}"
>
	<Icon class="size-3.5 shrink-0" />
	<span>{line}</span>
	{#if hidden > 0}
		<span>·</span>
		<button
			type="button"
			class="rounded-sm text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			onclick={onShowStatic}
		>
			{n(hidden)} static hidden
		</button>
	{/if}
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
			<Popover.Content class="w-[26rem] p-0" align="start">
				<div class="border-b px-3 py-2">
					<p class="text-sm font-medium">What ran</p>
					<p class="text-xs text-muted-foreground">
						Each source's own account. A blank count means it was not reported, not zero.
					</p>
				</div>
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
					<div class="divide-y">
						{#each coverage as row (row.id)}
							<div class="px-3 py-2">
								<div class="flex items-baseline gap-2">
									<span class="text-sm font-medium">{row.label}</span>
									{#if row.tool}
										<span class="font-mono text-[10px] text-muted-foreground">{row.tool}</span>
									{/if}
									<span
										class="ml-auto text-xs {row.status === 'failed'
											? 'text-destructive'
											: row.status === 'partial'
												? 'text-warning'
												: 'text-muted-foreground'}"
									>
										{COVERAGE_STATUS_LABELS[row.status] ?? row.status}
									</span>
								</div>
								<dl class="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
									{#each [['Found', row.urls_found], ['Stored', row.urls_stored], ['Verified', row.urls_probed], ['Pages fetched', row.pages_fetched], ['Hosts', row.hosts_scanned], ['Depth reached', row.depth_reached], ['Errors', row.errors]] as [label, value] (label)}
										{#if value !== null && value !== undefined}
											<div class="flex justify-between gap-2">
												<dt class="text-muted-foreground">{label}</dt>
												<dd class="tabular-nums">{n(value as number)}</dd>
											</div>
										{/if}
									{/each}
								</dl>
								{#if row.cap_reason}
									<p class="mt-1 text-[11px] text-muted-foreground">{row.cap_reason}</p>
								{/if}
								{#if row.error}
									<p class="mt-1 text-[11px] text-destructive">{row.error}</p>
								{/if}
							</div>
						{/each}
					</div>
				</ScrollArea>
			</Popover.Content>
		</Popover.Root>
	{/if}
</div>
