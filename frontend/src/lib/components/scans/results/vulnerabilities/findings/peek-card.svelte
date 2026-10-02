<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { SEVERITY_CHIP } from '$lib/config/vulnerabilities';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import { peek } from './peek';

	const PREVIEW = 6;

	interface Props {
		projectId: string;
		scanId: string;
		q: string;
		title: string;
		total: number;
		exclude?: string;
		line: (v: VulnerabilityRead) => { main: string; sub: string };
		onPick: (v: VulnerabilityRead) => void;
		trigger: Snippet<[Record<string, unknown>]>;
		footer?: Snippet;
	}

	let { projectId, scanId, q, title, total, exclude, line, onPick, trigger, footer }: Props =
		$props();

	let items = $state<VulnerabilityRead[] | null>(null);
	let failed = $state(false);

	function load() {
		failed = false;
		peek(projectId, scanId, q, PREVIEW + 1)
			.then((r) => (items = r.items.filter((v) => v.id !== exclude).slice(0, PREVIEW)))
			.catch(() => (failed = true));
	}
</script>

<HoverCard.Root openDelay={250} closeDelay={80} onOpenChange={(o) => o && load()}>
	<HoverCard.Trigger>
		{#snippet child({ props })}
			{@render trigger(props)}
		{/snippet}
	</HoverCard.Trigger>
	<HoverCard.Content class="w-96 p-0" align="start">
		<div class="border-b px-3 py-2 text-xs font-medium">{title}</div>
		{#if failed}
			<p class="px-3 py-3 text-xs text-muted-foreground">Findings not loaded.</p>
		{:else if !items}
			<div class="space-y-2 px-3 py-3">
				{#each { length: Math.min(Math.max(total, 1), 3) } as _, i (i)}
					<Skeleton class="h-3.5 w-full" />
				{/each}
			</div>
		{:else if items.length === 0}
			<p class="px-3 py-3 text-xs text-muted-foreground">None</p>
		{:else}
			<ul class="divide-y">
				{#each items as f (f.id)}
					{@const l = line(f)}
					<li>
						<button
							type="button"
							class="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-muted/50"
							onclick={() => onPick(f)}
						>
							<span
								class="mt-1.5 size-2 shrink-0 rounded-full {(
									SEVERITY_CHIP[f.severity] ?? SEVERITY_CHIP.unknown
								).edge}"
							></span>
							<span class="min-w-0 flex-1">
								<span class="block truncate text-sm">{l.main}</span>
								<span class="block truncate font-mono text-2xs text-muted-foreground">{l.sub}</span>
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
		{#if footer}
			<div class="flex flex-wrap items-center gap-3 border-t px-3 py-2 text-2xs">
				{@render footer()}
			</div>
		{/if}
	</HoverCard.Content>
</HoverCard.Root>
