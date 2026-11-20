<script lang="ts">
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import { BODY_ROW, HEAD_ROW } from '$lib/components/settings/columns';
	import { LEVEL_BADGE, LEVEL_HELP, LEVEL_LABELS } from '$lib/config/access-keys';
	import {
		EXPIRY_TONE_CLASS,
		formatDateTime,
		formatShortDate,
		relativeTime
	} from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { keyExpiry } from '$lib/utilities/access-keys';
	import type { AccessKey } from '$lib/types/access-key';
	import { ACCESS_KEY_COL } from './columns';

	interface Props {
		keys: AccessKey[];
		onRevoke: (key: AccessKey) => void;
	}

	let { keys, onRevoke }: Props = $props();
</script>

<div class="@container/access-keys w-full" role="table" aria-label="Access keys">
	<div class={HEAD_ROW} role="row">
		<div class={ACCESS_KEY_COL.name} role="columnheader">Name</div>
		<div class={ACCESS_KEY_COL.key} role="columnheader">Key</div>
		<div class={ACCESS_KEY_COL.access} role="columnheader">Access</div>
		<div class={ACCESS_KEY_COL.used} role="columnheader">Last used</div>
		<div class={ACCESS_KEY_COL.expires} role="columnheader">Expires</div>
		<div class={ACCESS_KEY_COL.created} role="columnheader">Created</div>
		<div class={ACCESS_KEY_COL.actions} role="columnheader">
			<span class="sr-only">Actions</span>
		</div>
	</div>
	{#each keys as key (key.id)}
		{@const expiry = keyExpiry(key)}
		<div class="{BODY_ROW} {expiry.tone === 'expired' ? 'text-muted-foreground' : ''}" role="row">
			<div class="{ACCESS_KEY_COL.name} flex flex-col" role="cell">
				<span class="text-sm leading-5 font-medium wrap-anywhere">{key.name}</span>
				<span class="font-mono text-2xs text-muted-foreground @xl/access-keys:hidden">
					{key.prefix}…
				</span>
			</div>
			<div class="{ACCESS_KEY_COL.key} font-mono text-xs leading-5" role="cell">{key.prefix}…</div>
			<div class="{ACCESS_KEY_COL.access} text-sm leading-5" role="cell">
				<Hint text={LEVEL_HELP[key.access]}>
					{#snippet child(props)}
						<Badge {...props} variant={LEVEL_BADGE[key.access]}>{LEVEL_LABELS[key.access]}</Badge>
					{/snippet}
				</Hint>
			</div>
			<div class="{ACCESS_KEY_COL.used} text-sm leading-5" role="cell">
				{#if key.last_used_at}
					<Hint text={formatDateTime(key.last_used_at)}>
						{#snippet child(props)}
							<span {...props}>{relativeTime(key.last_used_at)}</span>
						{/snippet}
					</Hint>
					<div class="font-mono text-2xs text-muted-foreground tabular-nums wrap-anywhere">
						{key.last_used_ip ?? ''}{key.last_used_ip ? ' · ' : ''}{plural(key.use_count, 'call')}
					</div>
				{:else}
					<span class="text-muted-foreground">Never</span>
				{/if}
			</div>
			<div
				class="{ACCESS_KEY_COL.expires} text-sm leading-5 {EXPIRY_TONE_CLASS[expiry.tone]}"
				role="cell"
			>
				{#if key.expires_at}
					<Hint text={formatDateTime(key.expires_at)}>
						{#snippet child(props)}
							<span {...props}>{expiry.label}</span>
						{/snippet}
					</Hint>
				{:else}
					{expiry.label}
				{/if}
			</div>
			<div
				class="{ACCESS_KEY_COL.created} text-xs leading-5 text-muted-foreground tabular-nums"
				role="cell"
			>
				{formatShortDate(key.created_at)}
			</div>
			<div class={ACCESS_KEY_COL.actions} role="cell">
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7"
								aria-label="{key.name} actions"
							>
								<EllipsisIcon class="size-4" />
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end">
						<DropdownMenu.Item variant="destructive" onSelect={() => onRevoke(key)}>
							Revoke
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		</div>
	{/each}
</div>
