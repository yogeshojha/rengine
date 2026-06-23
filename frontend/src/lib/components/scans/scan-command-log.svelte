<script lang="ts">
	import { ChevronRight } from 'lucide-svelte';

	import * as Collapsible from '$lib/components/ui/collapsible';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { scansApi } from '$lib/api/scans';
	import {
		activityStatusIcon,
		activityStatusClass,
		durationText
	} from '$lib/utilities/scan-status';
	import type { ScanCommandRead, ScanCommandDetail } from '$lib/types/scan';

	interface Props {
		scanId: string;
		projectId: string;
		commands: ScanCommandRead[];
	}

	let { scanId, projectId, commands }: Props = $props();

	let outputs = $state<Record<string, string | null>>({});
	let loadingId = $state<string | null>(null);

	async function loadOutput(id: string) {
		if (id in outputs || loadingId === id) return;
		loadingId = id;
		try {
			const detail: ScanCommandDetail = await scansApi.command(scanId, id, projectId);
			outputs[id] = detail.output ?? '';
		} catch {
			outputs[id] = null;
		} finally {
			loadingId = null;
		}
	}
</script>

<div class="space-y-1.5">
	{#each commands as c (c.id)}
		{@const Icon = activityStatusIcon(c.status)}
		<Collapsible.Root onOpenChange={(open) => open && loadOutput(c.id)}>
			<Collapsible.Trigger
				class="group flex w-full items-center gap-2 rounded-md border border-border px-3 py-2 text-left hover:bg-muted/40"
			>
				<ChevronRight
					class="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-90"
				/>
				<Icon
					class="h-3.5 w-3.5 shrink-0 {activityStatusClass(c.status)} {c.status === 'running'
						? 'animate-spin'
						: ''}"
				/>
				<span class="shrink-0 font-mono text-xs font-medium">{c.tool}</span>
				<span class="truncate font-mono text-xs text-muted-foreground">{c.command}</span>
				<span class="ml-auto flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
					{#if c.return_code != null}<span class="tabular-nums">rc {c.return_code}</span>{/if}
					{#if durationText(c.duration_seconds, true)}<span class="tabular-nums"
							>{durationText(c.duration_seconds, true)}</span
						>{/if}
				</span>
			</Collapsible.Trigger>
			<Collapsible.Content>
				<div
					class="mt-1 rounded-md border border-border bg-muted/30"
					role="region"
					aria-label="{c.tool} output"
				>
					{#if loadingId === c.id}
						<p class="p-3 text-xs text-muted-foreground">Loading output…</p>
					{:else if outputs[c.id] === null}
						<p class="p-3 text-xs text-destructive">Failed to load output.</p>
					{:else if outputs[c.id]}
						<ScrollArea class="h-64">
							<pre
								class="whitespace-pre-wrap break-all p-3 font-mono text-xs leading-relaxed">{outputs[
									c.id
								]}</pre>
						</ScrollArea>
					{:else}
						<p class="p-3 text-xs text-muted-foreground">No output captured.</p>
					{/if}
				</div>
			</Collapsible.Content>
		</Collapsible.Root>
	{/each}
</div>
