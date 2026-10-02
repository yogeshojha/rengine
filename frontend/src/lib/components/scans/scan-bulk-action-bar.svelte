<script lang="ts">
	import GitCompareArrows from '@lucide/svelte/icons/git-compare-arrows';
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import { plural } from '$lib/utilities/strings';

	interface Props {
		selectedCount: number;
		liveCount: number;
		targetCount: number;
		compareHref?: string | null;
		compareReason?: string;
		onRescan: () => void;
		onCancel: () => void;
		onDelete: () => void;
		onClear: () => void;
	}

	let {
		selectedCount,
		liveCount,
		targetCount,
		compareHref = null,
		compareReason = '',
		onRescan,
		onCancel,
		onDelete,
		onClear
	}: Props = $props();
</script>

<SelectionActionBar {selectedCount} noun="scan" {onClear}>
	{#if compareHref}
		<Button variant="ghost" size="sm" class="gap-2 font-medium" href={compareHref}>
			<GitCompareArrows class="h-3.5 w-3.5 text-muted-foreground" />
			Compare runs
		</Button>
	{:else if compareReason}
		<Hint text={compareReason}>
			{#snippet child(props)}
				<span {...props} class="inline-flex">
					<Button
						variant="ghost"
						size="sm"
						class="gap-2 font-medium"
						disabled
						aria-label="Compare runs. {compareReason}"
					>
						<GitCompareArrows class="h-3.5 w-3.5" />
						Compare runs
					</Button>
				</span>
			{/snippet}
		</Hint>
	{/if}

	{#if targetCount > 0}
		<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={onRescan}>
			<Play class="h-3.5 w-3.5 text-muted-foreground" />
			Re-scan {plural(targetCount, 'target')}
		</Button>
	{/if}

	{#if liveCount > 0}
		<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={onCancel}>
			<Ban class="h-3.5 w-3.5 text-muted-foreground" />
			Cancel {liveCount}
		</Button>
	{/if}

	<Button
		variant="ghost"
		size="sm"
		class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
		onclick={onDelete}
	>
		<Trash2 class="h-3.5 w-3.5" />
		Delete
	</Button>
</SelectionActionBar>
