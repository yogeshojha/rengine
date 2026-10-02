<script lang="ts">
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import { SEVERITY_CHIP, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import { evidenceLabel } from '$lib/config/evidence';
	import type { ScanFindings } from '$lib/types/scan';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import { findingsOf, findingsHref, findingHref } from './findings';
	import { historyPrefs } from './prefs.svelte';

	const PREVIEW = 6;

	interface Props {
		projectId: string;
		scanId: string;
		findings: ScanFindings | null | undefined;
		live: boolean;
		highlight?: string | null;
	}

	let { projectId, scanId, findings, live, highlight = null }: Props = $props();

	let shown = $derived(historyPrefs.severities);
	let counts = $derived(
		shown.map((s) => ({ sev: s, n: findings ? (findings[s as keyof ScanFindings] as number) : 0 }))
	);
	let total = $derived(counts.reduce((a, c) => a + c.n, 0));
	let version = $derived(counts.map((c) => c.n).join('.'));

	let items = $state<Record<string, VulnerabilityRead[] | null>>({});
	let failed = $state<Record<string, boolean>>({});

	function load(sev: string) {
		failed = { ...failed, [sev]: false };
		findingsOf(projectId, scanId, [sev], PREVIEW, version)
			.then((r) => (items = { ...items, [sev]: r.items }))
			.catch(() => (failed = { ...failed, [sev]: true }));
	}
</script>

{#if !findings?.covered}
	<span class="text-xs text-muted-foreground">{live ? 'Not run yet' : 'Not scanned'}</span>
{:else if total === 0}
	<span class="text-xs text-muted-foreground">None</span>
{:else}
	<div class="flex items-center gap-1">
		{#each counts as c (c.sev)}
			{#if c.n === 0}
				<Hint text="No {SEVERITY_LABELS[c.sev].toLowerCase()} findings">
					{#snippet child(props)}
						<span
							{...props}
							class="inline-flex h-6 min-w-8 items-center justify-center rounded-md border border-dashed border-border px-1.5 font-mono text-xs text-muted-foreground/50"
							aria-label="No {SEVERITY_LABELS[c.sev].toLowerCase()} findings"
						>
							0
						</span>
					{/snippet}
				</Hint>
			{:else}
				<HoverCard.Root openDelay={250} closeDelay={80} onOpenChange={(o) => o && load(c.sev)}>
					<HoverCard.Trigger
						href={findingsHref(scanId, [c.sev])}
						onclick={(e: MouseEvent) => e.stopPropagation()}
						class="inline-flex h-6 min-w-8 items-center justify-center rounded-md px-1.5 font-mono text-xs font-semibold tabular-nums transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {SEVERITY_CHIP[
							c.sev
						].chip} {highlight === c.sev ? 'ring-2 ring-current/40' : ''}"
						aria-label="{c.n} {SEVERITY_LABELS[c.sev].toLowerCase()} {c.n === 1
							? 'finding'
							: 'findings'}"
					>
						{c.n}
					</HoverCard.Trigger>
					<HoverCard.Content class="w-96 p-0" align="start">
						<div class="flex items-center justify-between border-b px-3 py-2">
							<span class="text-xs font-medium {SEVERITY_CHIP[c.sev].ink}">
								{c.n}
								{SEVERITY_LABELS[c.sev].toLowerCase()}
							</span>
							<a
								href={findingsHref(scanId, [c.sev])}
								class="text-2xs text-primary hover:text-primary/80"
							>
								Open in results
							</a>
						</div>
						{#if failed[c.sev]}
							<p class="px-3 py-3 text-xs text-muted-foreground">Findings not loaded.</p>
						{:else if !items[c.sev]}
							<div class="space-y-2 px-3 py-3">
								{#each { length: Math.min(c.n, 3) } as _, i (i)}
									<Skeleton class="h-3.5 rounded" />
								{/each}
							</div>
						{:else}
							<ul class="divide-y">
								{#each items[c.sev] ?? [] as f (f.id)}
									<li>
										<a href={findingHref(scanId, f.id)} class="block px-3 py-2 hover:bg-muted/50">
											<div class="truncate text-sm">{f.template_name}</div>
											<div class="mt-0.5 flex items-center gap-2 text-2xs text-muted-foreground">
												<span class="truncate font-mono">{f.matched_at}</span>
												<span class="shrink-0">{evidenceLabel(f.evidence)}</span>
											</div>
										</a>
									</li>
								{/each}
							</ul>
							{#if c.n > (items[c.sev]?.length ?? 0)}
								<div class="border-t px-3 py-1.5 text-2xs text-muted-foreground">
									{c.n - (items[c.sev]?.length ?? 0)} more
								</div>
							{/if}
						{/if}
					</HoverCard.Content>
				</HoverCard.Root>
			{/if}
		{/each}
	</div>
{/if}
