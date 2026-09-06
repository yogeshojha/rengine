<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import PlayIcon from '@lucide/svelte/icons/play';
	import SquareIcon from '@lucide/svelte/icons/square';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import PanelHead from '$lib/components/panel-head.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CopyButton from '$lib/components/copy-button.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { relativeTime } from '$lib/utilities/dates';
	import { TOUCHES_TARGETS, type McpCapability } from '$lib/types/mcp';

	interface Props {
		canAdmin: boolean;
		onIssueToken: () => void;
	}

	let { canAdmin, onIssueToken }: Props = $props();

	let confirmStop = $state(false);
	let copied = $state('');
	let transport = $state<'http' | 'stdio'>('http');
	let rateLimit = $state<number | null>(null);

	const status = $derived(mcp.status);
	const running = $derived(status?.enabled ?? false);
	const sessions = $derived(status?.sessions ?? []);
	const rate = $derived(rateLimit ?? status?.rate_limit_per_minute ?? 120);

	const stdioSnippet = $derived(
		JSON.stringify(
			{
				mcpServers: {
					rengine: {
						command: 'docker',
						args: ['compose', 'exec', '-T', 'api', '/app/.venv/bin/python', '-m', 'mcp.stdio'],
						env: { RENGINE_MCP_TOKEN: 'paste-your-token-here' }
					}
				}
			},
			null,
			2
		)
	);

	async function start() {
		await mcp.setRunning(true);
	}

	async function stop() {
		confirmStop = false;
		await mcp.setRunning(false);
	}

	function requestStop() {
		if (sessions.length) confirmStop = true;
		else void stop();
	}

	async function setCeiling(key: McpCapability, value: boolean) {
		const next = { ...(status?.ceiling ?? {}), [key]: value };
		await mcp.save({ ceiling: next as Record<string, boolean> });
	}

	async function copy(value: string, key: string) {
		if (await writeClipboard(value)) {
			copied = key;
			setTimeout(() => (copied = copied === key ? '' : copied), 1600);
		}
	}

	async function commitRate() {
		if (rateLimit === null || rateLimit === status?.rate_limit_per_minute) return;
		const value = Math.min(10000, Math.max(1, Math.round(rateLimit)));
		await mcp.save({ rate_limit_per_minute: value });
		rateLimit = null;
	}
</script>

