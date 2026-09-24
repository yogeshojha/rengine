<script lang="ts">
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import { Button } from '$lib/components/ui/button';
	import SectionHead from '$lib/components/section-head.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { CHANNEL_META, type ChannelKind } from '$lib/config/channels';

	interface Props {
		channel: ChannelKind;
		canAdmin: boolean;
	}

	let { channel, canAdmin }: Props = $props();

	const meta = $derived(CHANNEL_META[channel]);
</script>

<section class="flex flex-col gap-4 py-5">
	<SectionHead title="Bot">
		<a
			href={meta.createUrl}
			target="_blank"
			rel="noopener noreferrer"
			class="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
		>
			{meta.createLabel}
			<ExternalLinkIcon class="size-3" />
		</a>
	</SectionHead>
	<EmptyState compact icon={KeyRoundIcon} title="No {meta.apiKeyLabel}">
		{#if canAdmin}
			<Button size="sm" href={ROUTES.settings('api-keys')}>Add API key</Button>
		{/if}
	</EmptyState>
</section>
