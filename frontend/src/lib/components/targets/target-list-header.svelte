<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox';

	interface Props {
		selectAllChecked: boolean | 'indeterminate';
		onSelectAll: () => void;
	}

	let { selectAllChecked, onSelectAll }: Props = $props();
</script>

<div
	class="flex items-center gap-3 px-4 py-2 border-b border-border bg-muted/30 text-xs font-medium text-muted-foreground uppercase tracking-wider"
>
	<Checkbox
		checked={selectAllChecked === 'indeterminate' ? undefined : selectAllChecked}
		onCheckedChange={onSelectAll}
	/>

	<div class="w-[240px]">Target</div>
	<div class="w-[120px]">Scans</div>
	<div class="hidden md:block flex-1 min-w-[180px]">Organizations</div>
	<div class="hidden lg:block flex-1 min-w-[200px]">Tags</div>
	<div class="hidden sm:block w-[80px] text-right">Updated</div>

	<div class="flex gap-1">
		<div class="w-8"></div>
		<div class="w-8"></div>
	</div>
</div>
