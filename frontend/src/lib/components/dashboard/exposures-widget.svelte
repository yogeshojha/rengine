<script lang="ts">
	import Widget from './widget.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { BAND_RAIL, BAND_TEXT, KIND_ICONS } from '$lib/config/interest';
	import { INTEREST_BAND, type InterestPage, type InterestRow } from '$lib/types/interest';

	interface Props {
		page: InterestPage | null;
		class?: string;
	}

	let { page, class: className = '' }: Props = $props();

	const BANDS = [INTEREST_BAND.CRITICAL, INTEREST_BAND.HIGH, INTEREST_BAND.NOTABLE] as const;
	const KINDS_SHOWN = 2;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	$effect(() => {
		void interestCatalog.load();
	});

	let bands = $derived(
		BANDS.map((b) => ({ key: b, count: page?.summary.bands[b] ?? 0 })).filter((b) => b.count > 0)
	);
	let rows = $derived(page?.rows ?? []);
	let kindLabel = (k: string) => interestCatalog.kind(k)?.label ?? k.replace(/_/g, ' ');
	let reasons = (r: InterestRow) => r.kinds.slice(0, KINDS_SHOWN);
</script>

<Widget
	title="Exposures"
	description="Hosts that are risk by what they are, not by a CVE"
	href={ROUTES.exposures()}
	hrefLabel="All exposures"
	class={className}
>
	{#if bands.length}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b px-5 py-2.5 text-xs">
			{#each bands as b (b.key)}
				<span class="flex items-center gap-1.5">
					<span class="size-2 rounded-full {BAND_RAIL[b.key]}"></span>
					<span class="text-muted-foreground">{interestCatalog.bandLabel(b.key)}</span>
					<span class="font-medium tabular-nums">{b.count.toLocaleString()}</span>
				</span>
			{/each}
		</div>
	{/if}
	<ul class="divide-y divide-border/60">
		{#each rows as r (r.subdomain_id)}
			<li>
				<a
					href={ROUTES.exposures()}
					class="flex items-center gap-3 px-5 py-2 transition-colors hover:bg-muted/40"
				>
					<span class="h-8 w-0.5 shrink-0 rounded-full {BAND_RAIL[r.band] ?? 'bg-muted'}"></span>
					<span class="flex min-w-0 flex-1 flex-col gap-0.5">
						<span class="flex min-w-0 items-center gap-2">
							<span class="truncate font-mono text-xs font-medium">{r.host}</span>
							{#if r.is_new}
								<span class="shrink-0 text-[10px] font-medium text-success uppercase">new</span>
							{/if}
						</span>
						<span
							class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground"
						>
							{#each reasons(r) as k (k)}
								{@const Icon = KIND_ICONS[k]}
								<span class="flex items-center gap-1">
									{#if Icon}<Icon class="size-3" />{/if}
									{kindLabel(k)}
								</span>
							{/each}
							{#if r.kinds.length > KINDS_SHOWN}
								<span>+{r.kinds.length - KINDS_SHOWN}</span>
							{/if}
							{#if r.target_value}
								<span class="truncate">· {r.target_value}</span>
							{/if}
						</span>
					</span>
					<Hint text="Exposure score">
						{#snippet child(props)}
							<span {...props} class="text-sm font-semibold tabular-nums {BAND_TEXT[r.band] ?? ''}">
								{r.score}
							</span>
						{/snippet}
					</Hint>
				</a>
			</li>
		{/each}
	</ul>
	{#snippet footer()}
		{#if page}
			{plural(page.total, 'exposed host', 'exposed hosts')} across the project, highest score first
		{/if}
	{/snippet}
</Widget>
