<script lang="ts">
	import BuildingIcon from '@lucide/svelte/icons/building-2';
	import TagIcon from '@lucide/svelte/icons/tag';
	import XIcon from '@lucide/svelte/icons/x';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import { Switch } from '$lib/components/ui/switch';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { MAX_IMPORT_TAGS } from '$lib/config/bounty-programs';
	import type { BountyProgram } from '$lib/types/bounty-program';

	interface Props {
		program: BountyProgram;
		count: number;
		outOfScopeCount: number;
		open: boolean;
		importing: boolean;
		onOpenChange: (open: boolean) => void;
		onConfirm: (options: {
			groupByProgram: boolean;
			organizationName: string;
			tags: string[];
		}) => void;
	}

	let { program, count, outOfScopeCount, open, importing, onOpenChange, onConfirm }: Props =
		$props();

	let groupByProgram = $state(true);
	let organizationName = $state('');
	let tags = $state<string[]>([]);
	let draft = $state('');

	// reset on open
	$effect(() => {
		if (!open) return;
		groupByProgram = true;
		organizationName = program.name;
		tags = [program.platform];
		draft = '';
	});

	const atTagLimit = $derived(tags.length >= MAX_IMPORT_TAGS);

	function addTag() {
		const name = draft.trim().toLowerCase();
		if (!name || atTagLimit) return;
		if (!tags.includes(name)) tags = [...tags, name];
		draft = '';
	}

	function removeTag(name: string) {
		tags = tags.filter((t) => t !== name);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ',') {
			event.preventDefault();
			addTag();
		} else if (event.key === 'Backspace' && !draft && tags.length > 0) {
			tags = tags.slice(0, -1);
		}
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Add {count} {count === 1 ? 'target' : 'targets'}</Dialog.Title>
			<Dialog.Description>
				From {program.name} on {program.platform_label}.
				{#if outOfScopeCount > 0}
					{outOfScopeCount} out of scope.
				{/if}
			</Dialog.Description>
		</Dialog.Header>

		<div class="flex flex-col gap-5 py-2">
			<div class="flex flex-col gap-3">
				<div class="flex items-center justify-between gap-4">
					<div class="flex items-center gap-2">
						<BuildingIcon class="size-4 text-muted-foreground" />
						<span class="text-sm font-medium">Group as an organization</span>
					</div>
					<Switch checked={groupByProgram} onCheckedChange={(v) => (groupByProgram = v)} />
				</div>
				{#if groupByProgram}
					<FormField label="Organization name">
						{#snippet children({ id })}
							<Input {id} bind:value={organizationName} placeholder={program.name} />
						{/snippet}
					</FormField>
				{/if}
			</div>

			<div class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<TagIcon class="size-4 text-muted-foreground" />
					<span class="text-sm font-medium">Tags</span>
				</div>
				<div class="flex flex-wrap items-center gap-1.5">
					{#each tags as tag (tag)}
						<Badge variant="secondary" class="gap-1 pr-1">
							{tag}
							<button
								type="button"
								onclick={() => removeTag(tag)}
								class="rounded-sm text-muted-foreground hover:text-foreground"
								aria-label={`Remove ${tag}`}
							>
								<XIcon class="size-3" />
							</button>
						</Badge>
					{/each}
				</div>
				<Input
					bind:value={draft}
					onkeydown={onKeydown}
					onblur={addTag}
					disabled={atTagLimit}
					placeholder={atTagLimit ? `${MAX_IMPORT_TAGS} tags maximum` : 'Add a tag'}
				/>
			</div>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton
				loading={importing}
				onclick={() =>
					onConfirm({
						groupByProgram,
						organizationName: organizationName.trim(),
						tags
					})}
			>
				Add {count}
				{count === 1 ? 'target' : 'targets'}
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
