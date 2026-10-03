<script lang="ts">
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { uptime } from '$lib/utilities/dates';
	import type { McpCapability, McpStatus } from '$lib/types/mcp';
	import { toast } from 'svelte-sonner';

	interface Props {
		status: McpStatus;
		open: boolean;
	}

	let { status, open = $bindable() }: Props = $props();

	const RATE_MAX = 10_000;

	let rateDraft = $state<string | null>(null);
	let confirmStop = $state(false);

	const rate = $derived(rateDraft ?? String(status.rate_limit_per_minute));
	const connected = $derived(new Set(status.sessions.map((s) => s.token_id)).size);

	async function setCeiling(key: McpCapability, value: boolean) {
		if (await mcp.save({ ceiling: { ...status.ceiling, [key]: value } })) {
			toast.success('Ceiling saved');
			void mcp.loadTokens(true);
		}
	}

	async function commitRate() {
		if (rateDraft === null) return;
		const value = Math.min(RATE_MAX, Math.max(1, Math.round(Number(rateDraft) || 0)));
		rateDraft = null;
		if (value !== status.rate_limit_per_minute) {
			if (await mcp.save({ rate_limit_per_minute: value })) toast.success('Rate limit saved');
		}
	}

	async function stop() {
		if (await mcp.setRunning(false)) confirmStop = false;
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>Agent settings</Sheet.Title>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col divide-y px-5">
				<section class="flex flex-col gap-3 py-5">
					<SectionHead title="Server" />
					<div class="flex items-start justify-between gap-4">
						<div class="flex flex-col">
							<span class="text-sm font-medium">
								{status.enabled ? 'Running' : 'Stopped'}{#if status.enabled && status.started_at}
									<span class="font-normal text-muted-foreground"
										>{` · ${uptime(status.started_at)}`}</span
									>{/if}
							</span>
							<span class="text-xs text-muted-foreground"> Stopping disconnects every agent. </span>
						</div>
						{#if status.enabled}
							<Button
								variant="outline"
								size="sm"
								class="shrink-0 text-destructive hover:text-destructive"
								disabled={mcp.isSaving}
								onclick={() => (connected ? (confirmStop = true) : stop())}
							>
								Stop server
							</Button>
						{:else}
							<LoadingButton
								size="sm"
								class="shrink-0"
								loading={mcp.isSaving}
								loadingLabel="Starting"
								onclick={() => mcp.setRunning(true)}
							>
								Start server
							</LoadingButton>
						{/if}
					</div>
					<dl class="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-x-3 gap-y-2 text-sm">
						<dt class="text-xs leading-5 text-muted-foreground">Endpoint</dt>
						<dd class="flex min-w-0 items-start gap-1">
							<span class="min-w-0 font-mono text-xs leading-5 wrap-anywhere"
								>{status.endpoint}</span
							>
							<span class="flex h-5 shrink-0 items-center">
								<CopyButton value={status.endpoint} />
							</span>
						</dd>
						<dt class="text-xs leading-5 text-muted-foreground">Protocol</dt>
						<dd class="font-mono text-xs leading-5">{status.protocol_version}</dd>
						<dt class="text-xs leading-5 text-muted-foreground">stdio</dt>
						<dd class="flex min-w-0 items-start gap-1">
							<span class="min-w-0 font-mono text-xs leading-5 wrap-anywhere">
								{status.stdio_command}
							</span>
							<span class="flex h-5 shrink-0 items-center">
								<CopyButton value={status.stdio_command} />
							</span>
						</dd>
					</dl>
				</section>

				<section class="flex flex-col gap-3 py-5">
					<div class="flex flex-col gap-0.5">
						<SectionHead title="Ceiling" />
						<span class="text-xs text-muted-foreground">Highest access any key may hold.</span>
					</div>
					{#each status.capabilities as capability (capability.key)}
						{@const on = capability.always || (status.ceiling[capability.key] ?? false)}
						<div class="flex items-start justify-between gap-4">
							<span class="flex min-w-0 flex-col">
								<span class="flex items-center gap-1.5 text-sm leading-5 font-medium">
									{capability.label}
									{#if capability.always}
										<span class="text-2xs font-normal text-muted-foreground">required</span>
									{:else if capability.touches_targets}
										<TriangleAlertIcon class="size-3.5 text-warning" aria-label="Reaches targets" />
									{/if}
								</span>
								<span class="text-xs text-muted-foreground">{capability.help}</span>
							</span>
							<span class="flex h-5 shrink-0 items-center">
								<Switch
									checked={on}
									disabled={capability.always || mcp.isSaving}
									onCheckedChange={(v) => setCeiling(capability.key, v)}
									aria-label="Allow {capability.label}"
								/>
							</span>
						</div>
					{/each}
				</section>

				<section class="flex flex-col gap-2.5 py-5">
					<SectionHead title="Rate limit" />
					<label class="flex items-center gap-2 text-sm" for="agents-rate">
						<Input
							id="agents-rate"
							type="number"
							min="1"
							max={RATE_MAX}
							class="h-8 w-20 text-right font-mono text-xs tabular-nums"
							value={rate}
							oninput={(e) => (rateDraft = e.currentTarget.value)}
							onblur={commitRate}
							onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
						/>
						<span class="text-xs text-muted-foreground">calls per minute, per agent</span>
					</label>
				</section>
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	bind:open={confirmStop}
	title="Stop server"
	description="{connected} connected agent{connected === 1 ? ' is' : 's are'} disconnected."
	confirmLabel="Stop server"
	loadingLabel="Stopping"
	destructive
	loading={mcp.isSaving}
	onOpenChange={(v) => (confirmStop = v)}
	onConfirm={stop}
/>
