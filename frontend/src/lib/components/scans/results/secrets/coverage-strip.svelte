<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Info from '@lucide/svelte/icons/info';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { DROP_REASON_LABELS } from '$lib/config/secrets';
	import type { SecretCoverage } from '$lib/types/secret';

	interface Props {
		coverage: SecretCoverage | null;
	}

	let { coverage }: Props = $props();

	const n = (v: number) => v.toLocaleString();

	let ran = $derived(coverage?.ran ?? false);
	let partial = $derived(coverage?.partial ?? false);
	let Icon = $derived(!ran ? CircleSlash : partial ? TriangleAlert : CircleCheck);
	let tone = $derived(partial ? 'text-warning' : 'text-muted-foreground');
	let error = $derived(coverage?.rows.find((r) => r.error)?.error ?? null);
	let matches = $derived(coverage?.rows.reduce((a, r) => a + r.matches, 0) ?? 0);
	let drops = $derived.by<[string, number][]>(() => {
		const totals: Record<string, number> = {};
		for (const row of coverage?.rows ?? []) {
			for (const [reason, count] of Object.entries(row.dropped ?? {})) {
				totals[reason] = (totals[reason] ?? 0) + count;
			}
		}
		return Object.entries(totals).sort((a, b) => b[1] - a[1]);
	});
	let facts = $derived.by<[string, string][]>(() => {
		if (!coverage) return [];
		const out: [string, string][] = [
			['Responses', n(coverage.documents_total)],
			['Read', n(coverage.documents_read)],
			['Truncated', n(coverage.truncated)],
			['Detectors', n(coverage.detectors)],
			['Matches', n(matches)],
			['Secrets', n(coverage.secrets)]
		];
		if (coverage.scans > 1) out.unshift(['Scans', n(coverage.scans)]);
		return out;
	});
	let summary = $derived.by(() => {
		if (!coverage || !ran) return 'Not scanned';
		const parts = [`${n(coverage.documents_read)} responses read`];
		if (coverage.truncated) parts.push(`${n(coverage.truncated)} truncated`);
		return parts.join(' · ');
	});
</script>

<div
	class="flex flex-wrap items-center gap-x-2 gap-y-1 border-b bg-muted/10 px-4 py-2 text-xs {tone}"
>
	<Icon class="size-3.5 shrink-0" />
	<span>{summary}</span>
	{#if coverage && ran}
		<Popover.Root>
			<Popover.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="sm"
						class="h-6 gap-1 px-1.5 text-xs font-normal text-muted-foreground hover:text-foreground"
					>
						<Info class="size-3" /> Coverage
					</Button>
				{/snippet}
			</Popover.Trigger>
			<Popover.Content class="w-72 p-0" align="start">
				<ScrollArea class="max-h-96">
					<dl class="divide-y">
						{#each facts as [label, value] (label)}
							<div class="flex items-center justify-between gap-3 px-3 py-1.5 text-xs">
								<dt class="text-muted-foreground">{label}</dt>
								<dd class="font-mono tabular-nums">{value}</dd>
							</div>
						{/each}
					</dl>
					{#if drops.length}
						<div
							class="border-t px-3 py-1.5 text-2xs tracking-wide text-muted-foreground uppercase"
						>
							Dropped
						</div>
						<dl class="divide-y">
							{#each drops as [reason, count] (reason)}
								<div class="flex items-center justify-between gap-3 px-3 py-1.5 text-xs">
									<dt class="text-muted-foreground">{DROP_REASON_LABELS[reason] ?? reason}</dt>
									<dd class="font-mono tabular-nums">{n(count)}</dd>
								</div>
							{/each}
						</dl>
					{/if}
					{#if error}
						<p class="border-t px-3 py-2 text-xs text-warning">{error}</p>
					{/if}
				</ScrollArea>
			</Popover.Content>
		</Popover.Root>
	{/if}
</div>
