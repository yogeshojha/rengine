<script lang="ts">
	import { untrack } from 'svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import SectionHead from '$lib/components/section-head.svelte';
	import { tripwiresApi } from '$lib/api/tripwires';
	import { RECENT_DAYS } from '$lib/config/tripwires';
	import type { DailyPreview, DailyPreviewRequest } from '$lib/types/tripwire';
	import { formatShortDate } from '$lib/utilities/dates';

	interface Props {
		projectId: string;
		request: DailyPreviewRequest;
		/** The targets the check reads, or the recent changes it fires on. */
		part: 'read' | 'history';
		enabled?: boolean;
	}

	let { projectId, request, part, enabled = true }: Props = $props();

	const DEBOUNCE_MS = 300;
	const SHOWN_CHANGES = 5;
	const SHOWN_ROWS = 3;

	let preview = $state<DailyPreview | null>(null);
	let loading = $state(false);
	let failure = $state<string | null>(null);
	let seq = 0;

	let signature = $derived(JSON.stringify(request));
	let unread = $derived(preview ? preview.targets - preview.read : 0);
	let waiting = $derived(preview ? preview.read - preview.reported : 0);
	let plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

	$effect(() => {
		void signature;
		const on = enabled;
		return untrack(() => {
			if (!on) {
				preview = null;
				failure = null;
				return;
			}
			const mine = ++seq;
			loading = true;
			const timer = setTimeout(async () => {
				try {
					const result = await tripwiresApi.dailyPreview(projectId, request);
					if (mine !== seq) return;
					preview = result;
					failure = null;
				} catch (e) {
					if (mine !== seq) return;
					preview = null;
					failure = e instanceof Error ? e.message : 'Preview not loaded';
				} finally {
					if (mine === seq) loading = false;
				}
			}, DEBOUNCE_MS);
			return () => clearTimeout(timer);
		});
	});
</script>

{#if part === 'read'}
	<div class="flex flex-col gap-3 rounded-lg border bg-muted/20 p-4">
		<SectionHead title="Targets read" />
		{#if loading && !preview}
			<Skeleton class="h-4 w-40" />
			<Skeleton class="h-4 w-2/3" />
		{:else if failure}
			<p class="text-xs text-destructive">{failure}</p>
		{:else if preview}
			<p class="text-sm">
				<span class="font-semibold tabular-nums">{preview.read.toLocaleString()}</span>
				<span class="text-muted-foreground">
					of {preview.targets.toLocaleString()}
					{plural(preview.targets, 'target', 'targets')} in scope
				</span>
			</p>
			{#if preview.off_reason}
				<p class="text-xs text-destructive">{preview.off_reason}</p>
			{/if}
			{#if unread > 0}
				<p class="text-xs text-muted-foreground">
					{unread.toLocaleString()}
					{plural(unread, 'target has', 'targets have')} no registrable domain
				</p>
			{/if}
			{#if waiting > 0}
				<p class="text-xs text-muted-foreground">
					{waiting.toLocaleString()}
					{plural(waiting, 'target', 'targets')} not looked up
				</p>
			{/if}
		{/if}
	</div>
{:else}
	<div class="flex min-w-0 flex-col gap-3 rounded-lg border bg-muted/20 p-4">
		<SectionHead title="Last {preview?.days ?? RECENT_DAYS} days" />
		{#if loading && !preview}
			<Skeleton class="h-4 w-40" />
			<Skeleton class="h-4 w-full" />
		{:else if preview}
			<p class="text-sm">
				<span class="font-semibold tabular-nums"
					>{preview.changes.length}{preview.capped ? '+' : ''}</span
				>
				<span class="text-muted-foreground">
					{plural(preview.changes.length, 'change', 'changes')} would have fired
				</span>
			</p>
			{#if preview.changes.length > 0}
				<div class="flex flex-col divide-y divide-border/60">
					{#each preview.changes.slice(0, SHOWN_CHANGES) as change, i (i)}
						<div class="flex min-w-0 flex-col gap-0.5 py-1.5 text-2xs">
							<span class="flex items-baseline justify-between gap-2">
								<span class="truncate font-mono">{change.target_value}</span>
								<span class="shrink-0 text-muted-foreground"
									>{formatShortDate(change.checked_at)}</span
								>
							</span>
							{#each change.rows.slice(0, SHOWN_ROWS) as row (row.key)}
								<span class="truncate text-muted-foreground">{row.label} · {row.detail}</span>
							{/each}
							{#if change.fired > SHOWN_ROWS}
								<span class="text-muted-foreground">and {change.fired - SHOWN_ROWS} more</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
{/if}
