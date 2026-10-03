<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Radar from '@lucide/svelte/icons/radar';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { SCAN_STATUS_DOT } from '$lib/utilities/scan-status';
	import type { ScanStatus } from '$lib/types/scan';
	import type { SurfaceCoverage } from '$lib/types/surface';

	interface Props {
		coverage: SurfaceCoverage | null;
		error?: string | null;
		onRetry?: () => void;
		onScanUncovered?: (targetIds: string[]) => void;
	}

	let { coverage, error = null, onRetry, onScanUncovered }: Props = $props();

	let covered = $derived(coverage?.covered ?? []);
	let uncovered = $derived(coverage?.uncovered ?? []);
	let stale = $derived(covered.filter((t) => t.stale));
	let live = $derived(covered.filter((t) => t.scan_status === 'running'));
	let oldest = $derived(coverage?.observed_from ?? null);

	const statusDot = (status: string | null) =>
		SCAN_STATUS_DOT[status as ScanStatus] ?? 'bg-muted-foreground';

	let Icon = $derived(
		!coverage || !covered.length ? CircleSlash : uncovered.length ? TriangleAlert : CircleCheck
	);
	let tone = $derived(uncovered.length ? 'text-warning' : 'text-muted-foreground');

	let summary = $derived.by(() => {
		if (!coverage || !covered.length) return 'Not scanned';
		const parts = [
			`${covered.length} of ${coverage.targets_total} ${
				coverage.targets_total === 1 ? 'target' : 'targets'
			} scanned`
		];
		if (oldest) parts.push(`oldest ${relativeTime(oldest)}`);
		if (live.length) parts.push(`${live.length} running`);
		return parts.join(' · ');
	});
</script>

<div class="flex flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2 text-xs {tone}">
	{#if coverage}
		<Icon class="size-3.5 shrink-0" />
		<span>{summary}</span>
	{:else if error}
		<TriangleAlert class="size-3.5 shrink-0" />
		<span>Coverage not loaded · {error}</span>
		{#if onRetry}
			<Button variant="outline" size="sm" class="h-6 px-2 text-xs" onclick={() => onRetry()}>
				Retry
			</Button>
		{/if}
	{:else}
		<Skeleton class="h-4 w-56 max-w-full" />
	{/if}

	{#if coverage && (covered.length || uncovered.length)}
		<Popover.Root>
			<Popover.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="sm"
						class="h-6 gap-1 px-1.5 text-xs font-normal text-muted-foreground hover:text-foreground"
					>
						Coverage
					</Button>
				{/snippet}
			</Popover.Trigger>
			<Popover.Content class="w-96 p-0" align="start">
				<div class="border-b px-3 py-2">
					<p class="text-sm font-medium">Coverage</p>
				</div>
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
					<div class="divide-y">
						{#each covered as row (row.target_id)}
							<div class="flex items-center gap-2 px-3 py-2">
								<span class="flex h-5 shrink-0 items-center">
									<span class="size-1.5 rounded-full {statusDot(row.scan_status)}"></span>
								</span>
								<a
									href={ROUTES.target(row.target_id)}
									class="min-w-0 flex-1 truncate text-xs leading-5 hover:text-primary"
								>
									{row.target_value}
								</a>
								<span
									class="shrink-0 text-2xs leading-5 {row.stale
										? 'text-warning'
										: 'text-muted-foreground'}"
								>
									{relativeTime(row.observed_at)}
								</span>
								{#if row.scan_id}
									<a
										href={ROUTES.scan(row.scan_id)}
										class="shrink-0 text-2xs leading-5 text-muted-foreground hover:text-foreground"
									>
										run
									</a>
								{/if}
							</div>
						{/each}
					</div>

					{#if uncovered.length}
						<div class="border-t bg-muted/20 px-3 py-2">
							<p class="text-2xs font-medium text-warning">
								{uncovered.length} not scanned for {coverage.noun_plural}
							</p>
						</div>
						<div class="divide-y">
							{#each uncovered as row (row.target_id)}
								<a
									href={ROUTES.target(row.target_id)}
									class="block truncate px-3 py-1.5 text-xs hover:bg-muted/40"
								>
									{row.target_value}
								</a>
							{/each}
						</div>
					{/if}
				</ScrollArea>

				{#if uncovered.length && onScanUncovered}
					<div class="border-t p-2">
						<Button
							variant="outline"
							size="sm"
							class="w-full gap-1.5 text-xs"
							onclick={() => onScanUncovered(uncovered.map((t) => t.target_id))}
						>
							<Radar class="size-3.5" />
							Scan {uncovered.length}
							{uncovered.length === 1 ? 'target' : 'targets'}
						</Button>
					</div>
				{/if}
			</Popover.Content>
		</Popover.Root>
	{/if}

	{#if stale.length}
		<span class="text-warning">
			{stale.length}
			{stale.length === 1 ? 'target' : 'targets'} last scanned over a month ago
		</span>
	{/if}
</div>
