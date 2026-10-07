<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	let {
		label,
		options,
		selected = $bindable()
	}: {
		label: string;
		options: { key: string; label: string; count: number }[];
		selected: string[];
	} = $props();

	function toggle(key: string) {
		selected = selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key];
	}
</script>

{#if options.length > 1}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					class={selected.length ? 'border-primary/50 bg-primary/5' : ''}
				>
					{label}
					{#if selected.length}
						<Badge variant="secondary" class="h-5 px-1.5 text-xs">{selected.length}</Badge>
					{/if}
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-48">
			{#each options as o (o.key)}
				<DropdownMenu.CheckboxItem
					checked={selected.includes(o.key)}
					onCheckedChange={() => toggle(o.key)}
					closeOnSelect={false}
				>
					<span class="flex-1 truncate">{o.label}</span>
					<span class="font-mono text-2xs text-muted-foreground">{o.count}</span>
				</DropdownMenu.CheckboxItem>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}
