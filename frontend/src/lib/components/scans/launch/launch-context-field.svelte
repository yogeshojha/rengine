<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import * as Select from '$lib/components/ui/select';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { SELECT_NONE } from '$lib/constants';
	import { NO_CONTEXT_LABEL } from '$lib/types/scan-context';
	import type { LaunchState } from './launch-state.svelte';

	interface Props {
		launch: LaunchState;
		disabled?: boolean;
		onNewContext: () => void;
	}

	let { launch, disabled = false, onNewContext }: Props = $props();

	let contexts = $derived(scanContextsStore.contexts);
	let label = $derived(
		launch.contextId === SELECT_NONE
			? NO_CONTEXT_LABEL
			: (contexts.find((c) => c.id === launch.contextId)?.name ?? NO_CONTEXT_LABEL)
	);
</script>

<div class="flex flex-col gap-2">
	<div class="flex items-center justify-between">
		<Label for="launch-context">Scan context</Label>
		<Button
			variant="ghost"
			size="sm"
			class="h-6 gap-1 px-2 text-xs text-muted-foreground"
			onclick={onNewContext}
			{disabled}
		>
			<Plus class="size-3" /> New context
		</Button>
	</div>
	<Select.Root type="single" bind:value={launch.contextId} {disabled}>
		<Select.Trigger id="launch-context" class="w-full">{label}</Select.Trigger>
		<Select.Content>
			<Select.Item value={SELECT_NONE} label={NO_CONTEXT_LABEL}>{NO_CONTEXT_LABEL}</Select.Item>
			{#each contexts as context (context.id)}
				<Select.Item value={context.id} label={context.name}>{context.name}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>
</div>
