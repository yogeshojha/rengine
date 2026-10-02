<script lang="ts">
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import TokenForm from './token-form.svelte';
	import { CHANNEL_META, RATE_LIMIT_MAX, RATE_LIMIT_MIN } from '$lib/config/channels';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import type { ChannelStatus } from '$lib/types/remote-control';
	import type { McpCapability } from '$lib/types/mcp';

	interface Props {
		status: ChannelStatus;
		open: boolean;
	}

	let { status, open = $bindable() }: Props = $props();

	let rateDraft = $state<string | null>(null);
	let changing = $state(false);
	let confirmDisconnect = $state(false);

	const meta = $derived(CHANNEL_META[status.channel]);
	const rate = $derived(rateDraft ?? String(status.rate_limit_per_minute));

	async function setCeiling(key: McpCapability, value: boolean) {
		await remoteControl.save({ ceiling: { ...status.ceiling, [key]: value } });
	}

	async function commitRate() {
		if (rateDraft === null) return;
		const value = Math.min(
			RATE_LIMIT_MAX,
			Math.max(RATE_LIMIT_MIN, Math.round(Number(rateDraft) || 0))
		);
		rateDraft = null;
		if (value !== status.rate_limit_per_minute)
			await remoteControl.save({ rate_limit_per_minute: value }, 'Rate limit saved');
	}

	const disconnectText = $derived(
		[
			`${status.bot ? `Bot @${status.bot.username}` : 'The bot'} is disconnected.`,
			status.chats_total
				? `Its ${status.chats_total} paired chat${status.chats_total === 1 ? ' is' : 's are'} removed.`
				: '',
			`The ${status.label} API key is deleted.`,
			status.shared_notifications
				? `${status.shared_notifications} notification channel${status.shared_notifications === 1 ? ' stops' : 's stop'} sending.`
				: ''
		]
			.filter(Boolean)
			.join(' ')
	);

	async function disconnect() {
		confirmDisconnect = false;
		if (await remoteControl.disconnect()) open = false;
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>{status.label} settings</Sheet.Title>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col divide-y px-5">
				<section class="flex flex-col gap-3 py-5">
					<SectionHead title="Bot" />
					<div class="flex flex-wrap items-baseline justify-between gap-2">
						{#if status.bot}
							<a
								href={meta.chatUrl(status.bot.username)}
								target="_blank"
								rel="noopener noreferrer"
								class="font-mono text-sm text-primary hover:text-primary/80"
								>@{status.bot.username}</a
							>
						{/if}
						<span class="font-mono text-xs text-muted-foreground">{status.secret_masked}</span>
					</div>
					{#if changing}
						<TokenForm channel={status.channel} action="Save" onDone={() => (changing = false)} />
						{#if status.chats_total}
							<span class="text-xs text-muted-foreground">
								A token for a different bot removes the {status.chats_total} paired chat{status.chats_total ===
								1
									? ''
									: 's'}.
							</span>
						{/if}
					{/if}
					<div class="flex flex-wrap gap-2">
						<Button variant="outline" size="sm" onclick={() => (changing = !changing)}>
							{changing ? 'Cancel' : 'Change bot'}
						</Button>
						<Button
							variant="outline"
							size="sm"
							class="text-destructive hover:text-destructive"
							onclick={() => (confirmDisconnect = true)}
						>
							Disconnect bot
						</Button>
					</div>
				</section>

				<section class="flex flex-col gap-3 py-5">
					<SectionHead title="Ceiling" />
					{#each status.capabilities as capability (capability.key)}
						{@const on = capability.always || (status.ceiling[capability.key] ?? false)}
						<div class="flex items-start justify-between gap-4">
							<span class="flex min-w-0 flex-col">
								<span class="flex items-center gap-1.5 text-sm leading-5 font-medium">
									{capability.label}
									{#if capability.touches_targets}
										<TriangleAlertIcon class="size-3.5 text-warning" aria-label="Reaches targets" />
									{/if}
								</span>
								<span class="text-xs text-muted-foreground">{capability.help}</span>
							</span>
							<span class="flex h-5 shrink-0 items-center">
								<Switch
									checked={on}
									disabled={capability.always || remoteControl.isSaving}
									onCheckedChange={(v) => setCeiling(capability.key, v)}
									aria-label="Allow {capability.label}"
								/>
							</span>
						</div>
					{/each}
					<p class="text-xs text-muted-foreground">
						Capabilities above read are confirmed with the account's authenticator code.
					</p>
				</section>

				<section class="flex flex-col gap-2.5 py-5">
					<SectionHead title="Rate limit" />
					<label class="flex items-center gap-2 text-sm" for="rc-rate">
						<Input
							id="rc-rate"
							type="number"
							min={RATE_LIMIT_MIN}
							max={RATE_LIMIT_MAX}
							class="h-8 w-20 text-right font-mono text-xs tabular-nums"
							value={rate}
							oninput={(e) => (rateDraft = e.currentTarget.value)}
							onblur={commitRate}
							onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
						/>
						<span class="text-xs text-muted-foreground">commands per minute, per chat</span>
					</label>
				</section>
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	bind:open={confirmDisconnect}
	title="Disconnect bot"
	description={disconnectText}
	confirmLabel="Disconnect"
	destructive
	loading={remoteControl.isSaving}
	onOpenChange={(v) => (confirmDisconnect = v)}
	onConfirm={disconnect}
/>
