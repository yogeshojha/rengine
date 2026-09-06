<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import MoreVerticalIcon from '@lucide/svelte/icons/more-vertical';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import PanelHead from '$lib/components/panel-head.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { relativeTime, formatShortDate } from '$lib/utilities/dates';
	import { TOUCHES_TARGETS, tokenState, type McpCapability, type McpToken } from '$lib/types/mcp';

	interface Props {
		canAdmin: boolean;
		onIssueToken: () => void;
	}

	let { canAdmin, onIssueToken }: Props = $props();

	let pending = $state<{ token: McpToken; action: 'revoke' | 'delete' } | null>(null);

	const tokens = $derived(mcp.tokens);

	async function confirm() {
		if (!pending) return;
		const { token, action } = pending;
		pending = null;
		if (action === 'revoke') await mcp.revokeToken(token.id);
		else await mcp.deleteToken(token.id);
	}
</script>

<Card.Root class="gap-0 py-0">
	<PanelHead
		title="Service tokens"
		description="A token is bound to one project and one capability set. Revoking takes effect on the next call."
	>
		{#if canAdmin}
			<Button size="sm" onclick={onIssueToken}>
				<PlusIcon class="size-4" />
				New token
			</Button>
		{/if}
	</PanelHead>

	{#if tokens.length === 0}
		<div class="px-5 py-8">
			<EmptyState
				compact
				icon={KeyRoundIcon}
				title="No tokens yet"
				description="An agent needs a token to reach this instance. Nothing connects without one."
			>
				{#if canAdmin}
					<Button size="sm" onclick={onIssueToken}>New token</Button>
				{/if}
			</EmptyState>
		</div>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full min-w-[46rem] text-sm">
				<thead>
					<tr class="border-b bg-muted/40">
						{#each ['Name', 'Project', 'May', 'Last used', 'Expires', ''] as heading (heading)}
							<th
								class="px-5 py-2.5 text-left text-[10px] font-semibold tracking-wider text-muted-foreground uppercase whitespace-nowrap"
							>
								{heading}
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each tokens as token (token.id)}
						{@const state = tokenState(token)}
						<tr class="border-b last:border-b-0 {state === 'active' ? '' : 'opacity-55'}">
							<td class="px-5 py-3">
								<div class="flex items-center gap-2 font-medium">
									{token.name}
									{#if state === 'revoked'}
										<Badge variant="outline" class="text-[10px]">Revoked</Badge>
									{:else if state === 'expired'}
										<Badge variant="outline" class="text-[10px]">Expired</Badge>
									{/if}
								</div>
								<div class="font-mono text-xs text-muted-foreground">{token.token_prefix}…</div>
							</td>
							<td class="px-5 py-3 text-muted-foreground">
								{token.project_name ?? 'Every project'}
							</td>
							<td class="px-5 py-3">
								<div class="flex flex-wrap gap-1">
									{#each token.capabilities as capability (capability)}
										<Badge
											variant={TOUCHES_TARGETS.includes(capability as McpCapability)
												? 'warning'
												: 'info'}
											class="text-[10px] capitalize"
										>
											{capability}
										</Badge>
									{/each}
								</div>
							</td>
							<td class="px-5 py-3 whitespace-nowrap text-muted-foreground">
								{#if token.last_used_at}
									{relativeTime(token.last_used_at)}
									<span class="block text-xs">{token.calls} calls</span>
								{:else}
									Never used
								{/if}
							</td>
							<td class="px-5 py-3 whitespace-nowrap text-muted-foreground">
								{token.expires_at ? formatShortDate(token.expires_at) : 'Never'}
							</td>
							<td class="px-5 py-3 text-right">
								{#if canAdmin}
									<DropdownMenu.Root>
										<DropdownMenu.Trigger>
											{#snippet child({ props })}
												<Button {...props} variant="ghost" size="icon" class="size-7">
													<MoreVerticalIcon class="size-4" />
													<span class="sr-only">Token actions</span>
												</Button>
											{/snippet}
										</DropdownMenu.Trigger>
										<DropdownMenu.Content align="end">
											{#if state === 'active'}
												<DropdownMenu.Item onSelect={() => (pending = { token, action: 'revoke' })}>
													Revoke
												</DropdownMenu.Item>
											{/if}
											<DropdownMenu.Item
												variant="destructive"
												onSelect={() => (pending = { token, action: 'delete' })}
											>
												Delete
											</DropdownMenu.Item>
										</DropdownMenu.Content>
									</DropdownMenu.Root>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</Card.Root>

<ConfirmDialog
	open={pending !== null}
	title={pending?.action === 'revoke' ? 'Revoke this token?' : 'Delete this token?'}
	description={pending
		? `${pending.token.name} stops working on its next call. Any agent using it loses access immediately; scans it already started keep running.`
		: ''}
	confirmLabel={pending?.action === 'revoke' ? 'Revoke' : 'Delete'}
	destructive
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
