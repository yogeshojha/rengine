<script lang="ts">
	import { cn } from '$lib/utils';
	import VerbRail from './verb-rail.svelte';
	import { VERB } from '$lib/config/compare';
	import { CHANGE_VERB, VERB_ORDER, type ChangeVerb } from '$lib/types/compare';

	interface Props {
		counts: Record<ChangeVerb, number>;
		active: ChangeVerb[];
		confirmed: boolean;
		onToggle: (verb: ChangeVerb) => void;
	}

	let { counts, active, confirmed, onToggle }: Props = $props();

	let shown = $derived(
		VERB_ORDER.filter((v) => {
			if (v === CHANGE_VERB.DISAPPEARED) return confirmed || counts.disappeared > 0;
			if (v === CHANGE_VERB.UNCONFIRMED) return !confirmed || counts.unconfirmed > 0;
			return true;
		})
	);
</script>

<div
	class="sticky top-0 z-10 flex flex-wrap items-center gap-1.5 border-b bg-background/95 px-4 py-2.5 backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:px-5"
>
	{#each shown as verb (verb)}
		{@const spec = VERB[verb]}
		{@const n = counts[verb] ?? 0}
		{@const on = active.includes(verb)}
		<button
			type="button"
			aria-pressed={on}
			disabled={n === 0 && !on}
			onclick={() => onToggle(verb)}
			class={cn(
				'inline-flex items-center gap-2 rounded-full border py-1 pr-2.5 pl-2 text-xs font-medium transition-colors',
				on
					? 'border-primary/40 bg-primary/8 text-foreground'
					: 'border-border text-muted-foreground hover:text-foreground',
				n === 0 && !on && 'opacity-45'
			)}
		>
			<VerbRail {verb} size="dot" />
			{spec.label}
			<span class="tabular-nums opacity-70">{n.toLocaleString()}</span>
		</button>
	{/each}
</div>
