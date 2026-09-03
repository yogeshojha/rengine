<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Card from '$lib/components/ui/card';
	import * as Item from '$lib/components/ui/item';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ScanTrendSparkline from '$lib/components/scans/scan-trend-sparkline.svelte';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import { ROUTES } from '$lib/config/routes';
	import type { ScanRead, ScanStatus } from '$lib/types/scan';

	interface Props {
		history: ScanRead[];
		current: ScanRead;
		loading: boolean;
		nounPlural: string;
	}

	let { history, current, loading, nounPlural }: Props = $props();

	const MAX_ROWS = 5;
	const DOT: Record<ScanStatus, string> = {
		completed: 'bg-success',
		running: 'bg-info',
		pending: 'bg-muted-foreground/40',
		failed: 'bg-destructive',
		cancelled: 'bg-muted-foreground/60'
	};
	const fmt = (iso: string) =>
		new Date(iso).toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});

	let rows = $derived(history.slice(0, MAX_ROWS));
	let trend = $derived(
		[...history]
			.filter((s) => s.status === 'completed')
			.reverse()
			.map((s) => s.subdomains_found)
	);
	let target = $derived(current.execution_config.target_value);
</script>

<Card.Root>
	<Card.Header>
		<Card.Title>Scan history</Card.Title>
		<Card.Description>
			{#if history.length > 1}
				{history.length} scans of {target} · {nounPlural} found per scan
			{:else}
				First scan of {target}
			{/if}
		</Card.Description>
	</Card.Header>
	<Card.Content class="px-3">
		{#if loading && !history.length}
			<div class="flex flex-col gap-2 px-3">
				<Skeleton class="h-10 w-full" />
				<Skeleton class="h-9 w-full" />
				<Skeleton class="h-9 w-full" />
			</div>
		{:else}
			{#if trend.length > 1}
				<div class="px-3 pb-3">
					<ScanTrendSparkline values={trend} class="h-12 w-full" />
				</div>
			{/if}
			<Item.Group class="gap-0.5">
				{#each rows as s (s.id)}
					{@const isCurrent = s.id === current.id}
					{@const added =
						s.status === 'completed' && s.is_first_scan !== true ? (s.new_subdomains ?? 0) : 0}
					<Item.Root
						size="sm"
						variant={isCurrent ? 'muted' : 'default'}
						class={isCurrent ? '' : 'hover:bg-muted/60'}
					>
						{#snippet child({ props })}
							<svelte:element
								this={isCurrent ? 'div' : 'a'}
								href={isCurrent ? undefined : ROUTES.scan(s.id)}
								{...props}
							>
								<Item.Media>
									<span
										class="size-2 rounded-full {DOT[s.status]}"
										title={SCAN_STATUS_LABEL[s.status]}
									></span>
								</Item.Media>
								<Item.Content class="gap-0">
									<Item.Title class="font-normal">
										{s.engine_name}
										{#if isCurrent}<span class="text-xs text-muted-foreground">this scan</span>{/if}
									</Item.Title>
									<Item.Description class="text-xs"
										>{fmt(s.started_at ?? s.created_at)}</Item.Description
									>
								</Item.Content>
								<Item.Actions class="gap-1.5 text-sm tabular-nums">
									<span class="font-medium">{s.subdomains_found.toLocaleString()}</span>
									{#if added > 0}
										<span class="inline-flex items-center text-xs text-success">
											<ArrowUpRight class="size-3" />{added}
										</span>
									{/if}
								</Item.Actions>
							</svelte:element>
						{/snippet}
					</Item.Root>
				{/each}
			</Item.Group>
		{/if}
	</Card.Content>
	{#if history.length > MAX_ROWS}
		<Card.Footer>
			<Button
				variant="link"
				size="sm"
				class="h-auto gap-1 px-0"
				href={ROUTES.target(current.target_id)}
			>
				View all scans <ChevronRight class="size-3.5" />
			</Button>
		</Card.Footer>
	{/if}
</Card.Root>