{#if status}
	<div class="space-y-6">
		<Card.Root class="gap-0 py-0">
			<div class="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
				<div class="flex items-center gap-3">
					<span
						class="size-2.5 shrink-0 rounded-full {running
							? 'bg-success shadow-[0_0_0_3px] shadow-success/20'
							: 'bg-muted-foreground/50'}"
					></span>
					<div class="flex flex-col gap-0.5">
						<span class="text-base leading-6 font-semibold">
							{running ? 'Accepting connections' : 'Stopped'}
						</span>
						<span class="text-xs text-muted-foreground">
							{#if running}
								Started {relativeTime(status.started_at)} &middot;
								{sessions.length} agent{sessions.length === 1 ? '' : 's'} connected &middot;
								{status.calls_today} call{status.calls_today === 1 ? '' : 's'} today
							{:else}
								No agent can reach this instance.
							{/if}
						</span>
					</div>
				</div>

				<div class="flex items-center gap-2">
					{#if running}
						<Button variant="outline" size="sm" onclick={() => copy(status.endpoint, 'endpoint')}>
							{#if copied === 'endpoint'}
								<CheckIcon class="size-4" />Copied
							{:else}
								<CopyIcon class="size-4" />Copy endpoint
							{/if}
						</Button>
						<Hint text={canAdmin ? '' : 'Only an administrator can stop the server.'}>
							{#snippet child({ props })}
								<span class="inline-flex">
									<Button
										{...props as Record<string, unknown>}
										variant="outline"
										size="sm"
										disabled={!canAdmin || mcp.isSaving}
										onclick={requestStop}
										class="text-destructive hover:text-destructive"
									>
										<SquareIcon class="size-4" />
										Stop server
									</Button>
								</span>
							{/snippet}
						</Hint>
					{:else}
						<Hint text={canAdmin ? '' : 'Only an administrator can start the server.'}>
							{#snippet child({ props })}
								<span class="inline-flex">
									<LoadingButton
										{...props as Record<string, unknown>}
										size="sm"
										loading={mcp.isSaving}
										disabled={!canAdmin}
										onclick={start}
									>
										<PlayIcon class="size-4" />
										Start server
									</LoadingButton>
								</span>
							{/snippet}
						</Hint>
					{/if}
				</div>
			</div>

			<div class="grid grid-cols-2 border-t sm:grid-cols-3 lg:grid-cols-5">
				{#snippet cell(label: string, value: string, mono = false)}
					<div class="flex min-w-0 flex-col gap-0.5 border-r px-5 py-3 last:border-r-0">
						<span class="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
							{label}
						</span>
						<span class="truncate text-sm {mono ? 'font-mono text-xs' : ''}">{value}</span>
					</div>
				{/snippet}
				{@render cell('Endpoint', status.endpoint.replace(/^https?:\/\//, ''), true)}
				{@render cell('Protocol', status.protocol_version, true)}
				{@render cell('Tools exposed', `${status.tools_available} of ${status.tools_total}`)}
				{@render cell('Tokens', `${status.tokens_active} active`)}
				{@render cell('Rate limit', `${status.rate_limit_per_minute} / min`)}
			</div>
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead title="Transport" description="How an agent reaches the server">
				<div class="flex rounded-md bg-muted p-0.5">
					{#each ['http', 'stdio'] as const as option (option)}
						<button
							type="button"
							class="rounded-sm px-3 py-1 text-xs {transport === option
								? 'bg-background font-medium text-foreground shadow-sm'
								: 'text-muted-foreground'}"
							onclick={() => (transport = option)}
						>
							{option === 'http' ? 'HTTP' : 'stdio'}
						</button>
					{/each}
				</div>
			</PanelHead>

			{#if transport === 'http'}
				<div class="divide-y">
					<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
						<div class="min-w-0">
							<div class="flex items-center gap-2 text-sm font-medium">
								Endpoint
								<Badge variant="secondary" class="text-[10px]">Same origin as reNgine</Badge>
							</div>
							<p class="mt-0.5 text-xs text-muted-foreground">
								Agents connect over the API you already run. Put a reverse proxy in front if one
								must reach it from another machine.
							</p>
						</div>
						<div class="flex items-center gap-1.5 rounded-md border bg-muted px-2.5 py-1">
							<span class="font-mono text-xs">{status.endpoint}</span>
							<CopyButton value={status.endpoint} class="size-5" />
						</div>
					</div>

					<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
						<div class="min-w-0">
							<div class="flex items-center gap-2 text-sm font-medium">
								Service token required
								<Badge variant="success" class="text-[10px]">Enforced</Badge>
							</div>
							<p class="mt-0.5 text-xs text-muted-foreground">
								Every request carries <span class="font-mono">Authorization: Bearer</span>. There is
								no anonymous mode.
							</p>
						</div>
						<Switch checked disabled />
					</div>

					<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
						<div class="min-w-0">
							<div class="text-sm font-medium">Rate limit per token</div>
							<p class="mt-0.5 text-xs text-muted-foreground">
								Calls one agent may make each minute, on top of the instance-wide throttle.
							</p>
						</div>
						<div class="flex items-center gap-2">
							<Input
								type="number"
								min="1"
								max="10000"
								class="h-8 w-24"
								disabled={!canAdmin}
								value={rate}
								oninput={(e) => (rateLimit = Number(e.currentTarget.value))}
								onblur={commitRate}
							/>
							<span class="text-xs text-muted-foreground">/ min</span>
						</div>
					</div>
				</div>
			{:else}
				<div class="space-y-3 px-5 py-4">
					<div
						class="flex gap-2.5 rounded-md border border-warning/30 bg-warning/8 px-3 py-2.5 text-xs"
					>
						<TriangleAlertIcon class="mt-0.5 size-4 shrink-0 text-warning" />
						<span>
							Your agent starts a stdio server itself, so Start and Stop do not apply to it. Revoke
							the token to cut that access.
						</span>
					</div>
					<div class="space-y-1.5">
						<div class="flex items-center justify-between gap-2">
							<span class="text-xs font-medium">Agent configuration</span>
							<Button variant="outline" size="sm" onclick={() => copy(stdioSnippet, 'stdio')}>
								{#if copied === 'stdio'}
									<CheckIcon class="size-4" />Copied
								{:else}
									<CopyIcon class="size-4" />Copy config
								{/if}
							</Button>
						</div>
						<pre
							class="overflow-x-auto rounded-md border bg-muted px-3 py-2.5 font-mono text-xs">{stdioSnippet}</pre>
						<p class="text-xs text-muted-foreground">
							Issue a token on the Access tab and paste it in place of the placeholder.
						</p>
					</div>
				</div>
			{/if}
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead
				title="What agents may do"
				description="The instance ceiling. No token can be granted more than this allows."
			/>
			<div class="divide-y">
				{#each status.capabilities as capability (capability.key)}
					{@const touches = TOUCHES_TARGETS.includes(capability.key)}
					<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
						<div class="min-w-0">
							<div class="flex flex-wrap items-center gap-2 text-sm font-medium">
								{capability.label}
								{#if capability.always}
									<Badge variant="secondary" class="text-[10px]">Always on</Badge>
								{:else if touches}
									<Badge variant="warning" class="gap-1 text-[10px]">
										<TriangleAlertIcon class="size-3" />
										Reaches targets
									</Badge>
								{/if}
							</div>
							<p class="mt-0.5 text-xs text-muted-foreground">{capability.help}</p>
						</div>
						<Switch
							checked={capability.always || (status.ceiling[capability.key] ?? false)}
							disabled={capability.always || !canAdmin || mcp.isSaving}
							onCheckedChange={(v) => setCeiling(capability.key, v)}
						/>
					</div>
				{/each}
			</div>
		</Card.Root>

		{#if running}
			<Card.Root class="gap-0 py-0">
				<PanelHead title="Connected agents" description="Live sessions and what each has called">
					<span>{sessions.length} connected</span>
				</PanelHead>
				{#if sessions.length}
					<div class="divide-y">
						{#each sessions as session (session.token_id + session.client)}
							<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
								<div class="min-w-0">
									<div class="flex flex-wrap items-center gap-2 text-sm font-medium">
										{session.client}
										{#each session.capabilities as capability (capability)}
											<Badge variant="info" class="text-[10px] capitalize">{capability}</Badge>
										{/each}
									</div>
									<p class="mt-0.5 truncate text-xs text-muted-foreground">
										<span class="font-mono">{session.token_name}</span>
										&middot; connected {relativeTime(session.first_seen)}
										&middot; {session.calls} call{session.calls === 1 ? '' : 's'}
										{#if session.last_tool}
											&middot; last <span class="font-mono">{session.last_tool}</span>
											{relativeTime(session.last_seen)}
										{/if}
									</p>
								</div>
								{#if canAdmin}
									<Button
										variant="outline"
										size="sm"
										onclick={() => mcp.disconnect(session.token_id)}
									>
										Disconnect
									</Button>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="px-5 py-8">
						<EmptyState
							compact
							title="No agent has connected yet"
							description="Issue a service token and paste it into your agent to see it here."
						>
							{#if canAdmin}
								<Button size="sm" onclick={onIssueToken}>New token</Button>
							{/if}
						</EmptyState>
					</div>
				{/if}
			</Card.Root>
		{/if}
	</div>

	<ConfirmDialog
		bind:open={confirmStop}
		title="Stop the MCP server?"
		description="{sessions.length} agent{sessions.length === 1
			? ' is'
			: 's are'} connected and will be disconnected immediately. A scan an agent started keeps running; the agent cannot read the result. Tokens stay valid, so the same agents reconnect when you start it again."
		confirmLabel="Stop server"
		destructive
		loading={mcp.isSaving}
		onOpenChange={(v) => (confirmStop = v)}
		onConfirm={stop}
	/>
{/if}
