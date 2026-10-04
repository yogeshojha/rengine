<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { TONE_DOT } from '$lib/config/toolbox';
	import { relativeTime } from '$lib/utilities/dates';
	import { cn } from '$lib/utils';
	import type { ToolRun } from '$lib/types/toolbox';

	interface Props {
		runs: ToolRun[];
		activeId: string | null;
		limit?: number;
		error?: string | null;
		class?: string;
		onOpen: (run: ToolRun) => void;
		onClear: () => Promise<void>;
	}

	let {
		runs,
		activeId,
		limit = 6,
		error = null,
		class: className,
		onOpen,
		onClear
	}: Props = $props();

	let confirming = $state(false);
	let clearing = $state(false);

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

	async function clear() {
		clearing = true;
		try {
			await onClear();
			confirming = false;
		} catch {
			toast.error('Runs not cleared');
		} finally {
			clearing = false;
		}
	}
</script>

{#if !shown.length && error}
	<div class={cn('shrink-0 border-t p-2', className)}>
		<p class="px-2 py-1 text-2xs text-muted-foreground">Recent runs not loaded.</p>
	</div>
{:else if shown.length}
	<div class={cn('shrink-0 border-t p-2', className)}>
		<div class="flex items-center justify-between px-2 pb-1">
			<p class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">Recent</p>
			<Hint text="Runs are kept for seven days">
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<Button
							variant="ghost"
							size="sm"
							class="h-5 px-1.5 text-2xs text-muted-foreground"
							onclick={() => (confirming = true)}
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
				<span class="min-w-0 flex-1 truncate font-mono text-2xs">{run.label}</span>
				<span class="shrink-0 text-2xs text-muted-foreground">
					{relativeTime(run.finished_at ?? run.queued_at)}
				</span>
			</button>
		{/each}
	</div>
{/if}

<ConfirmDialog
	open={confirming}
	title="Clear recent runs"
	description="Toolbox runs and their results are removed."
	confirmLabel="Clear"
	destructive
	loading={clearing}
	loadingLabel="Clearing"
	onOpenChange={(next) => {
		if (!clearing) confirming = next;
	}}
	onConfirm={clear}
/>
