<script lang="ts">
	import { cn } from '$lib/utils';
	import { CHANGE_VERB, type ChangeVerb } from '$lib/types/compare';

	interface Props {
		verb: ChangeVerb;
		size?: 'rail' | 'dot';
		class?: string;
	}

	let { verb, size = 'rail', class: className }: Props = $props();

	let box = $derived(size === 'rail' ? 'w-[3px] self-stretch' : 'h-3.5 w-[3px]');
</script>

<span class={cn('flex shrink-0 flex-col gap-[3px] overflow-hidden rounded-full', box, className)}>
	{#if verb === CHANGE_VERB.APPEARED}
		<span class="flex-1 rounded-full bg-primary"></span>
	{:else if verb === CHANGE_VERB.CHANGED}
		<span class="flex-1 rounded-full bg-info"></span>
		<span class="flex-1 rounded-full bg-info"></span>
	{:else if verb === CHANGE_VERB.UNCONFIRMED}
		<span class="flex-1 rounded-full ring-1 ring-warning/70 ring-inset"></span>
	{:else if verb === CHANGE_VERB.DISAPPEARED}
		<span class="flex-1 rounded-full ring-1 ring-muted-foreground/60 ring-inset"></span>
	{:else}
		<span class="flex-1 rounded-full bg-border"></span>
	{/if}
</span>
