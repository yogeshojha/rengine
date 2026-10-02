<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Field from '$lib/components/ui/field';

	interface Props {
		label: string;
		description?: string;
		error?: string;
		class?: string;
		children: Snippet<[{ id: string }]>;
	}

	let { label, description, error, class: className, children }: Props = $props();

	const fieldId = $props.id();
</script>

<Field.Field class={className} data-invalid={error ? true : undefined}>
	<Field.Label for={fieldId}>{label}</Field.Label>
	{@render children({ id: fieldId })}
	{#if error}
		<Field.Error>{error}</Field.Error>
	{:else if description}
		<Field.Description>{description}</Field.Description>
	{/if}
</Field.Field>
