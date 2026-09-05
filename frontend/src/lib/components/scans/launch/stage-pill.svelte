<script lang="ts">
	import type { Snippet } from 'svelte';
	import Check from '@lucide/svelte/icons/check';
	import Link from '@lucide/svelte/icons/link';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Hint from '$lib/components/hint.svelte';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { StageState } from '$lib/utilities/launch-plan';

	interface Props {
		stage: StageCatalogEntry;
		state: StageState;
		disabled?: boolean;
		onToggle: () => void;
		children?: Snippet;
	}

	let { stage, state, disabled = false, onToggle, children }: Props = $props();

	const BLOCKED_HINT = 'Skipped at passive intensity. This stage sends traffic to the target.';
	const IMPLIED_HINT = 'Included automatically. A selected stage depends on its results.';

	let hint = $derived(
		state === 'blocked' ? BLOCKED_HINT : state === 'implied' ? IMPLIED_HINT : stage.description
	);
	let pressed = $derived(state === 'on' || state === 'implied');
</script>

<span
	class="inline-flex h-7 items-stretch rounded-md border text-[13px] transition-colors {state ===
	'on'
		? 'border-border bg-muted text-foreground'
		: state === 'implied'
			? 'border-dashed border-border bg-muted/60 text-muted-foreground'
			: state === 'blocked'
				? 'border-border/60 text-muted-foreground/60'
				: 'border-border bg-background text-muted-foreground hover:bg-accent hover:text-foreground'}"
>
	<Hint text={hint}>
		{#snippet child(props)}
			<button
				{...props}
				type="button"
				aria-pressed={pressed}
				class="inline-flex items-center gap-1.5 rounded-md px-2.5 font-medium outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed {state ===
				'off'
					? 'font-normal'
					: ''}"
				{disabled}
				onclick={onToggle}
			>
				{#if state === 'on'}
					<Check class="size-3 shrink-0" />
				{:else if state === 'implied'}
					<Link class="size-3 shrink-0" />
				{:else if state === 'blocked'}
					<EyeOff class="size-3 shrink-0" />
				{/if}
				<span>{stage.title}</span>
			</button>
		{/snippet}
	</Hint>
	{#if children && (state === 'on' || state === 'implied')}
		<span class="my-1 w-px bg-border"></span>
		{@render children()}
	{/if}
</span>
