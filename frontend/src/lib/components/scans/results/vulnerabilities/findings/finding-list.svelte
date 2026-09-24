<script lang="ts">
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import { SEVERITY_CHIP, SEVERITY_LABELS, VULN_STATE_LABELS } from '$lib/config/vulnerabilities';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import { peek } from './peek';

	interface Props {
		projectId: string;
		scanId: string;
		q: string;
		exclude: string;
		limit?: number;
		sort?: string;
		main: (f: VulnerabilityRead) => string;
		onOpen: (f: VulnerabilityRead) => void;
		onTotal?: (n: number) => void;
	}

	let {
		projectId,
		scanId,
		q,
		exclude,
		limit = 25,
		sort = 'severity',
		main,
		onOpen,
		onTotal
	}: Props = $props();

	let rows = $state<VulnerabilityRead[] | null>(null);
	let failed = $state(false);

	$effect(() => {
		const key = `${q}|${exclude}`;
		rows = null;
		failed = false;
		peek(projectId, scanId, q, limit + 1, sort)
			.then((r) => {
				if (key !== `${q}|${exclude}`) return;
				rows = r.items.filter((f) => f.id !== exclude).slice(0, limit);
				onTotal?.(r.total);
			})
			.catch(() => (failed = true));
	});
</script>

{#if failed}
	<p class="px-3 py-4 text-xs text-muted-foreground">Findings not loaded.</p>
{:else if rows === null}
	<div class="space-y-2 p-3">
		{#each { length: 3 } as _, i (i)}
			<div class="h-8 animate-pulse rounded bg-muted/60"></div>
		{/each}
	</div>
{:else if rows.length === 0}
	<p class="px-3 py-4 text-xs text-muted-foreground">None</p>
{:else}
	<ul class="divide-y divide-border/60">
		{#each rows as f (f.id)}
			<li>
				<button
					type="button"
					class="flex w-full items-center gap-3 px-3 py-1.5 text-left hover:bg-muted/40"
					onclick={() => onOpen(f)}
				>
					<span
						class="inline-flex h-5 w-16 shrink-0 items-center justify-center rounded text-2xs font-semibold uppercase {(
							SEVERITY_CHIP[f.severity] ?? SEVERITY_CHIP.unknown
						).chip}"
					>
						{SEVERITY_LABELS[f.severity] ?? f.severity}
					</span>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm">{main(f)}</span>
						<span class="block truncate font-mono text-2xs text-muted-foreground"
							>{f.matched_at}</span
						>
					</span>
					<span class="hidden shrink-0 sm:inline-flex">
						<EvidenceMark evidence={f.evidence} showLabel hint={false} />
					</span>
					<span class="hidden w-24 shrink-0 text-right text-2xs text-muted-foreground sm:block">
						{VULN_STATE_LABELS[f.state] ?? f.state}
					</span>
				</button>
			</li>
		{/each}
	</ul>
{/if}
