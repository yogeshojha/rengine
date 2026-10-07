<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import Check from '@lucide/svelte/icons/check';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import Copy from '@lucide/svelte/icons/copy';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import { cloudStorageApi } from '$lib/api/cloud-storage';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { externalHref } from '$lib/utilities/links';
	import { relativeTime } from '$lib/utilities/dates';
	import { formatBytes } from '$lib/utilities/format';
	import { plural } from '$lib/utilities/strings';
	import { SEVERITY_CHIP } from '$lib/config/vulnerabilities';
	import {
		ACCESS_BY_KEY,
		ACCESS_ORDER,
		OPEN_ACCESS,
		PROVIDER_LABELS,
		ReviewState,
		SOURCE_HELP,
		SOURCE_LABELS,
		STATE_LABELS
	} from '$lib/config/cloud-storage';
	import type { CloudBucket, CloudBucketSummary } from '$lib/types/cloud-storage';

	interface Props {
		projectId: string;
		scanId?: string;
		targetId?: string;
		active?: boolean;
		revision?: number;
		onTotal?: (total: number) => void;
	}

	let { projectId, scanId, targetId, active = true, revision = 0, onTotal }: Props = $props();

	let summary = $state<CloudBucketSummary | null>(null);
	let loading = $state(false);
	let errored = $state(false);
	let seen = $state(false);
	let filter = $state<string>('all');
	let overrides = new SvelteMap<string, string>();
	let req = 0;

	const keyOf = (b: CloudBucket) => `${b.provider}|${b.name}`;
	const stateOf = (b: CloudBucket) => overrides.get(keyOf(b)) ?? b.state;

	async function load() {
		if (!projectId || (!scanId && !targetId)) return;
		const my = ++req;
		loading = true;
		try {
			const res = scanId
				? await cloudStorageApi.scan(projectId, scanId)
				: await cloudStorageApi.target(projectId, targetId as string);
			if (my !== req) return;
			summary = res;
			errored = false;
			overrides.clear();
			onTotal?.(res.total);
		} catch {
			if (my !== req) return;
			errored = true;
		} finally {
			if (my === req) loading = false;
		}
	}

	$effect(() => {
		if (active) seen = true;
	});

	$effect(() => {
		void revision;
		void scanId;
		void targetId;
		if (untrack(() => seen) || active) void load();
	});

	let rows = $derived(summary?.rows ?? []);
	let shown = $derived(
		filter === 'all'
			? rows
			: filter === 'open'
				? rows.filter((r) => OPEN_ACCESS.has(r.access))
				: rows.filter((r) => r.access === filter)
	);
	let tabs = $derived([
		{ key: 'all', label: 'All' },
		...((summary?.open_count ?? 0) > 0 ? [{ key: 'open', label: 'Open' }] : []),
		...ACCESS_ORDER.filter((a) => (summary?.access_counts[a] ?? 0) > 0).map((a) => ({
			key: a as string,
			label: ACCESS_BY_KEY[a].label
		}))
	]);
	let counts = $derived({
		all: summary?.total ?? 0,
		open: summary?.open_count ?? 0,
		...(summary?.access_counts ?? {})
	});
	let subtitle = $derived(
		summary
			? [
					summary.candidates != null ? `${plural(summary.candidates, 'name')} checked` : null,
					summary.observed_at ? `observed ${relativeTime(summary.observed_at)}` : null
				]
					.filter(Boolean)
					.join(' · ')
			: ''
	);

	async function setReview(bucket: CloudBucket, next: ReviewState) {
		if (!summary?.target_id) return;
		const key = keyOf(bucket);
		const previous = overrides.get(key);
		overrides.set(key, next);
		try {
			await cloudStorageApi.triage(
				projectId,
				summary.target_id,
				[[bucket.provider, bucket.name]],
				next
			);
		} catch {
			if (previous === undefined) overrides.delete(key);
			else overrides.set(key, previous);
			toast.error('Review state not saved');
		}
	}

	async function copy(value: string) {
		await writeClipboard(value);
		toast.success('Copied');
	}
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-wrap items-center justify-between gap-2">
		<div class="flex flex-col">
			<span class="text-sm font-medium">Cloud storage</span>
			{#if subtitle}
				<span class="text-xs text-muted-foreground">{subtitle}</span>
			{/if}
		</div>
		{#if tabs.length > 1}
			<CountTabs {tabs} value={filter} {counts} onChange={(k) => (filter = k)} />
		{/if}
	</div>

	{#if loading && !summary}
		<div class="flex flex-col gap-2">
			{#each Array(4) as _, i (i)}
				<Skeleton class="h-12 w-full rounded-lg" />
			{/each}
		</div>
	{:else if errored}
		<EmptyState compact title="Could not load" class="border-dashed" />
	{:else if !summary?.covered}
		<EmptyState compact title="Not scanned" class="border-dashed" />
	{:else if shown.length === 0}
		<EmptyState
			compact
			title={filter === 'all' ? 'No buckets' : 'No matches'}
			class="border-dashed"
		/>
	{:else}
		<div class="overflow-hidden rounded-xl border bg-card">
			<div
				class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-0 divide-y divide-border/60 sm:grid-cols-[7rem_minmax(0,1fr)_8rem_auto]"
			>
				{#each shown as b (keyOf(b))}
					{@const spec = ACCESS_BY_KEY[b.access]}
					{@const sev = SEVERITY_CHIP[spec.severity]}
					{@const current = stateOf(b)}
					<div class="col-span-full grid grid-cols-subgrid items-center px-4 py-2.5">
						<div class="order-1">
							<span
								title={spec.help}
								class="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium {OPEN_ACCESS.has(
									b.access
								)
									? `${sev.ink}`
									: 'text-muted-foreground'}"
							>
								<span class="size-2 rounded-full {sev.edge}"></span>
								{spec.label}
							</span>
						</div>
						<div class="order-3 col-span-full min-w-0 sm:order-2 sm:col-span-1">
							<div class="flex items-center gap-2">
								<a
									href={externalHref(b.url)}
									target="_blank"
									rel="noopener noreferrer"
									class="truncate font-mono text-sm hover:text-foreground hover:underline"
									title={b.url}
								>
									{b.name}
								</a>
								<ArrowUpRight class="size-3 shrink-0 text-muted-foreground" />
							</div>
							<div class="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
								<span>{PROVIDER_LABELS[b.provider] ?? b.provider}</span>
								{#if b.region}<span>· {b.region}</span>{/if}
								<span title={SOURCE_HELP[b.source]} class="rounded border px-1 py-px">
									{SOURCE_LABELS[b.source] ?? b.source}
								</span>
								{#if current !== ReviewState.OPEN}
									<span class="rounded border border-dashed px-1 py-px"
										>{STATE_LABELS[current]}</span
									>
								{/if}
							</div>
						</div>
						<div class="order-2 text-right text-xs text-muted-foreground tabular-nums sm:order-3">
							{#if b.object_count != null}
								{plural(b.object_count, 'object')}
							{/if}
							{#if b.size != null}
								<div>{formatBytes(b.size)}</div>
							{/if}
						</div>
						<div class="order-4 justify-self-end">
							<DropdownMenu.Root>
								<DropdownMenu.Trigger>
									{#snippet child({ props })}
										<Button {...props} variant="ghost" size="icon" class="size-7">
											<Ellipsis class="size-4" />
											<span class="sr-only">Actions for {b.name}</span>
										</Button>
									{/snippet}
								</DropdownMenu.Trigger>
								<DropdownMenu.Content align="end" class="w-44">
									{#if current !== ReviewState.CONFIRMED}
										<DropdownMenu.Item onclick={() => setReview(b, ReviewState.CONFIRMED)}>
											<Check class="size-3.5" /> Confirm
										</DropdownMenu.Item>
									{/if}
									{#if current !== ReviewState.IGNORED}
										<DropdownMenu.Item onclick={() => setReview(b, ReviewState.IGNORED)}>
											<EyeOff class="size-3.5" /> Ignore
										</DropdownMenu.Item>
									{/if}
									{#if current !== ReviewState.OPEN}
										<DropdownMenu.Item onclick={() => setReview(b, ReviewState.OPEN)}>
											<RotateCcw class="size-3.5" /> Reopen
										</DropdownMenu.Item>
									{/if}
									<DropdownMenu.Separator />
									<DropdownMenu.Item onclick={() => copy(b.url)}>
										<Copy class="size-3.5" /> Copy URL
									</DropdownMenu.Item>
								</DropdownMenu.Content>
							</DropdownMenu.Root>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
