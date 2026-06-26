<script lang="ts">
	import CirclePlus from '@lucide/svelte/icons/circle-plus';
	import Check from '@lucide/svelte/icons/check';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import { cn } from '$lib/utils';
	import type { Facet } from '$lib/utilities/scan-insights';

	interface Props {
		title: string;
		options: Facet[];
		selected: string[];
		onChange: (next: string[]) => void;
	}

	let { title, options, selected, onChange }: Props = $props();
	let open = $state(false);

	function toggle(value: string) {
		onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button variant="outline" size="sm" class="h-8 border-dashed" {...props}>
				<CirclePlus data-icon="inline-start" />
				{title}
				{#if selected.length}
					<Separator orientation="vertical" class="mx-0.5 h-4" />
					<Badge variant="secondary" class="rounded-sm px-1 font-normal lg:hidden">
						{selected.length}
					</Badge>
					<div class="hidden gap-1 lg:flex">
						{#if selected.length > 2}
							<Badge variant="secondary" class="rounded-sm px-1 font-normal">
								{selected.length} selected
							</Badge>
						{:else}
							{#each options.filter((o) => selected.includes(o.value)) as o (o.value)}
								<Badge variant="secondary" class="rounded-sm px-1 font-normal">{o.label}</Badge>
							{/each}
						{/if}
					</div>
				{/if}
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-56 p-0" align="start">
		<Command.Root>
			<Command.Input placeholder={title} />
			<Command.List>
				<Command.Empty>No matches.</Command.Empty>
				<Command.Group>
					{#each options as option (option.value)}
						{@const isSel = selected.includes(option.value)}
						<Command.Item value={option.value} onSelect={() => toggle(option.value)}>
							<div
								class={cn(
									'flex size-4 items-center justify-center rounded-sm border',
									isSel
										? 'border-primary bg-primary text-primary-foreground'
										: 'border-muted-foreground/40 [&_svg]:invisible'
								)}
							>
								<Check class="size-3" />
							</div>
							<span class="truncate">{option.label}</span>
							<span class="ml-auto font-mono text-xs text-muted-foreground">{option.count}</span>
						</Command.Item>
					{/each}
				</Command.Group>
				{#if selected.length}
					<Command.Separator />
					<Command.Group>
						<Command.Item value="__clear" onSelect={() => onChange([])} class="justify-center">
							Clear
						</Command.Item>
					</Command.Group>
				{/if}
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
