<script lang="ts">
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import { ROUTES } from '$lib/config/routes';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import type { NarrativeOptions } from '$lib/types/report';

	let { narrative = $bindable() }: { narrative: NarrativeOptions } = $props();

	const catalog = $derived(reportCatalog.catalog);
	const aiAvailable = $derived(reportCatalog.aiAvailable);

	function label(list: { key: string; label: string }[] | undefined, key: string): string {
		return list?.find((i) => i.key === key)?.label ?? key;
	}

	const audienceHelp = $derived(
		catalog?.audiences.find((a) => a.key === narrative.audience)?.help ?? ''
	);
</script>

<div class="space-y-6">
	<div class="grid gap-4 sm:grid-cols-2">
		<div class="space-y-1.5">
			<Label class="text-xs">Audience</Label>
			<Select.Root type="single" bind:value={narrative.audience}>
				<Select.Trigger class="h-9 w-full"
					>{label(catalog?.audiences, narrative.audience)}</Select.Trigger
				>
				<Select.Content>
					{#each catalog?.audiences ?? [] as item (item.key)}
						<Select.Item value={item.key}>{item.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			{#if audienceHelp}<p class="text-xs text-muted-foreground">{audienceHelp}</p>{/if}
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Length</Label>
			<Select.Root type="single" bind:value={narrative.depth}>
				<Select.Trigger class="h-9 w-full">{label(catalog?.depths, narrative.depth)}</Select.Trigger
				>
				<Select.Content>
					{#each catalog?.depths ?? [] as item (item.key)}
						<Select.Item value={item.key}>{item.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
	</div>

	<Separator />

	{#if !aiAvailable}
		<Alert.Root>
			<SparklesIcon />
			<Alert.Title>AI is not connected</Alert.Title>
			<Alert.Description>
				Reports are written without a model. Every section still carries the same computed findings.
				Connect a provider on the <a href={ROUTES.ai()} class="underline">AI page</a> to have the narrative
				drafted for you.
			</Alert.Description>
		</Alert.Root>
	{/if}

	<div class="flex items-start justify-between gap-4">
		<div class="space-y-0.5">
			<Label class="text-sm font-medium">Draft the narrative with AI</Label>
			<p class="text-xs text-muted-foreground">
				The model receives a summary of the computed findings. It never sees raw rows, evidence or
				credentials.
			</p>
		</div>
		<Switch
			checked={narrative.ai_enabled}
			disabled={!aiAvailable}
			onCheckedChange={(v) => (narrative.ai_enabled = v)}
		/>
	</div>

	{#if narrative.ai_enabled}
		<div class="space-y-4 rounded-md border bg-muted/30 p-4">
			<div class="flex items-start justify-between gap-4">
				<div class="space-y-0.5">
					<span class="text-sm">Explain each finding</span>
					<p class="text-xs text-muted-foreground">
						Written once per check and cached, so the same check costs nothing on later reports.
					</p>
				</div>
				<Switch
					checked={narrative.explain_findings}
					onCheckedChange={(v) => (narrative.explain_findings = v)}
				/>
			</div>
			{#if narrative.explain_findings}
				<div class="space-y-1.5">
					<Label class="text-xs">Explain at most</Label>
					<Input
						type="number"
						min="1"
						max="40"
						bind:value={narrative.max_explained_issues}
						class="h-9 w-28"
					/>
				</div>
			{/if}
			<div class="flex items-start justify-between gap-4">
				<div class="space-y-0.5">
					<span class="text-sm">Say when a model wrote a section</span>
					<p class="text-xs text-muted-foreground">Prints one line under the drafted text.</p>
				</div>
				<Switch
					checked={narrative.disclose_ai}
					onCheckedChange={(v) => (narrative.disclose_ai = v)}
				/>
			</div>
			<div class="space-y-1.5">
				<Label class="text-xs">House style</Label>
				<Textarea
					bind:value={narrative.house_style}
					rows={3}
					class="text-sm"
					placeholder="Refer to the client as the Bank. Use British spelling. Never name a tool."
				/>
				<p class="text-xs text-muted-foreground">
					Passed to the model with every section. Leave it empty for the default voice.
				</p>
			</div>
		</div>
	{/if}
</div>
