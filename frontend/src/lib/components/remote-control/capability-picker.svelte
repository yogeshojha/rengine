<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import type { SvelteSet } from 'svelte/reactivity';
	import type { ChannelStatus } from '$lib/types/remote-control';

	interface Props {
		status: ChannelStatus;
		granted: SvelteSet<string>;
	}

	let { status, granted }: Props = $props();

	const capabilities = $derived(status.capabilities);
	const ceiling = $derived(status.ceiling);
	const alwaysGranted = $derived(capabilities.filter((c) => c.always).map((c) => c.key));

	function toggle(key: string, value: boolean) {
		if (value) granted.add(key);
		else granted.delete(key);
		for (const always of alwaysGranted) granted.add(always);
	}
</script>

<div class="flex flex-col gap-2">
	<span class="text-sm font-medium">Capabilities</span>
	<div class="flex flex-col gap-1.5">
		{#each capabilities as capability (capability.key)}
			{@const locked = capability.always}
			{@const blocked = !locked && !ceiling[capability.key]}
			{@const touches = capability.touches_targets}
			<label
				class="flex items-start gap-2.5 rounded-md border px-3 py-2.5 {touches &&
				granted.has(capability.key)
					? 'border-warning/40 bg-warning/6'
					: ''} {blocked ? 'opacity-50' : ''}"
			>
				<Checkbox
					class="mt-0.5"
					checked={locked || (!blocked && granted.has(capability.key))}
					disabled={locked || blocked}
					onCheckedChange={(v) => toggle(capability.key, Boolean(v))}
				/>
				<span class="min-w-0">
					<span class="flex flex-wrap items-center gap-2 text-sm font-medium">
						{capability.label}
						{#if locked}
							<Badge variant="secondary" class="text-2xs">Required</Badge>
						{:else}
							<Badge variant="outline" class="text-2xs">Authenticator</Badge>
							{#if touches}
								<Badge variant="warning" class="gap-1 text-2xs">
									<TriangleAlertIcon class="size-3" />
									Reaches targets
								</Badge>
							{/if}
						{/if}
						{#if blocked}
							<Badge variant="outline" class="text-2xs">Off in ceiling</Badge>
						{/if}
					</span>
					<span class="mt-0.5 block text-xs text-muted-foreground">{capability.help}</span>
				</span>
			</label>
		{/each}
	</div>
</div>
