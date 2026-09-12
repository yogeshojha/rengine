<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Check from '@lucide/svelte/icons/check';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import {
		CHECKS,
		HYGIENE_NONE,
		HygieneTone,
		TONE_DOT,
		TONE_LABEL,
		hygieneQuery,
		type CheckSpec
	} from '$lib/config/hygiene';
	import type { HygieneCheckCount, HygieneSummary } from '$lib/utilities/scan-insights';

	interface Props {
		summary: HygieneSummary | null;
		loading: boolean;
		onFilter: (search: string) => void;
	}

	let { summary, loading, onFilter }: Props = $props();

	const MIN_METER = 1.5;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	interface Row {
		spec: CheckSpec;
		count: HygieneCheckCount;
	}

	let byKey = $derived(new Map((summary?.checks ?? []).map((c) => [c.key, c])));
	let failing = $derived.by<Row[]>(() =>
		CHECKS.map((spec) => ({ spec, count: byKey.get(spec.key) }))
			.filter((r): r is Row => !!r.count && r.count.failing > 0)
			.sort((a, b) => b.count.failing / b.count.applicable - a.count.failing / a.count.applicable)
	);
	let warnings = $derived(failing.filter((r) => r.spec.tone === HygieneTone.WARNING));
	let infos = $derived(failing.filter((r) => r.spec.tone === HygieneTone.INFO));
	let passing = $derived(
		CHECKS.filter((spec) => {
			const c = byKey.get(spec.key);
			return !!c && c.applicable > 0 && c.failing === 0;
		})
	);
	let evaluated = $derived(summary?.evaluated ?? 0);
	let pending = $derived(summary?.pending ?? 0);
	let hasData = $derived(evaluated > 0 || pending > 0);

	const share = (r: Row) =>
		r.count.applicable > 0 ? (r.count.failing / r.count.applicable) * 100 : 0;
	const shareLabel = (r: Row) => {
		const p = share(r);
		return p > 0 && p < 1 ? '<1%' : `${Math.round(p)}%`;
	};
</script>

{#if (loading && !summary) || hasData}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Web hygiene">
			{#if summary}
				<span class="tabular-nums"
					>{plural(evaluated, 'web asset checked', 'web assets checked')}</span
				>
				{#if summary.warning > 0}
					<span class="flex items-center gap-1.5 tabular-nums">
						<span class="size-1.5 rounded-full {TONE_DOT.warning}" aria-hidden="true"></span>
						{summary.warning.toLocaleString()} warning
					</span>
				{/if}
				{#if summary.info > 0}
					<span class="flex items-center gap-1.5 tabular-nums">
						<span class="size-1.5 rounded-full {TONE_DOT.info}" aria-hidden="true"></span>
						{summary.info.toLocaleString()} info
					</span>
				{/if}
			{/if}
		</PanelHead>

		{#if !summary}
			<div class="grid grid-cols-1 md:grid-cols-2">
				{#each Array(2) as _, i (i)}
					<div class="flex flex-col gap-3 p-5 {i > 0 ? 'border-t md:border-t-0 md:border-l' : ''}">
						<Skeleton class="h-4 w-24" />
						<Skeleton class="h-10 w-full" />
						<Skeleton class="h-10 w-full" />
						<Skeleton class="h-10 w-full" />
					</div>
				{/each}
			</div>
		{:else if evaluated === 0}
			<p class="p-5 text-sm text-muted-foreground">
				{plural(pending, 'web asset', 'web assets')} pending evaluation.
			</p>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2">
				{@render column(HygieneTone.WARNING, warnings, '')}
				{@render column(HygieneTone.INFO, infos, 'border-t md:border-t-0 md:border-l')}
			</div>
			<div
				class="flex flex-wrap items-center gap-x-4 gap-y-2 border-t px-5 py-3 text-xs text-muted-foreground"
			>
				{#if summary.clean > 0}
					<Button
						variant="link"
						size="sm"
						class="h-auto gap-1 px-0 text-xs"
						onclick={() => onFilter(hygieneQuery(HYGIENE_NONE))}
					>
						{plural(summary.clean, 'web asset passes', 'web assets pass')} every applicable check
						<ChevronRight class="size-3.5" />
					</Button>
				{/if}
				{#if pending > 0}
					<span class="tabular-nums"
						>{plural(pending, 'web asset', 'web assets')} pending evaluation</span
					>
				{/if}
				{#if passing.length}
					<span class="flex flex-wrap items-center gap-1.5">
						<span>Passing on every applicable web asset</span>
						{#each passing as spec (spec.key)}
							<Hint text={spec.help}>
								{#snippet child(props)}
									<span
										{...props}
										class="inline-flex h-5 items-center gap-1 rounded-sm border border-border px-1.5 text-2xs"
									>
										<Check class="size-3 text-success" />
										{spec.label}
									</span>
								{/snippet}
							</Hint>
						{/each}
					</span>
				{/if}
			</div>
		{/if}
	</Card.Root>
{/if}

{#snippet column(tone: HygieneTone, rows: Row[], cls: string)}
	<section class="flex min-w-0 flex-col gap-3 p-5 {cls}">
		<div class="flex items-center gap-2">
			<span class="size-1.5 rounded-full {TONE_DOT[tone]}" aria-hidden="true"></span>
			<h3 class="text-sm font-medium">{TONE_LABEL[tone]}</h3>
			<span class="text-xs text-muted-foreground tabular-nums">
				{plural(rows.length, 'check failing', 'checks failing')}
			</span>
		</div>
		{#if rows.length}
			<ul class="-mx-2 flex flex-col gap-0.5">
				{#each rows as r (r.spec.key)}
					<li>
						<button
							type="button"
							class="group flex w-full flex-col gap-1.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/50"
							onclick={() => onFilter(r.count.query)}
						>
							<span class="flex w-full items-center gap-2">
								<span class="flex min-w-0 flex-1 flex-col">
									<Hint text={r.spec.help}>
										{#snippet child(props)}
											<span {...props} class="truncate text-sm leading-5">{r.spec.label}</span>
										{/snippet}
									</Hint>
									<span class="truncate text-xs leading-4 text-muted-foreground">
										of {plural(r.count.applicable, 'applicable web asset', 'applicable web assets')}
									</span>
								</span>
								<span class="text-sm font-medium tabular-nums"
									>{r.count.failing.toLocaleString()}</span
								>
								<span class="w-9 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
									{shareLabel(r)}
								</span>
							</span>
							<span
								class="block h-1 w-full overflow-hidden rounded-full bg-muted"
								aria-hidden="true"
							>
								<span
									class="block h-full rounded-full {TONE_DOT[tone]}"
									style="width:{Math.max(MIN_METER, share(r))}%"
								></span>
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="text-xs text-muted-foreground">
				No {TONE_LABEL[tone].toLowerCase()} checks failing.
			</p>
		{/if}
	</section>
{/snippet}
