<script lang="ts">
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import XIcon from '@lucide/svelte/icons/x';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import type { PlatformCount } from '$lib/types/bounty-program';

	interface Props {
		platforms: PlatformCount[];
		dismissible?: boolean;
	}

	let { platforms, dismissible = false }: Props = $props();

	function stored(): string[] {
		try {
			const raw = localStorage.getItem(STORAGE_KEYS.bountyConnectDismissed);
			return raw ? (JSON.parse(raw) as string[]) : [];
		} catch {
			return [];
		}
	}

	let dismissed = $state<string[]>(stored());

	const pending = $derived(
		platforms.filter(
			(p) => p.api_provider && !p.configured && !(dismissible && dismissed.includes(p.platform))
		)
	);
	const names = $derived(
		pending.length > 1
			? `${pending
					.slice(0, -1)
					.map((p) => p.label)
					.join(', ')} and ${pending[pending.length - 1].label}`
			: (pending[0]?.label ?? '')
	);

	function dismiss() {
		dismissed = [...new Set([...dismissed, ...pending.map((p) => p.platform)])];
		try {
			localStorage.setItem(STORAGE_KEYS.bountyConnectDismissed, JSON.stringify(dismissed));
		} catch {
			/* a viewer with site data blocked keeps the alert */
		}
	}
</script>

{#if pending.length > 0}
	<Alert.Root class="flex items-center gap-3">
		<KeyRoundIcon class="size-4 shrink-0 translate-y-0 text-muted-foreground" />
		<div class="flex min-w-0 flex-1 flex-col gap-0.5">
			<Alert.Title class="line-clamp-none">{names} not connected</Alert.Title>
			<Alert.Description>
				Public programs come from the feed. Credentials add private programs.
			</Alert.Description>
		</div>
		<div class="flex shrink-0 items-center gap-1">
			<Button href={ROUTES.settings('api-keys')} size="sm" variant="outline">Add credentials</Button
			>
			{#if dismissible}
				<Button variant="ghost" size="icon" class="size-8" onclick={dismiss} aria-label="Dismiss">
					<XIcon class="size-4" />
				</Button>
			{/if}
		</div>
	</Alert.Root>
{/if}
