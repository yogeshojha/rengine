<script lang="ts">
	import type { Snippet } from 'svelte';
	import Check from '@lucide/svelte/icons/check';
	import Hint from '$lib/components/hint.svelte';
	import type { SectionCatalogEntry } from '$lib/types/report';

	interface Props {
		section: SectionCatalogEntry;
		on: boolean;
		unavailable?: boolean;
		onToggle: () => void;
		children?: Snippet;
	}

	let { section, on, unavailable = false, onToggle, children }: Props = $props();

	const UNAVAILABLE = 'This scan produced nothing for this section, so it would be skipped.';
	let hint = $derived(unavailable ? UNAVAILABLE : section.description);
</script>

<span
	class="inline-flex h-7 items-stretch rounded-md border text-[13px] transition-colors {on
		? 'border-border bg-muted text-foreground'
		: unavailable
			? 'border-border/60 text-muted-foreground/60'
			: 'border-border bg-background text-muted-foreground hover:bg-accent hover:text-foreground'}"
>
	<Hint text={hint}>
		{#snippet child(props)}
			<button
				{...props}
				type="button"
				aria-pressed={on}
				class="inline-flex items-center gap-1.5 rounded-md px-2.5 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 {on
					? 'font-medium'
					: ''}"
				onclick={onToggle}
			>
				{#if on}<Check class="size-3 shrink-0" />{/if}
				<span>{section.title}</span>
			</button>
		{/snippet}
	</Hint>
	{#if children && on}
		<span class="my-1 w-px bg-border"></span>
		{@render children()}
	{/if}
</span>
