<script lang="ts">
	import type { Snippet } from 'svelte';
	import Cell from '$lib/components/cell.svelte';
	import type { SkeletonShape } from '$lib/components/skeleton/shapes';
	import { widgetSpec } from '$lib/config/dashboard-widgets';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';

	interface Props {
		id: string;
		title: string;
		description?: string;
		href?: string;
		hrefLabel?: string;
		loading?: boolean;
		skeleton?: SkeletonShape;
		skeletonRows?: number;
		class?: string;
		bodyClass?: string;
		tools?: Snippet;
		children: Snippet;
		footer?: Snippet;
	}

	let { id, skeleton, tools, children, footer, ...rest }: Props = $props();

	let shape = $derived(skeleton ?? widgetSpec(id)?.skeleton ?? 'text');
</script>

<Cell
	{id}
	{...rest}
	skeleton={shape}
	onHide={() => dashboardLayout.hide(id)}
	{tools}
	{children}
	{footer}
/>
