<script lang="ts">
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import Square from '@lucide/svelte/icons/square';
	import * as InputGroup from '$lib/components/ui/input-group';
	import Hint from '$lib/components/hint.svelte';
	import { MAX_QUESTION_CHARS } from '$lib/config/ask';

	interface Props {
		disabled?: boolean;
		busy?: boolean;
		placeholder?: string;
		onSend: (text: string) => void;
		onStop?: () => void;
	}

	let {
		disabled = false,
		busy = false,
		placeholder = 'Ask about this finding',
		onSend,
		onStop
	}: Props = $props();

	let text = $state('');
	let area = $state<HTMLTextAreaElement | null>(null);

	export function focus() {
		area?.focus();
	}
	let ready = $derived(!disabled && !busy && text.trim().length > 0);

	function send() {
		if (!ready) return;
		onSend(text.trim());
		text = '';
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
			e.preventDefault();
			send();
		}
	}
</script>

<InputGroup.Root class="rounded-xl bg-card">
	<InputGroup.Textarea
		bind:ref={area}
		bind:value={text}
		rows={1}
		maxlength={MAX_QUESTION_CHARS}
		{placeholder}
		{disabled}
		onkeydown={onKey}
		aria-label="Question"
		class="max-h-40 min-h-9 resize-none text-sm"
	/>
	<InputGroup.Addon align="block-end" class="justify-end">
		{#if busy}
			<Hint text="Discards the answer">
				{#snippet child(props)}
					<InputGroup.Button
						{...props}
						size="icon-sm"
						variant="outline"
						onclick={() => onStop?.()}
						aria-label="Stop"
					>
						<Square />
					</InputGroup.Button>
				{/snippet}
			</Hint>
		{:else}
			<InputGroup.Button
				size="icon-sm"
				variant="default"
				class="rounded-full"
				disabled={!ready}
				onclick={send}
				aria-label="Send"
			>
				<ArrowUp />
			</InputGroup.Button>
		{/if}
	</InputGroup.Addon>
</InputGroup.Root>
