<script lang="ts">
	import type { IconProps } from '@lucide/svelte';

	let {
		color = 'currentColor',
		size = 24,
		strokeWidth = 2,
		absoluteStrokeWidth = false,
		name: _name,
		iconNode: _iconNode,
		children,
		class: className,
		...rest
	}: IconProps = $props();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	fill="none"
	stroke-linecap="round"
	stroke-linejoin="round"
	{...rest}
	width={size}
	height={size}
	stroke={color}
	stroke-width={absoluteStrokeWidth ? (Number(strokeWidth) * 24) / Number(size) : strokeWidth}
	class={['lucide-icon lucide lucide-ninja', className]}
>
	<circle cx="11" cy="13" r="8" />
	<rect x="5" y="10" width="12" height="5" rx="2.5" />
	<path d="M9 12.5h.01" />
	<path d="M13 12.5h.01" />
	<path d="M18 9c1.5-.5 2.5-2 3-4" />
	<path d="M18 9c1.5 0 3 .5 4 2" />
	{@render children?.()}
</svg>
