<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import SettingRow from './setting-row.svelte';
	import { BODY_ROW, CALL_COL, HEAD_ROW, USAGE_COL } from './columns';
	import { ai } from '$lib/stores/ai.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import {
		CALLS_PAGE,
		RECENT_CALLS,
		cacheHint,
		callCursor,
		costHint,
		formatCost,
		unpricedLabel
	} from '$lib/config/ai';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import type { AiCall } from '$lib/types/ai';

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	let calls = $state<AiCall[] | null>(null);
	let hasMore = $state(false);
	let loadingMore = $state(false);
	let generation = 0;
	let clearOpen = $state(false);
	let clearing = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const status = $derived(ai.status);
	const usage = $derived(status?.usage ?? null);
	const cached = $derived(status?.cached_narratives ?? 0);

	$effect(() => {
		if (!open) return;
		untrack(() => {
			const mine = ++generation;
			calls = null;
			hasMore = false;
			void ai.refreshStatus();
			ai.calls(RECENT_CALLS)
				.then((page) => {
					if (mine !== generation) return;
					calls = page.items;
					hasMore = page.has_more;
				})
				.catch(() => {
					if (mine === generation) calls = [];
				});
		});
	});

	async function showMore() {
		const last = calls?.at(-1);
		if (!last) return;
		const mine = generation;
		loadingMore = true;
		try {
			const page = await ai.calls(CALLS_PAGE, callCursor(last));
			if (mine !== generation) return;
			calls = [...(calls ?? []), ...page.items];
			hasMore = page.has_more;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Calls not loaded');
		} finally {
			loadingMore = false;
		}
	}

	function tokens(n: number): string {
		return n.toLocaleString();
	}

	function featureLabel(feature: string): string {
		return usage?.by_feature.find((f) => f.feature === feature)?.label ?? feature;
	}

	function providerLabel(provider: string): string {
		return ai.provider(provider)?.label ?? provider;
	}

	async function clearCache() {
		clearing = true;
		try {
			const removed = await ai.clearCache();
			if (removed === null) return;
			toast.success(`${removed.toLocaleString()} cached narratives removed`);
			clearOpen = false;
		} finally {
			clearing = false;
		}
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-3xl">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>Usage</Sheet.Title>
			{#if usage?.since}
				<Sheet.Description class="tabular-nums">
					Since {formatShortDate(usage.since)}
				</Sheet.Description>
			{/if}
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col pb-4">
				<section class="flex flex-col">
					<div class="px-5 pt-5 pb-2"><SectionHead title="By feature" /></div>
					{#if usage?.by_feature.length}
						<div
							class="@container/usage w-full border-t"
							role="table"
							aria-label="Usage by feature"
						>
							<div class={HEAD_ROW} role="row">
								<div class={USAGE_COL.feature}>Feature</div>
								<div class={USAGE_COL.calls}>Calls</div>
								<div class={USAGE_COL.cached}>Cached</div>
								<div class={USAGE_COL.failed}>Failed</div>
								<div class={USAGE_COL.input}>Input tokens</div>
								<div class={USAGE_COL.output}>Output tokens</div>
								<div class={USAGE_COL.cost}>Cost</div>
							</div>
							{#each usage.by_feature as f (f.feature)}
								<div class="{BODY_ROW} text-sm" role="row">
									<div class={USAGE_COL.feature}>{f.label}</div>
									<div class="{USAGE_COL.calls} tabular-nums">{f.calls.toLocaleString()}</div>
									<div class="{USAGE_COL.cached} tabular-nums text-muted-foreground">
										{f.cached.toLocaleString()}
									</div>
									<div
										class="{USAGE_COL.failed} tabular-nums {f.failed
											? 'text-destructive'
											: 'text-muted-foreground'}"
									>
										{f.failed.toLocaleString()}
									</div>
									<Hint text={cacheHint(f.cache_read_tokens, f.cache_write_tokens)}>
										{#snippet child(props)}
											<div {...props} class="{USAGE_COL.input} font-mono text-xs tabular-nums">
												{tokens(f.input_tokens)}
											</div>
										{/snippet}
									</Hint>
									<div class="{USAGE_COL.output} font-mono text-xs tabular-nums">
										{tokens(f.output_tokens)}
									</div>
									<Hint text={unpricedLabel(f.unpriced)}>
										{#snippet child(props)}
											<div {...props} class="{USAGE_COL.cost} tabular-nums">
												{formatCost(f.cost_usd)}
											</div>
										{/snippet}
									</Hint>
								</div>
							{/each}
						</div>
					{:else}
						<p class="px-5 pb-2 text-sm text-muted-foreground">No calls</p>
					{/if}
				</section>

				<section class="mt-4 flex flex-col">
					<SettingRow label="Cached narratives" class="border-y">
						<span class="text-sm tabular-nums">{cached.toLocaleString()}</span>
						<Button
							variant="outline"
							size="sm"
							disabled={!isAdmin || !cached}
							onclick={() => (clearOpen = true)}
						>
							Clear
						</Button>
					</SettingRow>
				</section>

				<section class="mt-4 flex flex-col">
					<div class="px-5 pt-1 pb-2"><SectionHead title="Recent calls" /></div>
					{#if calls === null}
						<div class="flex flex-col gap-2 px-5">
							<Skeleton class="h-8 w-full" />
							<Skeleton class="h-8 w-full" />
							<Skeleton class="h-8 w-full" />
						</div>
					{:else if calls.length}
						<div class="@container/calls w-full border-t" role="table" aria-label="Recent calls">
							<div class={HEAD_ROW} role="row">
								<div class={CALL_COL.when}>When</div>
								<div class={CALL_COL.feature}>Feature</div>
								<div class={CALL_COL.model}>Model</div>
								<div class={CALL_COL.input}>Input tokens</div>
								<div class={CALL_COL.output}>Output tokens</div>
								<div class={CALL_COL.cost}>Cost</div>
								<div class={CALL_COL.outcome}>Outcome</div>
							</div>
							{#each calls as call (call.id)}
								<div class="{BODY_ROW} text-sm" role="row">
									<div class="{CALL_COL.when} text-muted-foreground tabular-nums">
										{relativeTime(call.at)}
									</div>
									<div class={CALL_COL.feature}>{featureLabel(call.feature)}</div>
									<div class="{CALL_COL.model} font-mono text-xs wrap-anywhere">{call.model}</div>
									<Hint text={cacheHint(call.cache_read_tokens, call.cache_write_tokens)}>
										{#snippet child(props)}
											<div {...props} class="{CALL_COL.input} font-mono text-xs tabular-nums">
												{tokens(call.input_tokens)}
											</div>
										{/snippet}
									</Hint>
									<div class="{CALL_COL.output} font-mono text-xs tabular-nums">
										{tokens(call.output_tokens)}
									</div>
									<Hint text={costHint(call, providerLabel(call.provider))}>
										{#snippet child(props)}
											<div {...props} class="{CALL_COL.cost} tabular-nums">
												{formatCost(call.cost_usd)}
											</div>
										{/snippet}
									</Hint>
									<div class={CALL_COL.outcome}>
										{#if call.cached}
											<span class="text-muted-foreground">Cached</span>
										{:else if call.ok}
											OK
										{:else}
											<Hint text={call.error}>
												{#snippet child(props)}
													<span {...props} class="text-destructive">Failed</span>
												{/snippet}
											</Hint>
										{/if}
									</div>
								</div>
							{/each}
						</div>
						{#if hasMore}
							<div class="border-t px-5 py-2.5">
								<LoadingButton
									variant="ghost"
									size="sm"
									loading={loadingMore}
									loadingLabel="Show more"
									onclick={() => showMore()}
								>
									Show more
								</LoadingButton>
							</div>
						{/if}
					{:else}
						<p class="px-5 text-sm text-muted-foreground">No calls</p>
					{/if}
				</section>
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	open={clearOpen}
	title="Clear cached narratives"
	description={`${cached.toLocaleString()} cached narratives are removed.`}
	confirmLabel="Clear"
	destructive
	loading={clearing}
	onOpenChange={(value) => {
		if (!value) clearOpen = false;
	}}
	onConfirm={clearCache}
/>
