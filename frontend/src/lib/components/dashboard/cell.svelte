<script lang="ts">
	import type { Snippet } from 'svelte';
	import Cell from '$lib/components/cell.svelte';
	import type { SkeletonShape } from '$lib/components/skeleton/shapes';
	import { widgetSpec } from '$lib/config/dashboard-widgets';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';
	import { isScoped } from '$lib/utilities/surface-scope';
	import { useScopedRoutes } from './scope-links';

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
		projectWide?: boolean;
	}

	let {
		id,
		skeleton,
		tools,
		children,
		footer,
		projectWide = false,
		description,
		...rest
	}: Props = $props();

	const routes = useScopedRoutes();
	let scopedDescription = $derived(
		projectWide && isScoped(routes.scope)
			? [description, 'All targets'].filter(Boolean).join(' · ')
			: description
	);

	let shape = $derived(skeleton ?? widgetSpec(id)?.skeleton ?? 'text');
</script>

<Cell
	{id}
	{...rest}
	description={scopedDescription}
	skeleton={shape}
	onHide={() => dashboardLayout.hide(id)}
	{tools}
	{children}
	{footer}
/>
