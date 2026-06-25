<script lang="ts">
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Network from '@lucide/svelte/icons/network';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { SCAN_CHANGE_WINDOWS, type ScanChanges, type ScanChangeWindow } from '$lib/types/scan';

	interface Props {
		changes: ScanChanges | null;
		window: ScanChangeWindow;
		onWindow: (w: ScanChangeWindow) => void;
	}

	let { changes, window, onWindow }: Props = $props();
</script>

<div class="rounded-lg border border-border p-4">
	<div class="mb-3 flex items-center justify-between gap-2">
		<div class="flex items-center gap-1.5 text-sm font-medium">
			<Sparkles class="h-4 w-4 text-muted-foreground" />
			What changed
		</div>
		<div class="flex items-center gap-0.5 rounded-md border border-border p-0.5">
			{#each SCAN_CHANGE_WINDOWS as w (w.key)}
				<button
					type="button"
					class="rounded px-2 py-0.5 text-xs tabular-nums transition-colors {window === w.key
						? 'bg-muted font-medium text-foreground'
						: 'text-muted-foreground hover:text-foreground'}"
					onclick={() => onWindow(w.key)}
				>
					{w.label}
				</button>
			{/each}
		</div>
	</div>

	{#if !changes}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each Array(4) as _, i (i)}
				<div class="space-y-1.5"><Skeleton class="h-7 w-12" /><Skeleton class="h-3 w-20" /></div>
			{/each}
		</div>
	{:else}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<div class="space-y-0.5">
				<div
					class="flex items-center gap-1.5 text-2xl font-semibold tabular-nums {changes.new_subdomains >
					0
						? 'text-warning'
						: ''}"
				>
					<Network class="h-4 w-4 opacity-60" />
					{changes.new_subdomains > 0 ? '+' : ''}{changes.new_subdomains}
				</div>
				<div class="text-xs text-muted-foreground">New subdomains</div>
			</div>

			<div class="space-y-0.5">
				<div class="flex items-center gap-1.5 text-2xl font-semibold tabular-nums">
					<Crosshair class="h-4 w-4 opacity-60" />
					{changes.targets_changed}
				</div>
				<div class="text-xs text-muted-foreground">Targets changed</div>
			</div>

			<div class="space-y-0.5">
				<div class="flex items-center gap-1.5 text-2xl font-semibold tabular-nums">
					<Play class="h-4 w-4 opacity-60" />
					{changes.scans_run}
				</div>
				<div class="text-xs text-muted-foreground">Scans run</div>
			</div>

			<div class="space-y-0.5">
				<div
					class="flex items-center gap-1.5 text-2xl font-semibold tabular-nums {changes.failed_runs >
					0
						? 'text-destructive'
						: ''}"
				>
					<Ban class="h-4 w-4 opacity-60" />
					{changes.failed_runs}
				</div>
				<div class="text-xs text-muted-foreground">Failed / cancelled</div>
			</div>
		</div>
	{/if}
</div>
