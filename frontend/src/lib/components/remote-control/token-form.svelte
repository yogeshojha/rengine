<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { CHANNEL_META, type ChannelKind } from '$lib/config/channels';

	interface Props {
		channel: ChannelKind;
		action: string;
		token?: string;
		onDone?: () => void;
	}

	let { channel, action, token = $bindable(''), onDone }: Props = $props();
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

<form onsubmit={submit}>
	<FormField label="Bot token" error={error ?? undefined}>
		{#snippet children({ id })}
			<div class="flex flex-wrap gap-2">
				<Input
					{id}
					bind:value={token}
					type="password"
					autocomplete="off"
					spellcheck={false}
					placeholder={meta.tokenPlaceholder}
					aria-invalid={error ? true : undefined}
					oninput={() => (error = null)}
					class="h-9 min-w-0 flex-1 font-mono text-xs"
				/>
				<LoadingButton
					type="submit"
					loading={remoteControl.isSaving}
					loadingLabel="Checking"
					disabled={!token.trim()}
				>
					{action}
				</LoadingButton>
			</div>
		{/snippet}
	</FormField>
</form>
