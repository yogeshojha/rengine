<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { ROUTES } from '$lib/config/routes';
	import { notificationProviderMeta } from '$lib/config/notification-providers';
	import type { NotifProvider } from '$lib/types/notification-channel';
	import type { ChannelChoice } from '$lib/types/tripwire';

	interface Props {
		channels: ChannelChoice[];
		selected: string[];
		onChange: (ids: string[]) => void;
	}

	let { channels, selected, onChange }: Props = $props();

	function toggle(id: string, on: boolean) {
		onChange(on ? [...new Set([...selected, id])] : selected.filter((c) => c !== id));
	}
</script>

{#if channels.length === 0}
	<p class="text-xs text-muted-foreground">
		No notification channel is set up.
		<a
			href={ROUTES.settings('notifications')}
			target="_blank"
			rel="noreferrer noopener"
			class="text-foreground hover:text-primary">Notifications</a
		>
	</p>
{:else}
	<div class="flex flex-col gap-2">
		{#each channels as channel (channel.id)}
			{@const meta = notificationProviderMeta(channel.provider as NotifProvider)}
			{@const Icon = meta.icon}
			<label class="flex items-center gap-3 text-sm">
				<Checkbox
					checked={selected.includes(channel.id)}
					onCheckedChange={(v) => toggle(channel.id, v === true)}
				/>
				<Icon class="size-4 text-muted-foreground" />
				<span class="min-w-0 truncate">{channel.name}</span>
				<span class="text-xs text-muted-foreground">{meta.name}</span>
			</label>
		{/each}
	</div>
	{#if selected.length === 0}
		<p class="text-xs text-muted-foreground">
			With none chosen, the channels subscribed to Tripwires receive the message.
		</p>
	{/if}
{/if}
