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
	import CodeBlock from '$lib/components/code-block.svelte';
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
	import {
		MCP_STATE_DOT,
		MCP_STATE_LABEL,
		TOUCHES_TARGETS,
		type McpCapability
	} from '$lib/types/mcp';

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
	const serverState = $derived(running ? 'running' : ('stopped' as const));
	const grantable = $derived(
		(status?.capabilities ?? []).filter((c) => c.always || status?.ceiling[c.key]).length
	);

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
				<div class="flex items-center gap-2.5">
					<span
						class="size-2 shrink-0 rounded-full border {MCP_STATE_DOT[serverState]}"
						aria-hidden="true"
					></span>
					<span class="text-base leading-6 font-semibold">{MCP_STATE_LABEL[serverState]}</span>
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

			<div class="grid grid-cols-2 border-t sm:grid-cols-3 lg:grid-cols-6">
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
				{@render cell(
					'Uptime',
					running ? relativeTime(status.started_at).replace(' ago', '') : '—'
				)}
				{@render cell('Sessions', running ? String(sessions.length) : '—')}
				{@render cell('Calls today', String(status.calls_today))}
				{@render cell('Rate limit', `${status.rate_limit_per_minute}/min`)}
			</div>
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead title="Transport">
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
							<div class="text-sm font-medium">Endpoint</div>
							<p class="mt-0.5 text-xs text-muted-foreground">
								Served by the API. A reverse proxy owns TLS and any external access.
							</p>
						</div>
						<div class="flex items-center gap-1.5 rounded-md border bg-muted px-2.5 py-1">
							<span class="font-mono text-xs">{status.endpoint}</span>
							<CopyButton value={status.endpoint} class="size-5" />
						</div>
					</div>

					<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
						<div class="min-w-0">
							<div class="text-sm font-medium">Service token</div>
							<p class="mt-0.5 text-xs text-muted-foreground">
								Required on every request. There is no anonymous access.
							</p>
						</div>
						<Badge variant="success">Enforced</Badge>
					</div>

					<div class="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
						<div class="min-w-0">
							<div class="text-sm font-medium">Rate limit</div>
							<p class="mt-0.5 text-xs text-muted-foreground">
								Calls one token may make each minute.
							</p>
						</div>
						<div class="flex items-center gap-2">
							<Input
								type="number"
								min="1"
								max="10000"
								class="h-8 w-24 text-right tabular-nums"
								disabled={!canAdmin}
								value={rate}
								oninput={(e) => (rateLimit = Number(e.currentTarget.value))}
								onblur={commitRate}
							/>
							<span class="text-xs text-muted-foreground">/min</span>
						</div>
					</div>
				</div>
			{:else}
				<div class="space-y-3 px-5 py-4">
					<p class="text-xs text-muted-foreground">
						The agent starts this process, so Start and Stop do not apply. Revoke the token to cut
						access.
					</p>
					<span class="text-xs font-medium">Agent configuration</span>
					<CodeBlock code={stdioSnippet} lang="json" label="claude_desktop_config.json" />
				</div>
			{/if}
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<PanelHead title="Capabilities">
				<span class="tabular-nums">{grantable} of {status.capabilities.length} grantable</span>
			</PanelHead>
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
				<PanelHead title="Connected agents">
					{#if sessions.length}
						<span class="tabular-nums">
							{sessions.reduce((n, s) => n + s.calls, 0)} calls this session
						</span>
					{:else}
						<span>None connected</span>
					{/if}
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
										&middot; {relativeTime(session.first_seen)}
										&middot; <span class="tabular-nums">{session.calls}</span> calls
										{#if session.last_tool}
											&middot; <span class="font-mono">{session.last_tool}</span>
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
							title="No agent has connected"
							description="Issue a service token to connect an agent."
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
			: 's are'} connected and will be disconnected immediately. A scan an agent started keeps running — the agent just cannot read the result. Tokens stay valid, so the same agents reconnect when you start it again."
		confirmLabel="Stop server"
		destructive
		loading={mcp.isSaving}
		onOpenChange={(v) => (confirmStop = v)}
		onConfirm={stop}
	/>
{/if}
