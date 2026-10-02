<script lang="ts">
	import type { Snippet } from 'svelte';
	import Cell from '$lib/components/cell.svelte';
	import { widgetSpec } from '$lib/config/dashboard-widgets';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';
	import { isScoped } from '$lib/utilities/surface-scope';
	import { onDashboard, useScopedRoutes } from './scope-links';

	interface Props {
		id: string;
		title?: string;
		description?: string;
		href?: string;
		hrefLabel?: string;
		loading?: boolean;
		class?: string;
		bodyClass?: string;
		tools?: Snippet;
		children: Snippet;
		footer?: Snippet;
		projectWide?: boolean;
	}

	let {
		id,
		title,
		tools,
		children,
		footer,
		projectWide = false,
		description,
		...rest
	}: Props = $props();

	const routes = useScopedRoutes();
	const hideable = onDashboard();
	let scopedDescription = $derived(
		projectWide && isScoped(routes.scope)
			? [description, 'All targets'].filter(Boolean).join(' · ')
			: description
	);

	let spec = $derived(widgetSpec(id));
</script>

<Cell
	{id}
	{...rest}
	title={title ?? spec?.label ?? id}
	description={scopedDescription}
	skeleton={spec?.skeleton ?? 'text'}
	onHide={hideable ? () => dashboardLayout.hide(id) : undefined}
	{tools}
	{children}
	{footer}
/>
