<script lang="ts">
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import { Label } from '$lib/components/ui/label';
	import FormField from '$lib/components/form-field.svelte';
	import { sourceIcon } from '$lib/config/tripwires';
	import type { TripwireSourceSpec } from '$lib/types/tripwire';

	interface Props {
		sources: TripwireSourceSpec[];
		source: string;
		params: Record<string, string>;
		onSource: (key: string) => void;
		onParams: (params: Record<string, string>) => void;
	}

	let { sources, source, params, onSource, onParams }: Props = $props();

	const CARD =
		'flex cursor-pointer items-start gap-2.5 rounded-lg border border-border p-3 transition-colors hover:bg-muted/40 has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5';

	let spec = $derived(sources.find((s) => s.key === source) ?? null);
</script>

<FormField label="Reads">
	{#snippet children({ id })}
		<RadioGroup.Root
			{id}
			value={source}
			onValueChange={(v) => v && onSource(v)}
			class="grid gap-2 sm:grid-cols-2"
		>
			{#each sources as item (item.key)}
				{@const Icon = sourceIcon(item.key)}
				<Label for="source-{item.key}" class={CARD}>
					<RadioGroup.Item value={item.key} id="source-{item.key}" class="mt-0.5" />
					<span class="flex min-w-0 flex-1 flex-col gap-0.5">
						<span class="text-sm font-medium">{item.label}</span>
						<span class="text-xs font-normal text-muted-foreground">{item.help}</span>
					</span>
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground"
					>
						<Icon class="size-4" strokeWidth={1.75} aria-hidden="true" />
					</span>
				</Label>
			{/each}
		</RadioGroup.Root>
	{/snippet}
</FormField>

{#each spec?.fields ?? [] as field (field.key)}
	<FormField label={field.label}>
		{#snippet children({ id })}
			<RadioGroup.Root
				{id}
				value={params[field.key] ?? field.default}
				onValueChange={(v) => v && onParams({ ...params, [field.key]: v })}
				class="grid gap-2 sm:grid-cols-3"
			>
				{#each field.options as option (option.key)}
					<Label for="{field.key}-{option.key}" class={CARD}>
						<RadioGroup.Item value={option.key} id="{field.key}-{option.key}" class="mt-0.5" />
						<span class="flex flex-col gap-0.5">
							<span class="text-sm font-medium">{option.label}</span>
							{#if option.help}
								<span class="text-xs font-normal text-muted-foreground">{option.help}</span>
							{/if}
						</span>
					</Label>
				{/each}
			</RadioGroup.Root>
		{/snippet}
	</FormField>
{/each}
