<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { ROUTES } from '$lib/config/routes';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import type { Recheck } from '$lib/types/recheck';
	import { relativeTime } from '$lib/utilities/dates';
	import { isRecheckLive, recheckFailed } from '$lib/utilities/rechecks';

	interface Props {
		scanId: string;
		assetKey: string;
	}

	let { scanId, assetKey }: Props = $props();

	let entries = $derived(rechecks.history(scanId, assetKey));

	const dot = (r: Recheck) =>
		isRecheckLive(r)
			? 'bg-primary animate-pulse'
			: recheckFailed(r)
				? 'bg-destructive'
				: r.changed
					? 'bg-primary'
					: 'bg-muted-foreground/50';

	const seconds = (n: number | null) =>
		n == null ? '' : n < 60 ? `${Math.round(n)}s` : `${Math.floor(n / 60)}m ${Math.round(n % 60)}s`;
</script>

{#if entries.length}
	<div class="flex flex-col">
		{#each entries as entry (entry.scan_id + entry.asset_key)}
			<div class="border-b px-1 py-3 last:border-b-0">
				<div class="flex flex-wrap items-center gap-2 text-[13px]">
					<span class="flex h-5 shrink-0 items-center">
						<span class="size-2 rounded-full {dot(entry)}"></span>
					</span>
					<span class="font-medium">
						{isRecheckLive(entry) ? 'Rechecking now' : relativeTime(entry.created_at)}
					</span>
					{#if isRecheckLive(entry)}
						<RefreshCw class="size-3 animate-spin text-primary" />
					{:else if recheckFailed(entry)}
						<span class="text-xs font-medium text-destructive">recheck failed</span>
					{:else if entry.changed}
						<span
							class="rounded-full border border-primary/40 bg-primary/10 px-[7px] text-[11px] font-semibold text-primary"
						>
							{entry.changes.length}
							{entry.changes.length === 1 ? 'change' : 'changes'}
						</span>
					{:else}
						<span class="text-xs text-muted-foreground">no change</span>
					{/if}
					<span class="ml-auto text-xs text-muted-foreground">
						{entry.stage_titles.join(' · ')}{entry.duration_seconds != null
							? ` · ${seconds(entry.duration_seconds)}`
							: ''}
					</span>
				</div>

				{#if entry.changes.length}
					<dl class="mt-2 grid grid-cols-[6rem_minmax(0,1fr)] gap-x-3 gap-y-1 pl-4">
						{#each entry.changes as change (change.field)}
							<dt class="text-xs text-muted-foreground">{change.label}</dt>
							<dd class="font-mono text-xs break-all">
								{#if change.before && change.after}
									<span class="text-muted-foreground line-through">{change.before}</span>
									<span class="px-1 text-muted-foreground">→</span>
									<span class="font-medium">{change.after}</span>
								{:else if change.after}
									<span class="font-medium">{change.after}</span>
								{:else}
									<span class="text-muted-foreground">gone</span>
								{/if}
							</dd>
						{/each}
					</dl>
				{/if}

				{#if !isRecheckLive(entry)}
					<a
						href={ROUTES.scan(entry.scan_id)}
						class="mt-2 ml-4 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
					>
						Open focused scan <ArrowUpRight class="size-3" />
					</a>
				{/if}
			</div>
		{/each}
	</div>
{/if}
