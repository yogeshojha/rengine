<script lang="ts">
	import * as Select from '$lib/components/ui/select';

	interface Props {
		pageSize: number;
		onPageSizeChange: (size: number) => void;
	}

	let { pageSize, onPageSizeChange }: Props = $props();

	const pageSizeOptions = [
		{ value: '10', label: '10 per page' },
		{ value: '20', label: '20 per page' },
		{ value: '50', label: '50 per page' },
		{ value: '100', label: '100 per page' },
		{ value: '-1', label: 'All' }
	];

	let selectedValue = $state<string>('10');

	$effect(() => {
		selectedValue = pageSize === -1 ? '-1' : pageSize.toString();
	});

	const triggerContent = $derived(
		pageSizeOptions.find((opt) => opt.value === selectedValue)?.label ?? '10 per page'
	);

	function handleValueChange(value: string | undefined) {
		if (value) {
			onPageSizeChange(parseInt(value));
		}
	}
</script>

<Select.Root type="single" bind:value={selectedValue} onValueChange={handleValueChange}>
	<Select.Trigger class="h-9 w-[140px]">
		{triggerContent}
	</Select.Trigger>
	<Select.Content>
		{#each pageSizeOptions as option}
			<Select.Item value={option.value} label={option.label}>
				{option.label}
			</Select.Item>
		{/each}
	</Select.Content>
</Select.Root>
