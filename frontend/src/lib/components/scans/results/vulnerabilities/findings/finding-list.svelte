<script lang="ts">
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import EmptyState from '$lib/components/empty-state.svelte';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { SEVERITY_CHIP, SEVERITY_LABELS, VULN_STATE_LABELS } from '$lib/config/vulnerabilities';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import { peek } from './peek';

	const LIMIT = 25;

	interface Props {
		projectId: string;
		scanId: string;
		q: string;
		exclude: string;
		sort?: string;
		main: (f: VulnerabilityRead) => string;
		onOpen: (f: VulnerabilityRead) => void;
		onTotal?: (n: number) => void;
	}

	let { projectId, scanId, q, exclude, sort = 'severity', main, onOpen, onTotal }: Props = $props();

	let rows = $state<VulnerabilityRead[] | null>(null);
	let failed = $state(false);
	let attempt = $state(0);

	$effect(() => {
		void attempt;
		const key = `${q}|${exclude}`;
		rows = null;
		failed = false;
		peek(projectId, scanId, q, LIMIT + 1, sort)
			.then((r) => {
				if (key !== `${q}|${exclude}`) return;
				rows = r.items.filter((f) => f.id !== exclude).slice(0, LIMIT);
				onTotal?.(r.total);
			})
			.catch(() => (failed = true));
	});
</script>

{#if failed}
	<EmptyState
		compact
		icon={TriangleAlert}
		title="Findings not loaded"
		class="rounded-none border-0 bg-transparent"
	>
		<Button variant="outline" size="sm" onclick={() => attempt++}>Retry</Button>
	</EmptyState>
{:else if rows === null}
	<div class="space-y-2 p-3">
		{#each { length: 3 } as _, i (i)}
			<Skeleton class="h-8" />
		{/each}
	</div>
{:else if rows.length === 0}
	<p class="px-3 py-4 text-xs text-muted-foreground">No other findings</p>
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
