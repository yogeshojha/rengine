<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import TagIcon from '@lucide/svelte/icons/tag';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { ROUTES } from '$lib/config/routes';
	import { quote } from '$lib/utilities/scan-query';
	import ScanTagPicker from './scan-tag-picker.svelte';

	interface Props {
		tags: string[];
		onToggle: (name: string, on: boolean) => void;
		disabled?: boolean;
		linked?: boolean;
	}

	let { tags, onToggle, disabled = false, linked = false }: Props = $props();

	const CHIP = 'inline-flex h-6 items-center gap-1 rounded-md border border-border/70 text-xs';
</script>

<div class="flex flex-wrap items-center gap-1.5">
	{#each tags as name (name)}
		<span class="{CHIP} pr-0.5 pl-1.5">
			<TagIcon class="size-3 text-muted-foreground" />
			{#if linked}
				<a
					href={ROUTES.scansWhere({ q: `tag:${quote(name)}` })}
					class="text-foreground hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					{name}
				</a>
			{:else}
				<span class="text-foreground">{name}</span>
			{/if}
			<button
				type="button"
				class="inline-flex size-4 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				aria-label="Remove tag {name}"
				{disabled}
				onclick={() => onToggle(name, false)}
			>
				<X class="size-3" />
			</button>
		</span>
	{/each}
	<ScanTagPicker applied={tags} {onToggle} {disabled}>
		{#snippet trigger(props)}
			<Button {...props} variant="outline" size="sm" class="h-6 px-2 text-xs">
				<Plus class="size-3" />
				Add tag
			</Button>
		{/snippet}
	</ScanTagPicker>
</div>
