<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Mail from '@lucide/svelte/icons/mail';
	import Clock from '@lucide/svelte/icons/clock';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { formatShortDate } from '$lib/utilities/dates';
	import { ROUTES } from '$lib/config/routes';
	import { formatTargetType, type TargetType } from '$lib/types/target';
	import type { DashboardSignals } from '$lib/types/dashboard';

	interface Props {
		signals: DashboardSignals | null;
		loading: boolean;
		error: string | null;
		onRetry: () => void;
	}

	let { signals, loading, error, onRetry }: Props = $props();

	const PREVIEW = 4;
	const warnText = 'text-warning';

	let total = $derived(
		signals
			? signals.takeover.count +
					signals.spoofable.count +
					signals.stale.never_scanned +
					signals.stale.stale
			: 0
	);
</script>

<Card.Root class="h-full">
	<Card.Header>
		<Card.Title class="text-sm">Needs attention</Card.Title>
		<Card.Description
			>Derived from DNS, WHOIS &amp; scan coverage — verify before acting</Card.Description
		>
	</Card.Header>
	<Card.Content>
		{#if loading && !signals}
			<div class="grid gap-5 md:grid-cols-3">
				{#each Array(3) as _, i (i)}
					<div class="space-y-2">
						<Skeleton class="h-4 w-32" />
						{#each Array(3) as _, j (j)}
							<Skeleton class="h-7 w-full" />
						{/each}
					</div>
				{/each}
			</div>
		{:else if error && !signals}
			<div class="flex flex-col items-center gap-3 py-8 text-center">
				<TriangleAlert class="h-5 w-5 text-destructive" strokeWidth={1.5} />
				<p class="text-sm text-muted-foreground">{error}</p>
				<Button variant="outline" size="sm" onclick={onRetry}>
					<RefreshCw class="h-4 w-4" />
					Retry
				</Button>
			</div>
		{:else if signals && total === 0}
			<div class="flex flex-col items-center gap-2 py-8 text-center">
				<ShieldCheck class="h-6 w-6 text-muted-foreground" strokeWidth={1.5} />
				<p class="text-sm font-medium">Nothing needs attention</p>
				<p class="text-xs text-muted-foreground">
					No takeover candidates, exposed mail domains, or unscanned targets.
				</p>
			</div>
		{:else if signals}
			<div class="grid gap-5 md:grid-cols-3">
				<div>
					<div class="mb-2 flex items-center gap-2">
						<ShieldAlert class="h-4 w-4 {warnText}" />
						<span class="text-sm font-medium">Possible takeover</span>
						<span
							class="ml-auto rounded-full bg-warning/10 px-1.5 text-xs font-semibold tabular-nums {warnText}"
						>
							{signals.takeover.count}
						</span>
					</div>
					{#if signals.takeover.count === 0}
						<p class="px-2 text-xs text-muted-foreground">None detected.</p>
					{:else}
						<ul class="space-y-0.5">
							{#each signals.takeover.items.slice(0, PREVIEW) as it (it.name)}
								<li>
									<a
										href={ROUTES.target(it.target_id)}
										class="block rounded-md px-2 py-1 transition-colors hover:bg-muted/40"
									>
										<div class="truncate font-mono text-xs">{it.name}</div>
										<div class="truncate text-[11px] text-muted-foreground">
											→ {it.cname} <span class={warnText}>({it.provider})</span>
										</div>
									</a>
								</li>
							{/each}
						</ul>
						{#if signals.takeover.count > PREVIEW}
							<p class="mt-1 px-2 text-[11px] text-muted-foreground">
								+{signals.takeover.count - PREVIEW} more
							</p>
						{/if}
					{/if}
				</div>

				<div>
					<div class="mb-2 flex items-center gap-2">
						<Mail class="h-4 w-4 {warnText}" />
						<span class="text-sm font-medium">Spoofable email</span>
						<span
							class="ml-auto rounded-full bg-warning/10 px-1.5 text-xs font-semibold tabular-nums {warnText}"
						>
							{signals.spoofable.count}
						</span>
					</div>
					{#if signals.spoofable.count === 0}
						<p class="px-2 text-xs text-muted-foreground">None detected.</p>
					{:else}
						<ul class="space-y-0.5">
							{#each signals.spoofable.items.slice(0, PREVIEW) as it (it.target_id)}
								<li>
									<a
										href={ROUTES.target(it.target_id)}
										class="block rounded-md px-2 py-1 transition-colors hover:bg-muted/40"
									>
										<div class="truncate font-mono text-xs">{it.target_value}</div>
										<div class="truncate text-[11px] text-muted-foreground">{it.reason}</div>
									</a>
								</li>
							{/each}
						</ul>
						{#if signals.spoofable.count > PREVIEW}
							<p class="mt-1 px-2 text-[11px] text-muted-foreground">
								+{signals.spoofable.count - PREVIEW} more
							</p>
						{/if}
					{/if}
				</div>

				<div>
					<div class="mb-2 flex items-center gap-2">
						<Clock class="h-4 w-4 text-muted-foreground" />
						<span class="text-sm font-medium">Needs a scan</span>
						<span
							class="ml-auto rounded-full bg-muted px-1.5 text-xs font-semibold tabular-nums text-muted-foreground"
						>
							{signals.stale.never_scanned + signals.stale.stale}
						</span>
					</div>
					{#if signals.stale.never_scanned + signals.stale.stale === 0}
						<p class="px-2 text-xs text-muted-foreground">All targets scanned recently.</p>
					{:else}
						<ul class="space-y-0.5">
							{#each signals.stale.items.slice(0, PREVIEW) as it (it.target_id)}
								<li>
									<a
										href={ROUTES.target(it.target_id)}
										class="block rounded-md px-2 py-1 transition-colors hover:bg-muted/40"
									>
										<div class="truncate font-mono text-xs">{it.target_value}</div>
										<div class="truncate text-[11px] text-muted-foreground">
											{formatTargetType(it.target_type as TargetType)} ·
											{it.last_scanned_at
												? `last ${formatShortDate(it.last_scanned_at)}`
												: 'never scanned'}
										</div>
									</a>
								</li>
							{/each}
						</ul>
						{#if signals.stale.never_scanned + signals.stale.stale > PREVIEW}
							<p class="mt-1 px-2 text-[11px] text-muted-foreground">
								+{signals.stale.never_scanned + signals.stale.stale - PREVIEW} more
							</p>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</Card.Content>
</Card.Root>
