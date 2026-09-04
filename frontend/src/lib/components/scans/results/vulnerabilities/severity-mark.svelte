<script lang="ts">
	import { SEVERITY_FILL, severityLabel } from '$lib/config/vulnerabilities';

	interface Props {
		severity: string;
		size?: 'sm' | 'md';
		showLabel?: boolean;
		class?: string;
	}

	let { severity, size = 'sm', showLabel = true, class: klass = '' }: Props = $props();

	let fill = $derived(SEVERITY_FILL[severity] ?? SEVERITY_FILL.unknown);
	let dot = $derived(size === 'md' ? 'size-2.5' : 'size-2');
</script>

<span class="flex items-center gap-1.5 {klass}">
	<span class="{dot} shrink-0 rounded-full" style="background:{fill}"></span>
	{#if showLabel}
		<span
			class="text-[10px] font-semibold tracking-wide uppercase"
			style="color:color-mix(in oklch, {fill} 88%, var(--foreground))"
		>
			{severityLabel(severity)}
		</span>
	{/if}
</span>
