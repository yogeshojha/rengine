<script lang="ts">
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import BotIcon from '@lucide/svelte/icons/bot';
	import { ROUTES } from '$lib/config/routes';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { catalogLabel } from '$lib/config/reports';
	import type { NarrativeOptions } from '$lib/types/report';

	let { narrative = $bindable() }: { narrative: NarrativeOptions } = $props();

	const uid = $props.id();
	const catalog = $derived(reportCatalog.catalog);
	const aiAvailable = $derived(reportCatalog.aiAvailable);

	const audienceHelp = $derived(
		catalog?.audiences.find((a) => a.key === narrative.audience)?.help ?? ''
	);
</script>

<div class="space-y-6">
	<div class="grid gap-4 sm:grid-cols-2">
		<FormField label="Audience" description={audienceHelp || undefined}>
			{#snippet children({ id })}
				<Select.Root type="single" bind:value={narrative.audience}>
					<Select.Trigger {id} class="h-9 w-full"
						>{catalogLabel(catalog?.audiences, narrative.audience)}</Select.Trigger
					>
					<Select.Content>
						{#each catalog?.audiences ?? [] as item (item.key)}
							<Select.Item value={item.key}>{item.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			{/snippet}
		</FormField>
		<FormField label="Length">
			{#snippet children({ id })}
				<Select.Root type="single" bind:value={narrative.depth}>
					<Select.Trigger {id} class="h-9 w-full"
						>{catalogLabel(catalog?.depths, narrative.depth)}</Select.Trigger
					>
					<Select.Content>
						{#each catalog?.depths ?? [] as item (item.key)}
							<Select.Item value={item.key}>{item.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			{/snippet}
		</FormField>
	</div>

	<Separator />

	{#if !aiAvailable}
		<Alert.Root>
			<BotIcon />
			<Alert.Title>AI is not connected</Alert.Title>
			<Alert.Description>
				Connect a provider on the <a href={ROUTES.ai()} class="underline">AI page</a>.
			</Alert.Description>
		</Alert.Root>
	{/if}

	<div class="flex items-start justify-between gap-4">
		<div class="space-y-0.5">
			<Label for="{uid}-ai">Draft the narrative with AI</Label>
			<p class="text-xs text-muted-foreground">
				The model receives a summary of the computed findings.
			</p>
		</div>
		<Switch
			id="{uid}-ai"
			checked={narrative.ai_enabled}
			disabled={!aiAvailable}
			onCheckedChange={(v) => (narrative.ai_enabled = v)}
		/>
	</div>

	{#if narrative.ai_enabled}
		<div class="space-y-4 rounded-lg border bg-muted/30 p-4">
			<div class="flex items-start justify-between gap-4">
				<div class="space-y-0.5">
					<span class="text-sm">Explain each finding</span>
					<p class="text-xs text-muted-foreground">Written once per check and cached.</p>
				</div>
				<Switch
					checked={narrative.explain_findings}
					onCheckedChange={(v) => (narrative.explain_findings = v)}
					aria-label="Explain each finding"
				/>
			</div>
			{#if narrative.explain_findings}
				<FormField label="Findings explained, at most">
					{#snippet children({ id })}
						<div>
							<Input
								{id}
								type="number"
								min="1"
								max="40"
								bind:value={narrative.max_explained_issues}
								class="h-9 w-28"
							/>
						</div>
					{/snippet}
				</FormField>
			{/if}
			<div class="flex items-start justify-between gap-4">
				<div class="space-y-0.5">
					<span class="text-sm">Disclose sections written by a model</span>
					<p class="text-xs text-muted-foreground">Prints one line under the drafted text.</p>
				</div>
				<Switch
					checked={narrative.disclose_ai}
					onCheckedChange={(v) => (narrative.disclose_ai = v)}
					aria-label="Disclose sections written by a model"
				/>
			</div>
			<FormField label="House style" description="Passed to the model with every section.">
				{#snippet children({ id })}
					<Textarea
						{id}
						bind:value={narrative.house_style}
						rows={3}
						class="text-sm"
						placeholder="Refer to the client as the Bank. Use British spelling."
					/>
				{/snippet}
			</FormField>
		</div>
	{/if}
</div>
