<script lang="ts">
	import { IME_KEY_CODE } from '$lib/constants';
	import type { Snippet } from 'svelte';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import Brain from '@lucide/svelte/icons/brain';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Square from '@lucide/svelte/icons/square';
	import X from '@lucide/svelte/icons/x';
	import * as InputGroup from '$lib/components/ui/input-group';
	import Hint from '$lib/components/hint.svelte';
	import { ABOUT_SEPARATOR, BLOCK_ID, MAX_QUESTION_CHARS } from '$lib/config/ask';
	import { surfaceSpec } from '$lib/config/surface';
	import { cn } from '$lib/utils.js';

	export interface About {
		id: string;
		label: string;
	}

	interface Props {
		about?: About | null;
		intelligent: boolean;
		disabled?: boolean;
		busy?: boolean;
		hero?: boolean;
		placeholder?: string;
		leading?: Snippet;
		sendable?: boolean;
		onClearAbout?: () => void;
		onIntelligent: (on: boolean) => void;
		onSend: (text: string) => void;
		onStop?: () => void;
	}

	let {
		about = null,
		intelligent,
		disabled = false,
		busy = false,
		hero = false,
		placeholder = 'Ask about web assets, findings, endpoints and services',
		leading,
		sendable = true,
		onClearAbout,
		onIntelligent,
		onSend,
		onStop
	}: Props = $props();

	let text = $state('');

	function aboutNoun(value: string): string {
		const noun = surfaceSpec(value.split(ABOUT_SEPARATOR, 1)[0])?.noun ?? 'row';
		return noun.charAt(0).toUpperCase() + noun.slice(1);
	}
	let area = $state<HTMLTextAreaElement | null>(null);
	let ready = $derived(sendable && !disabled && !busy && text.trim().length > 0);

	export function focus() {
		area?.focus();
	}

	export function value(): string {
		return text;
	}

	export function fill(value: string) {
		text = value;
		queueMicrotask(() => {
			area?.focus();
			area?.setSelectionRange(value.length, value.length);
		});
	}

	function send() {
		if (!ready) return;
		onSend(text.trim());
		text = '';
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== IME_KEY_CODE) {
			e.preventDefault();
			send();
		}
	}
</script>

<InputGroup.Root
	class={cn(
		'rounded-2xl bg-card/95 shadow-sm backdrop-blur transition-[translate,box-shadow] duration-200 ease-out has-[textarea:focus-visible]:border-ring has-[textarea:focus]:shadow-md motion-safe:has-[textarea:focus]:-translate-y-0.5 dark:bg-card/95',
		hero && 'shadow-lg shadow-primary/5 has-[textarea:focus]:shadow-xl'
	)}
>
	<InputGroup.Textarea
		bind:ref={area}
		bind:value={text}
		rows={hero ? 2 : 1}
		maxlength={MAX_QUESTION_CHARS}
		{placeholder}
		{disabled}
		onkeydown={onKey}
		aria-label="Question"
		class={cn('max-h-48 resize-none', hero ? 'min-h-16 px-4 pt-4 text-base' : 'min-h-10 text-sm')}
	/>
	<InputGroup.Addon align="block-end" class="flex-wrap gap-2 px-3 pb-2.5">
		{@render leading?.()}
		{#if about}
			<span
				class="inline-flex h-7 max-w-[22rem] min-w-0 items-center gap-1.5 rounded-md border border-primary/25 bg-primary/5 pr-1 pl-2 text-xs text-primary"
			>
				<Sparkles class="size-3 shrink-0" />
				{#if BLOCK_ID.test(about.id)}
					<span class="shrink-0 font-mono font-semibold">{about.id}</span>
				{:else}
					<span class="shrink-0 font-semibold">{aboutNoun(about.id)}</span>
				{/if}
				<span class="truncate text-foreground/80">{about.label}</span>
				{#if onClearAbout}
					<button
						type="button"
						class="inline-flex size-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-primary/10 hover:text-foreground"
						onclick={onClearAbout}
						aria-label="Ask about everything in scope"
					>
						<X class="size-3" />
					</button>
				{/if}
			</span>
		{/if}
		<Hint text="Checks one more fact and writes follow-ups. Uses more AI tokens.">
			{#snippet child(props)}
				<button
					{...props}
					type="button"
					role="switch"
					aria-checked={intelligent}
					{disabled}
					onclick={() => onIntelligent(!intelligent)}
					class={cn(
						'inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-xs font-medium transition-colors disabled:opacity-50',
						intelligent
							? 'border-primary/30 bg-primary/10 text-primary'
							: 'border-transparent text-muted-foreground hover:bg-muted hover:text-foreground'
					)}
				>
					<Brain class="size-3.5" />
					Intelligent
				</button>
			{/snippet}
		</Hint>
		<span class="ml-auto"></span>
		{#if busy}
			<Hint text="Discards the answer">
				{#snippet child(props)}
					<InputGroup.Button
						{...props}
						size="icon-sm"
						variant="outline"
						class="rounded-full"
						onclick={() => onStop?.()}
						aria-label="Stop"
					>
						<Square class="size-3" />
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
				aria-label="Ask"
			>
				<ArrowUp />
			</InputGroup.Button>
		{/if}
	</InputGroup.Addon>
</InputGroup.Root>
