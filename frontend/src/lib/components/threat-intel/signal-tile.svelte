<script lang="ts">
	import type { IconComponent } from '$lib/config/icons';
	import { TONE_FILL } from '$lib/config/threat-intel';

	interface Props {
		icon: IconComponent;
		count: number;
		label: string;
		detail: string;
		tone?: string;
		onSelect?: () => void;
	}

	let { icon: Icon, count, label, detail, tone = 'neutral', onSelect }: Props = $props();

	let fill = $derived(TONE_FILL[tone] ?? TONE_FILL.neutral);
</script>

<svelte:element
	this={onSelect ? 'button' : 'div'}
	type={onSelect ? 'button' : undefined}
	role={onSelect ? 'button' : undefined}
	class="flex min-w-0 items-start gap-3 p-4 text-left {onSelect
		? 'cursor-pointer transition-colors hover:bg-accent/40'
		: ''}"
	onclick={onSelect}
>
	<span
		class="flex size-8 shrink-0 items-center justify-center rounded-md"
		style="background:color-mix(in oklch, {fill} 14%, transparent);color:{fill}"
	>
		<Icon class="size-4" />
	</span>
	<span class="flex min-w-0 flex-col gap-0.5">
		<span class="flex items-baseline gap-1.5">
			<span class="font-mono text-xl leading-none font-semibold tabular-nums">{count}</span>
			<span class="truncate text-xs font-medium">{label}</span>
		</span>
		<span class="text-2xs leading-4 text-muted-foreground">{detail}</span>
	</span>
</svelte:element>
