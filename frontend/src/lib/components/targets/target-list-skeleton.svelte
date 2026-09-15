<script lang="ts">
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { TARGET_SKELETON_COLUMNS } from './target-columns';

	interface Props {
		count?: number;
	}

	let { count = 5 }: Props = $props();
</script>

<TableSkeleton lead={TARGET_SKELETON_COLUMNS} rows={count} actions={false} selectable />
