<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { SvelteMap } from 'svelte/reactivity';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import LookalikeRow from './lookalike-row.svelte';
	import { lookalikesApi } from '$lib/api/lookalikes';
	import { SEVERITY_CHIP } from '$lib/config/vulnerabilities';
	import { LookalikeState, STATE_LABELS, VERDICTS } from '$lib/config/lookalikes';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import type { LookalikeSummary } from '$lib/types/lookalike';

	interface Props {
		open: boolean;
		onOpenChange: (open: boolean) => void;
		summary: LookalikeSummary;
		projectId: string;
		verdict?: string | null;
		onChanged?: () => void;
	}

	let {
		open,
		onOpenChange,
		summary,
		projectId,
		verdict = $bindable(null),
		onChanged
	}: Props = $props();

	const TABS = [LookalikeState.OPEN, LookalikeState.REVIEWED, LookalikeState.IGNORED].map(
		(key) => ({
			key,
			label: STATE_LABELS[key]
		})
	);

	let overrides = new SvelteMap<string, string>();
	let tab = $state<string>(LookalikeState.OPEN);
	let tabFor = '';
	let bulkPending = $state(false);

	$effect.pre(() => {
		const key = open ? `${summary.target_id ?? ''}:${summary.apex ?? ''}` : '';
		if (key === tabFor) return;
		tabFor = key;
		if (key) tab = LookalikeState.OPEN;
	});

	const stateOf = (domain: string, stored: string) => overrides.get(domain) ?? stored;

	let rows = $derived(summary.rows.map((r) => ({ ...r, state: stateOf(r.domain, r.state) })));
	let inTab = $derived(rows.filter((r) => r.state === tab));
	let shown = $derived(verdict ? inTab.filter((r) => r.verdict === verdict) : inTab);
	let counts = $derived(
		Object.fromEntries(TABS.map((t) => [t.key, rows.filter((r) => r.state === t.key).length]))
	);
	let bars = $derived(
		VERDICTS.map((v) => ({ ...v, count: inTab.filter((r) => r.verdict === v.key).length })).filter(
			(v) => v.count > 0
		)
	);
	let total = $derived(bars.reduce((n, b) => n + b.count, 0));

	async function setReview(domains: string[], next: LookalikeState) {
		if (!summary.target_id || !domains.length) return false;
		const previous = domains.map((d) => [d, overrides.get(d)] as const);
		for (const d of domains) overrides.set(d, next);
		try {
			await lookalikesApi.triage(projectId, summary.target_id, domains, next);
			onChanged?.();
			return true;
		} catch {
			for (const [d, s] of previous) {
				if (s === undefined) overrides.delete(d);
				else overrides.set(d, s);
			}
			toast.error('Review state not saved');
			return false;
		}
	}

	async function markShown() {
		bulkPending = true;
		const n = shown.length;
		const ok = await setReview(
			shown.map((r) => r.domain),
			LookalikeState.REVIEWED
		);
		bulkPending = false;
		if (ok) toast.success(`${plural(n, 'lookalike')} marked reviewed`);
	}

	let subtitle = $derived(
		[
			summary.permutations != null
				? `${summary.permutations.toLocaleString()} permutations checked`
				: null,
			`${summary.registered.toLocaleString()} registered`,
			summary.observed_at ? `observed ${relativeTime(summary.observed_at)}` : null
		]
			.filter(Boolean)
			.join(' · ')
	);
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		<Sheet.Header class="gap-1 border-b px-5 pt-4 pb-0 pr-12">
			<Sheet.Title class="text-base">
				Lookalikes of <span class="font-mono">{summary.apex}</span>
			</Sheet.Title>
			<Sheet.Description>{subtitle}</Sheet.Description>
			<div class="mt-2">
				<CountTabs
					tabs={TABS}
					value={tab}
					{counts}
					onChange={(k) => {
						tab = k;
						verdict = null;
					}}
				/>
			</div>
		</Sheet.Header>

		{#if total > 0}
			<div class="flex flex-col gap-2.5 border-b px-5 py-3.5">
				<div class="flex h-2 w-full gap-0.5 overflow-hidden rounded-full">
					{#each bars as b (b.key)}
						<button
							type="button"
							class="h-full transition-opacity {SEVERITY_CHIP[b.severity].edge} {verdict &&
							verdict !== b.key
								? 'opacity-25'
								: ''}"
							style="width:{(b.count / total) * 100}%"
							aria-label="{b.label}: {b.count}"
							onclick={() => (verdict = verdict === b.key ? null : b.key)}
						></button>
					{/each}
				</div>
				<div class="flex flex-wrap gap-1">
					{#each bars as b (b.key)}
						<button
							type="button"
							aria-pressed={verdict === b.key}
							class="flex h-6 items-center gap-1.5 rounded-md px-2 text-xs transition-colors hover:bg-muted {verdict ===
							b.key
								? 'bg-muted text-foreground'
								: 'text-muted-foreground'}"
							onclick={() => (verdict = verdict === b.key ? null : b.key)}
						>
							<span class="size-2 rounded-full {SEVERITY_CHIP[b.severity].edge}"></span>
							{b.label}
							<span class="font-medium text-foreground tabular-nums">{b.count}</span>
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<ScrollArea class="min-h-0 flex-1">
			{#if shown.length === 0}
				<EmptyState
					compact
					title="No {STATE_LABELS[tab].toLowerCase()} lookalikes"
					class="m-4 border-dashed"
				/>
			{:else}
				<ul class="flex flex-col divide-y divide-border/60 px-1">
					{#each shown as r (r.domain)}
						<LookalikeRow row={r} onReview={(next) => setReview([r.domain], next)} />
					{/each}
				</ul>
			{/if}
		</ScrollArea>

		{#if tab === LookalikeState.OPEN && shown.length > 1}
			<Sheet.Footer class="border-t px-5 py-3 sm:flex-row sm:justify-start">
				<LoadingButton size="sm" variant="outline" loading={bulkPending} onclick={markShown}>
					Mark {shown.length} reviewed
				</LoadingButton>
			</Sheet.Footer>
		{/if}
	</Sheet.Content>
</Sheet.Root>
