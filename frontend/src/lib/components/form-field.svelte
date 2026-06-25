<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Field from '$lib/components/ui/field';

	interface Props {
		label: string;
		for?: string;
		description?: string;
		error?: string;
		class?: string;
		children: Snippet<[{ id: string }]>;
	}

	let { label, for: forId, description, error, class: className, children }: Props = $props();

	const uid = $props.id();
	const fieldId = $derived(forId ?? uid);
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
