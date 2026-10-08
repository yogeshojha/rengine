<script lang="ts">
	import { cn } from '$lib/utils';
	import { SEVERITY_CHIP, SEVERITY_LABELS } from '$lib/config/vulnerabilities';

	interface Props {
		/** key into SEVERITY_CHIP; an unknown key renders neutral */
		severity: string;
		count: number;
		/** defaults to the severity's own label */
		label?: string;
		size?: 'sm' | 'default';
		/** renders a toggle button when set */
		onclick?: () => void;
		pressed?: boolean;
		/** names the button; a plain chip reads as its text */
		'aria-label'?: string;
		class?: string;
	}

	let {
		severity,
		count,
		label,
		size = 'default',
		onclick,
		pressed = false,
		'aria-label': ariaLabel,
		class: className
	}: Props = $props();

	let text = $derived(label ?? SEVERITY_LABELS[severity] ?? severity);
	// zero counts go neutral rather than faded so the label stays readable
	let tone = $derived(
		count > 0
			? (SEVERITY_CHIP[severity]?.chip ?? 'bg-muted text-foreground')
			: 'bg-muted text-muted-foreground'
	);
	let classes = $derived(
		cn(
			'inline-flex shrink-0 items-center rounded-md whitespace-nowrap',
			size === 'sm'
				? 'h-6 min-w-8 justify-center gap-1 px-1.5 text-xs'
				: 'h-8 gap-1.5 px-2.5 text-sm',
			tone,
			className
		)
	);
</script>

{#snippet body()}
	<span class="text-2xs font-normal">{text}</span>
	<span class="font-mono font-semibold tabular-nums">{count.toLocaleString()}</span>
{/snippet}

{#if onclick}
	<button
		type="button"
		class={cn(
			classes,
			'transition-shadow outline-none focus-visible:ring-[3px] focus-visible:ring-ring/70',
			pressed && 'ring-2 ring-current/50'
		)}
		aria-pressed={pressed}
		aria-label={ariaLabel}
		{onclick}
	>
		{@render body()}
	</button>
{:else}
	<span class={classes}>{@render body()}</span>
{/if}
