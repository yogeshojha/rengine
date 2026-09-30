<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox';
	import type { StageChoice } from '$lib/types/tripwire';

	interface Props {
		stages: StageChoice[];
		selected: string[];
		onChange: (names: string[]) => void;
	}

	let { stages, selected, onChange }: Props = $props();

	function toggle(name: string, on: boolean) {
		onChange(on ? [...new Set([...selected, name])] : selected.filter((s) => s !== name));
	}
</script>

<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
	{#each stages as stage (stage.name)}
		<label class="flex items-center gap-3 text-sm">
			<Checkbox
				checked={selected.includes(stage.name)}
				onCheckedChange={(v) => toggle(stage.name, v === true)}
			/>
			<span class="min-w-0 truncate">{stage.title}</span>
		</label>
	{/each}
</div>
{#if selected.length === 0}
	<p class="text-xs text-destructive">Choose at least one stage.</p>
{/if}
