<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import X from '@lucide/svelte/icons/x';

	interface Props {
		items: string[];
		onChange: (items: string[]) => void;
		placeholder?: string;
		/** Names each row for assistive tech, numbered. */
		label?: string;
		validate?: (v: string) => string | null;
	}

	let { items, onChange, placeholder = '', label, validate }: Props = $props();

	const uid = $props.id();

	let rows = $derived(items.length === 0 ? [''] : [...items, '']);

	function commit(next: string[]) {
		onChange(next.map((v) => v.trim()).filter((v) => v !== ''));
	}

	function updateRow(i: number, value: string) {
		const next = [...rows];
		next[i] = value;
		commit(next);
	}

	function removeRow(i: number) {
		const next = rows.filter((_, idx) => idx !== i);
		commit(next);
	}

	function onKeydown(e: KeyboardEvent, i: number) {
		if (e.key === 'Enter' && i === rows.length - 1 && rows[i].trim() !== '') {
			e.preventDefault();
		}
	}

	function errorFor(v: string): string | null {
		if (!validate || v.trim() === '') return null;
		return validate(v.trim());
	}
</script>

<div class="space-y-2">
	{#each rows as row, i (i)}
		{@const error = errorFor(row)}
		<div class="space-y-1.5">
			<div class="flex items-center gap-2">
				<Input
					value={row}
					{placeholder}
					aria-label={label ? `${label} ${i + 1}` : undefined}
					aria-invalid={error ? true : undefined}
					aria-describedby={error ? `${uid}-error-${i}` : undefined}
					class="h-9 flex-1 font-mono text-xs"
					oninput={(e) => updateRow(i, e.currentTarget.value)}
					onkeydown={(e) => onKeydown(e, i)}
				/>
				<Button
					variant="ghost"
					size="icon"
					class="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive"
					disabled={row.trim() === '' && rows.length === 1}
					onclick={() => removeRow(i)}
					aria-label="Remove"
				>
					<X class="h-4 w-4" />
				</Button>
			</div>
			{#if error}
				<p id="{uid}-error-{i}" class="text-sm text-destructive" role="alert">{error}</p>
			{/if}
		</div>
	{/each}
</div>
