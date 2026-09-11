<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import Search from '@lucide/svelte/icons/search';
	import { Label } from '$lib/components/ui/label';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import type { RunPreview } from '$lib/types/recheck';

	interface Props {
		assets: string[];
		queryLabel?: string;
		preview: RunPreview | null;
		loading?: boolean;
		disabled?: boolean;
		onRemove?: (asset: string) => void;
	}

	let {
		assets,
		queryLabel,
		preview,
		loading = false,
		disabled = false,
		onRemove
	}: Props = $props();

	let noun = $derived(
		preview && preview.asset_count === 1 ? preview.seed_kind : `${preview?.seed_kind ?? 'asset'}s`
	);
	let byQuery = $derived(Boolean(queryLabel));
</script>

<div class="flex flex-col gap-2">
	<Label>
		Assets
		<span class="ml-1 font-normal text-muted-foreground">
			{byQuery ? 'matched by search' : 'from the run that found them'}
		</span>
	</Label>

	{#if byQuery}
		<div class="rounded-md border bg-muted/20 p-2">
			<div class="flex items-center gap-2 font-mono text-xs">
				<Search class="size-3.5 shrink-0 text-muted-foreground" />
				<span class="min-w-0 truncate">{queryLabel}</span>
			</div>
		</div>
	{:else}
		<ScrollArea class="max-h-32 rounded-md border bg-muted/20">
			<div class="flex flex-wrap gap-1.5 p-2">
				{#each assets as asset (asset)}
					<span
						class="inline-flex items-center gap-1.5 rounded-md border bg-background py-0.5 pr-1 pl-2 font-mono text-xs"
					>
						{asset}
						{#if onRemove}
							<button
								type="button"
								class="rounded-sm px-0.5 text-muted-foreground hover:text-foreground"
								aria-label="Remove {asset}"
								{disabled}
								onclick={() => onRemove(asset)}
							>
								<X class="size-3" />
							</button>
						{/if}
					</span>
				{/each}
			</div>
		</ScrollArea>
	{/if}

	{#if loading && !preview}
		<Skeleton class="h-4 w-52" />
	{:else if preview}
		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
			<span class="font-medium text-foreground tabular-nums">
				{preview.asset_count.toLocaleString()}
				{noun}
			</span>
			{#if preview.target_count > 1}
				<span>·</span>
				<span>{preview.target_count} targets</span>
			{/if}
			{#if preview.capped}
				<span>·</span>
				<span class="text-warning">
					{preview.matched === null
						? `Capped at ${preview.asset_count.toLocaleString()}`
						: `Capped at ${preview.asset_count.toLocaleString()} of ${preview.matched.toLocaleString()}`}
				</span>
			{/if}
		</div>
		{#if preview.targets.length > 1}
			<ScrollArea class="max-h-24">
				<div class="flex flex-wrap gap-1">
					{#each preview.targets as t (t.target_id)}
						<span
							class="inline-flex items-center gap-1.5 rounded border bg-background px-1.5 py-0.5 text-xs"
						>
							<span class="font-mono">{t.target_value}</span>
							<span class="text-muted-foreground tabular-nums">{t.count.toLocaleString()}</span>
						</span>
					{/each}
				</div>
			</ScrollArea>
		{/if}
	{/if}
</div>
