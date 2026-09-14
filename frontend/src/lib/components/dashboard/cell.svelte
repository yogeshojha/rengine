<script lang="ts">
	import type { Snippet } from 'svelte';
	import Cell from '$lib/components/cell.svelte';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';

	interface Props {
		id: string;
		title: string;
		description?: string;
		href?: string;
		hrefLabel?: string;
		loading?: boolean;
		class?: string;
		bodyClass?: string;
		tools?: Snippet;
		children: Snippet;
		footer?: Snippet;
	}

	let { id, tools, children, footer, ...rest }: Props = $props();
</script>

<Cell {id} {...rest} onHide={() => dashboardLayout.hide(id)} {tools} {children} {footer} />
