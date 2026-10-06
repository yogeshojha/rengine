<script lang="ts">
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ScopeBar from '$lib/components/dashboard/scope-bar.svelte';
	import EstateComposer from './estate-composer.svelte';
	import ScanPicker from './scan-picker.svelte';
	import AskOff from './ask-off.svelte';
	import { blockHref } from './block-columns';
	import { surfaceSpec } from '$lib/config/surface';
	import { relativeTime } from '$lib/utilities/dates';
	import type { TargetScope } from '$lib/utilities/surface-scope';
	import type { EstateStarter, EstateStarters, EstateStatus, EstateThread } from '$lib/types/ask';

	const RECENT = 4;

	interface Props {
		status: EstateStatus | null;
		starters: EstateStarters | null;
		startersLoading: boolean;
		recent: EstateThread[];
		projectId: string;
		projectSlug: string;
		scope: TargetScope;
		scanId: string | null;
		intelligent: boolean;
		admin: boolean;
		busy: boolean;
		prefill?: string;
		onScope: (scope: TargetScope) => void;
		onScan: (id: string | null) => void;
		onIntelligent: (on: boolean) => void;
		onAsk: (text: string) => void;
		onStarter: (starter: EstateStarter) => void;
		onStop?: () => void;
		onOpen: (id: string) => void;
		onHistory: () => void;
	}

	let {
		status,
		starters,
		startersLoading,
		recent,
		projectId,
		projectSlug,
		scope,
		scanId,
		intelligent,
		admin,
		busy,
		prefill = '',
		onScope,
		onScan,
		onIntelligent,
		onAsk,
		onStarter,
		onStop,
		onOpen,
		onHistory
	}: Props = $props();

	let composer = $state<EstateComposer | null>(null);
	let available = $derived(status?.available ?? false);
	let offline = $derived(status !== null && !status.available);
	let scopeValues = $derived(starters?.filtered ? starters.scope_values : null);

	$effect(() => {
		if (!available || !composer) return;
		if (prefill) composer.fill(prefill);
		else composer.focus();
	});

	function noun(dimension: string, count: number): string {
		const spec = surfaceSpec(dimension);
		return (count === 1 ? spec?.noun : spec?.nounPlural) ?? '';
	}
</script>

{#snippet filters()}
	<ScopeBar {projectSlug} {scope} known={[]} onChange={onScope} />
	<ScanPicker {projectId} {scope} selected={scanId} onChange={onScan} />
{/snippet}

<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 pt-[9vh] pb-10">
	<div class="flex justify-center">
		{#if starters}
			<p
				class="ask-rise m-0 flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm text-muted-foreground"
			>
				<span
					><b class="font-semibold text-foreground tabular-nums">{starters.targets}</b>
					{starters.targets === 1 ? 'target' : 'targets'}</span
				>
				{#each starters.vitals as v (v.dimension)}
					<span
						><b class="font-semibold text-foreground tabular-nums"
							>{v.count.toLocaleString()}{v.capped ? '+' : ''}</b
						>
						{noun(v.dimension, v.count)}</span
					>
				{/each}
			</p>
		{:else if startersLoading}
			<Skeleton class="h-5 w-80" />
		{/if}
	</div>

	<div class="ask-composer">
		<EstateComposer
			bind:this={composer}
			hero
			{intelligent}
			{busy}
			sendable={available}
			placeholder={starters?.example ?? undefined}
			leading={filters}
			{onIntelligent}
			onSend={onAsk}
			{onStop}
		/>
	</div>
	{#if status && !available}
		<AskOff reason={status.off_reason ?? ''} code={status.off_code} {admin} />
	{/if}

	{#if startersLoading && !starters}
		<div class="grid gap-2 sm:grid-cols-2">
			{#each { length: 4 } as _, i (i)}
				<Skeleton class="h-10 rounded-xl" />
			{/each}
		</div>
	{:else if starters?.starters.length}
		<div
			class="ask-rise grid gap-2 sm:grid-cols-2"
			role="group"
			aria-label="Questions with answers"
		>
			{#each starters.starters as s (s.key)}
				{@const href = offline ? blockHref(s.dimension, s.query, scopeValues, scanId) : null}
				{#snippet body()}
					<span class="min-w-0 flex-1 text-sm leading-5">{s.question}</span>
					<span class="shrink-0 text-sm font-semibold tabular-nums"
						>{s.count.toLocaleString()}{s.capped ? '+' : ''}</span
					>
				{/snippet}
				{#if href}
					<a
						href={startersLoading ? undefined : href}
						aria-disabled={startersLoading}
						class="flex items-center gap-3 rounded-xl border bg-card/80 px-3.5 py-2.5 text-left backdrop-blur hover:border-primary/30 hover:bg-card aria-disabled:opacity-60"
					>
						{@render body()}
					</a>
				{:else}
					<button
						type="button"
						disabled={busy || startersLoading || !available}
						class="flex items-center gap-3 rounded-xl border bg-card/80 px-3.5 py-2.5 text-left backdrop-blur hover:border-primary/30 hover:bg-card disabled:opacity-60"
						onclick={() => onStarter(s)}
					>
						{@render body()}
					</button>
				{/if}
			{/each}
		</div>
	{/if}

	{#if recent.length}
		<section class="flex flex-col gap-1.5 pt-2" aria-label="Recent questions">
			<div class="flex items-center justify-between px-1">
				<span class="text-2xs font-medium tracking-wide text-muted-foreground uppercase"
					>Recent</span
				>
				<button
					type="button"
					class="text-xs text-muted-foreground hover:text-foreground"
					onclick={onHistory}>History</button
				>
			</div>
			<ul class="flex flex-col">
				{#each recent.slice(0, RECENT) as t (t.id)}
					<li>
						<button
							type="button"
							class="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left hover:bg-muted/60"
							onclick={() => onOpen(t.id)}
						>
							<MessagesSquare class="size-3.5 shrink-0 text-muted-foreground" />
							<span class="min-w-0 flex-1 truncate text-sm">{t.title}</span>
							<span class="shrink-0 text-xs text-muted-foreground tabular-nums"
								>{relativeTime(t.last_at)}</span
							>
						</button>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>
