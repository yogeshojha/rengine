<script lang="ts">
	import * as Select from '$lib/components/ui/select';

	interface Props {
		pageSize: number;
		onPageSizeChange: (size: number) => void;
		options?: number[];
	}

	let { pageSize, onPageSizeChange, options }: Props = $props();

	const DEFAULT_OPTIONS = [10, 20, 25, 50, 100];
	let pageSizeOptions = $derived(
		(options ?? DEFAULT_OPTIONS).map((n) => ({ value: String(n), label: `${n} per page` }))
	);

	let selectedValue = $derived(pageSize.toString());

	const triggerContent = $derived(
		pageSizeOptions.find((opt) => opt.value === selectedValue)?.label ?? `${pageSize} per page`
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
		{#each pageSizeOptions as option (option.value)}
			<Select.Item value={option.value} label={option.label}>
				{option.label}
			</Select.Item>
		{/each}
	</Select.Content>
</Select.Root>
