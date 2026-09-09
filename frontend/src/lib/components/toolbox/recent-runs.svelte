<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import { TONE_DOT } from '$lib/config/toolbox';
	import { relativeTime } from '$lib/utilities/dates';
	import { cn } from '$lib/utils';
	import type { ToolRun } from '$lib/types/toolbox';

	interface Props {
		runs: ToolRun[];
		activeId: string | null;
		limit?: number;
		onOpen: (run: ToolRun) => void;
		onClear: () => void;
	}

	let { runs, activeId, limit = 6, onOpen, onClear }: Props = $props();

	const shown = $derived.by(() => {
		const seen: Record<string, true> = {};
		return runs
			.filter((r) => {
				const key = `${r.tool}:${r.label}`;
				if (seen[key]) return false;
				seen[key] = true;
				return true;
			})
			.slice(0, limit);
	});
</script>

{#if shown.length}
	<div class="shrink-0 border-t p-2">
		<div class="flex items-center justify-between px-2 pb-1">
			<p class="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Recent</p>
			<Hint text="Runs are kept for seven days">
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<Button
							variant="ghost"
							size="sm"
							class="h-5 px-1.5 text-[11px] text-muted-foreground"
							onclick={onClear}
						>
							Clear
						</Button>
					</span>
				{/snippet}
			</Hint>
		</div>
		{#each shown as run (run.id)}
			<button
				type="button"
				onclick={() => onOpen(run)}
				class={cn(
					'flex w-full items-center gap-2 rounded-md px-2 py-1 text-left transition-colors',
					activeId === run.id ? 'bg-accent' : 'hover:bg-accent/50'
				)}
			>
				<span
					class="size-1.5 shrink-0 rounded-full {run.status === 'failed'
						? TONE_DOT.critical
						: TONE_DOT.muted}"
				></span>
				<span class="min-w-0 flex-1 truncate font-mono text-[11px]">{run.label}</span>
				<span class="shrink-0 text-[10px] text-muted-foreground">
					{relativeTime(run.finished_at ?? run.queued_at)}
				</span>
			</button>
		{/each}
	</div>
{/if}
