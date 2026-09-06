<script lang="ts">
	import { untrack } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import { ROUTES } from '$lib/config/routes';
	import { emptyTemplateFilter } from '$lib/types/vuln-template';
	import type { VulnTemplateRead } from '$lib/types/vuln-template';

	interface Props {
		id: string;
		value: string[];
		onChange: (value: string[]) => void;
	}

	let { id, value, onChange }: Props = $props();

	let templates = $state<VulnTemplateRead[]>([]);
	let loaded = $state(false);

	$effect(() => {
		untrack(() => {
			vulnTemplatesApi
				.search({ ...emptyTemplateFilter(), origins: ['custom'], limit: 200 })
				.then((res) => (templates = res.items))
				.catch(() => (templates = []))
				.finally(() => (loaded = true));
		});
	});

	let items = $derived(templates.map((t) => ({ id: t.id, label: t.name })));
	let selected = $derived(
		value.map((id) => ({ id, label: templates.find((t) => t.id === id)?.name ?? id }))
	);
</script>

{#if loaded && templates.length === 0}
	<div class="w-[280px] text-right">
		<p class="text-[11px] text-muted-foreground">No templates uploaded yet.</p>
		<Button
			variant="link"
			size="sm"
			class="h-auto px-0 text-[11px]"
			href={ROUTES.arsenal('nuclei')}
		>
			Upload one in the Tools Arsenal
		</Button>
	</div>
{:else}
	<div class="w-[280px] space-y-1">
		<MultiSelectCombobox
			{id}
			{items}
			{selected}
			onSelect={(item) => onChange(value.includes(item.id) ? value : [...value, item.id])}
			onRemove={(item) => onChange(value.filter((v) => v !== item.id))}
			allowCreate={false}
			placeholder="Search templates…"
			emptyText="No uploaded templates match."
		/>
		{#if value.length}
			<Badge variant="secondary" class="text-[10px] font-normal">
				{value.length} selected, always run
			</Badge>
		{/if}
	</div>
{/if}
