<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import {
		EVIDENCE_HELP,
		EVIDENCE_ORDER,
		evidenceLabel,
		evidenceRank,
		evidenceToken
	} from '$lib/config/evidence';

	interface Props {
		evidence: string;
		showLabel?: boolean;
		size?: 'sm' | 'md';
		hint?: boolean;
		onFilter?: (token: string) => void;
		class?: string;
	}

	let {
		evidence,
		showLabel = true,
		size = 'sm',
		hint = true,
		onFilter,
		class: klass = ''
	}: Props = $props();

	let rank = $derived(evidenceRank(evidence));
	let label = $derived(evidenceLabel(evidence));
	let steps = $derived(size === 'md' ? [6, 9, 12, 15] : [4, 6, 8, 10]);
	let bar = $derived(size === 'md' ? 'w-[3px]' : 'w-0.5');
	let text = $derived(hint ? (EVIDENCE_HELP[evidence] ?? null) : null);
</script>

{#snippet glyph(props: Record<string, unknown>)}
	{#if onFilter}
		<button
			{...props}
			type="button"
			class="flex h-5 shrink-0 items-center gap-1.5 {klass}"
			aria-label="Filter to {label.toLowerCase()} evidence"
			onclick={(e) => {
				e.stopPropagation();
				onFilter?.(evidenceToken(evidence));
			}}
		>
			{@render bars()}
			{#if showLabel}<span class="text-xs">{label}</span>{/if}
		</button>
	{:else}
		<span {...props} class="flex h-5 shrink-0 items-center gap-1.5 {klass}">
			{@render bars()}
			{#if showLabel}<span class="text-xs">{label}</span>{/if}
		</span>
	{/if}
{/snippet}

{#snippet bars()}
	<span class="flex items-end gap-px" aria-hidden="true">
		{#each EVIDENCE_ORDER as step, i (step)}
			<span
				class="{bar} rounded-[1px] {i <= rank ? 'bg-foreground' : 'bg-border'}"
				style="height:{steps[i]}px"
			></span>
		{/each}
	</span>
{/snippet}

<Hint {text}>
	{#snippet child(props)}
		{@render glyph(props)}
	{/snippet}
</Hint>
