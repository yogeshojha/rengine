<script lang="ts">
	import TokenForm from './token-form.svelte';
	import { CHANNEL_META, type ChannelKind } from '$lib/config/channels';
	import { externalHref } from '$lib/utilities/links';

	interface Props {
		channel: ChannelKind;
		label: string;
		canAdmin: boolean;
	}

	let { channel, label, canAdmin }: Props = $props();

	const meta = $derived(CHANNEL_META[channel]);
</script>

<section class="flex max-w-xl flex-col gap-5 px-5 py-8">
	<div>
		<h2 class="text-base font-semibold">Connect a {label} bot</h2>
		{#if !canAdmin}
			<p class="mt-1 text-sm text-muted-foreground">No bot connected.</p>
		{/if}
	</div>
	{#if canAdmin}
		<ol class="flex flex-col gap-4 text-sm">
			<li class="flex gap-3">
				<span
					class="grid size-5 shrink-0 place-items-center rounded-full border font-mono text-2xs text-muted-foreground"
					>1</span
				>
				<span class="leading-5">
					Create a bot with
					<a
						href={externalHref(meta.tokenSourceUrl)}
						target="_blank"
						rel="noopener noreferrer"
						class="font-medium text-primary hover:text-primary/80">{meta.tokenSource}</a
					>
					and copy its token.
				</span>
			</li>
			<li class="flex gap-3">
				<span
					class="grid size-5 shrink-0 place-items-center rounded-full border font-mono text-2xs text-muted-foreground"
					>2</span
				>
				<div class="flex min-w-0 flex-1 flex-col gap-2">
					<span class="leading-5">Paste the token.</span>
					<TokenForm {channel} action="Connect" />
				</div>
			</li>
		</ol>
	{/if}
</section>
