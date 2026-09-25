<script lang="ts">
	import ALargeSmall from '@lucide/svelte/icons/a-large-small';
	import { Button } from '$lib/components/ui/button';
	import LookalikeName from './lookalike-name.svelte';
	import LookalikeSheet from './lookalike-sheet.svelte';
	import { LookalikeState, THREAT_VERDICTS, VERDICTS, Verdict } from '$lib/config/lookalikes';
	import type { LookalikeSummary } from '$lib/types/lookalike';

	interface Props {
		summary: LookalikeSummary;
		projectId: string;
		onChanged?: () => void;
	}

	let { summary, projectId, onChanged }: Props = $props();

	const SHOWN = 3;
	let open = $state(false);

	let active = $derived(
		summary.rows.filter((r) => r.verdict !== Verdict.LINKED && r.state === LookalikeState.OPEN)
	);
	let threats = $derived(active.filter((r) => THREAT_VERDICTS.has(r.verdict)));
	let detail = $derived(
		VERDICTS.map((v) => ({ label: v.label, n: active.filter((r) => r.verdict === v.key).length }))
			.filter((v) => v.n > 0)
			.map((v) => `${v.label} ${v.n.toLocaleString()}`)
			.join(' · ')
	);
</script>

{#if active.length > 0}
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-2.5">
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-lg {threats.length
				? 'bg-sev-high-wash text-sev-high-ink'
				: 'bg-muted text-muted-foreground'}"
		>
			<ALargeSmall class="size-4" />
		</span>
		<span class="flex min-w-0 flex-col">
			<span class="text-sm">
				<span class="font-semibold tabular-nums">{active.length.toLocaleString()}</span>
				{active.length === 1 ? 'lookalike domain' : 'lookalike domains'} of
				<span class="font-mono">{summary.apex}</span> registered
			</span>
			{#if detail}
				<span class="text-xs text-muted-foreground">{detail}</span>
			{/if}
		</span>
		<span class="ml-auto flex flex-wrap items-center gap-1.5">
			{#each active.slice(0, SHOWN) as r (r.domain)}
				<span class="rounded-md border px-2 py-0.5 text-xs">
					<LookalikeName display={r.display} domain={r.display} apex={r.apex} />
				</span>
			{/each}
			{#if active.length > SHOWN}
				<span class="text-xs text-muted-foreground">+{active.length - SHOWN}</span>
			{/if}
			<Button size="sm" onclick={() => (open = true)}>Review</Button>
		</span>
	</div>
	<LookalikeSheet {open} onOpenChange={(o) => (open = o)} {summary} {projectId} {onChanged} />
{/if}
