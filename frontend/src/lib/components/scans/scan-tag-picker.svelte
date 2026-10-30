<script lang="ts">
	import type { Snippet } from 'svelte';
	import Check from '@lucide/svelte/icons/check';
	import Minus from '@lucide/svelte/icons/minus';
	import Plus from '@lucide/svelte/icons/plus';
	import * as Command from '$lib/components/ui/command';
	import * as Popover from '$lib/components/ui/popover';
	import { scanTagsApi } from '$lib/api/scan-tags';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { MAX_SCAN_TAG_LENGTH } from '$lib/types/scan';

	interface Props {
		applied: string[];
		partial?: string[];
		onToggle: (name: string, on: boolean) => void;
		disabled?: boolean;
		align?: 'start' | 'center' | 'end';
		trigger: Snippet<[Record<string, unknown>]>;
	}

	let {
		applied,
		partial = [],
		onToggle,
		disabled = false,
		align = 'start',
		trigger
	}: Props = $props();

	let open = $state(false);
	let search = $state('');
	let known = $state<string[]>([]);

	let typed = $derived(search.split(/\s+/).filter(Boolean).join(' ').toLowerCase());
	let names = $derived([...new Set([...applied, ...partial, ...known])].sort());
	let shown = $derived(typed ? names.filter((n) => n.includes(typed)) : names);
	let canCreate = $derived(
		typed !== '' && typed.length <= MAX_SCAN_TAG_LENGTH && !names.includes(typed)
	);

	async function load() {
		const projectId = projectsStore.activeProject?.id;
		if (!projectId) return;
		try {
			known = (await scanTagsApi.list(projectId)).map((t) => t.name);
		} catch {
			known = [];
		}
	}

	function onOpenChange(next: boolean) {
		open = next;
		if (next) void load();
		else search = '';
	}

	function toggle(name: string) {
		onToggle(name, !applied.includes(name));
	}

	function create() {
		onToggle(typed, true);
		search = '';
	}
</script>

<Popover.Root {open} {onOpenChange}>
	<Popover.Trigger {disabled}>
		{#snippet child({ props })}
			{@render trigger(props)}
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-60 p-0" {align}>
		<Command.Root shouldFilter={false}>
			<Command.Input
				placeholder="Find or create a tag"
				bind:value={search}
				maxlength={MAX_SCAN_TAG_LENGTH}
			/>
			<Command.List class="max-h-72">
				{#if !shown.length && !canCreate}
					<Command.Empty>No tags</Command.Empty>
				{/if}
				{#if shown.length}
					<Command.Group>
						{#each shown as name (name)}
							<Command.Item value={name} onSelect={() => toggle(name)} {disabled}>
								<span class="flex-1 truncate">{name}</span>
								{#if applied.includes(name)}
									<Check class="size-4 text-primary" />
								{:else if partial.includes(name)}
									<Minus class="size-4 text-muted-foreground" />
								{/if}
							</Command.Item>
						{/each}
					</Command.Group>
				{/if}
				{#if canCreate}
					<Command.Group>
						<Command.Item value="__create__" onSelect={create} {disabled}>
							<Plus class="size-4" />
							<span class="truncate">Create <span class="font-medium">{typed}</span></span>
						</Command.Item>
					</Command.Group>
				{/if}
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
