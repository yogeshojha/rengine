<script lang="ts">
	import * as InputOTP from '$lib/components/ui/input-otp';
	import { TOTP_DIGITS } from '$lib/constants';

	interface Props {
		value: string;
		onValueChange: (v: string) => void;
		disabled?: boolean;
		id?: string;
		/** The underlying input, for callers that need to move focus into the code field. */
		inputRef?: HTMLInputElement | null;
	}

	let { value, onValueChange, disabled = false, id, inputRef = $bindable(null) }: Props = $props();

	const half = Math.ceil(TOTP_DIGITS / 2);

	function attachInput(node: HTMLInputElement) {
		inputRef = node;
		return () => {
			if (inputRef === node) inputRef = null;
		};
	}
</script>

<InputOTP.Root
	{value}
	{disabled}
	inputId={id}
	maxlength={TOTP_DIGITS}
	inputmode="numeric"
	onValueChange={(v) => onValueChange(v.replace(/\D/g, '').slice(0, TOTP_DIGITS))}
	{@attach attachInput}
>
	{#snippet children({ cells })}
		<InputOTP.Group>
			{#each cells.slice(0, half) as cell, i (i)}
				<InputOTP.Slot {cell} class="size-10 text-lg tabular-nums" />
			{/each}
		</InputOTP.Group>
		<InputOTP.Separator />
		<InputOTP.Group>
			{#each cells.slice(half) as cell, i (i)}
				<InputOTP.Slot {cell} class="size-10 text-lg tabular-nums" />
			{/each}
		</InputOTP.Group>
	{/snippet}
</InputOTP.Root>
