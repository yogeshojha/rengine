<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { CHANNEL_META, type ChannelKind } from '$lib/config/channels';

	interface Props {
		channel: ChannelKind;
		action: string;
		onDone?: () => void;
	}

	let { channel, action, onDone }: Props = $props();

	let token = $state('');
	let error = $state<string | null>(null);

	const meta = $derived(CHANNEL_META[channel]);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!token.trim()) return;
		error = await remoteControl.connect(token.trim());
		if (!error) {
			token = '';
			onDone?.();
		}
	}
</script>

<form class="flex flex-col gap-1.5" onsubmit={submit}>
	<div class="flex flex-wrap gap-2">
		<Input
			id="bot-token-{channel}"
			bind:value={token}
			type="password"
			autocomplete="off"
			spellcheck={false}
			placeholder={meta.tokenPlaceholder}
			aria-label="Bot token"
			aria-invalid={error ? true : undefined}
			class="h-9 min-w-0 flex-1 font-mono text-xs"
		/>
		<LoadingButton
			type="submit"
			class="h-9"
			loading={remoteControl.isSaving}
			loadingLabel="Checking"
			disabled={!token.trim()}
		>
			{action}
		</LoadingButton>
	</div>
	{#if error}
		<span class="text-xs text-destructive">{error}</span>
	{/if}
</form>
