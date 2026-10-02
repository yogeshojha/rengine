<script lang="ts">
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import { Label } from '$lib/components/ui/label';
	import type { ChoiceSpec } from '$lib/types/tripwire';
	import FireModeGlyph from './fire-mode-glyph.svelte';

	interface Props {
		modes: ChoiceSpec[];
		value: string;
		onChange: (value: string) => void;
		id?: string;
	}

	let { modes, value, onChange, id = 'fire-on' }: Props = $props();
</script>

<RadioGroup.Root {value} onValueChange={(v) => v && onChange(v)} class="grid gap-2 sm:grid-cols-3">
	{#each modes as mode (mode.key)}
		<Label
			for="{id}-{mode.key}"
			class="flex cursor-pointer flex-col items-stretch gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-muted/40 has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5"
		>
			<span class="flex items-center justify-between gap-3">
				<span class="flex items-center gap-2.5">
					<RadioGroup.Item value={mode.key} id="{id}-{mode.key}" />
					<span class="text-sm font-medium">{mode.label}</span>
				</span>
				<FireModeGlyph mode={mode.key} />
			</span>
			<span class="text-xs leading-relaxed font-normal text-muted-foreground">{mode.help}</span>
		</Label>
	{/each}
</RadioGroup.Root>
<p class="mt-2 text-2xs text-muted-foreground">
	In each picture the left box is the previous run and the right box is this run. Bars are rows the
	query matches. The tinted bar is the row that fires.
</p>
