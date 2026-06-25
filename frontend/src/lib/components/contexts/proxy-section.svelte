<script lang="ts">
	import { onMount } from 'svelte';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Select from '$lib/components/ui/select';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import { Spinner } from '$lib/components/ui/spinner';
	import { proxiesStore } from '$lib/stores/proxies.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import type { ScanContextRead, ScanContextCreate } from '$lib/types/scan-context';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();

	onMount(() => {
		if (!proxiesStore.hasFetched) proxiesStore.fetch();
	});

	let activeProxies = $derived(proxiesStore.proxies.filter((p) => p.is_active));
	let selectedId = $derived(context.proxy_id ?? SELECT_NONE);
	let selected = $derived(activeProxies.find((p) => p.id === context.proxy_id) ?? null);

	function setProxy(v: string | undefined) {
		onChange({ proxy_id: v && v !== SELECT_NONE ? v : null } as Partial<CtxLike>);
	}

	let triggerLabel = $derived.by(() => {
		if (!context.proxy_id) return 'None';
		return selected ? selected.name : 'Unknown proxy';
	});
</script>

<div class="space-y-4">
	<div class="space-y-1.5">
		<Label class="text-xs">Proxy</Label>
		<Select.Root type="single" value={selectedId} onValueChange={setProxy}>
			<Select.Trigger class="h-9 w-full max-w-sm text-sm">
				{triggerLabel}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={SELECT_NONE} label="None">None</Select.Item>
				{#each activeProxies as proxy (proxy.id)}
					<Select.Item value={proxy.id} label={proxy.name}>
						<span class="flex items-center gap-2">
							{proxy.name}
							{#if proxy.is_default}
								<Badge variant="secondary" class="h-4 px-1 text-[10px]">Default</Badge>
							{/if}
						</span>
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<p class="text-xs text-muted-foreground">
			All scan HTTP traffic for this context is routed through the selected proxy.
		</p>
	</div>

	{#if proxiesStore.isLoading && !proxiesStore.hasFetched}
		<div class="flex items-center gap-2 text-xs text-muted-foreground">
			<Spinner class="h-3.5 w-3.5" />
			Loading proxies…
		</div>
	{:else if selected}
		<div class="rounded-md border border-dashed border-border bg-muted/40 px-3 py-2">
			<div class="flex items-center gap-2">
				<p class="text-[10px] uppercase tracking-wide text-muted-foreground">Endpoint</p>
				{#if selected.is_default}
					<Badge variant="secondary" class="h-4 px-1 text-[10px]">Default</Badge>
				{/if}
			</div>
			<code class="text-xs text-foreground">
				{selected.endpoints[0]?.url_masked ?? '—'}
			</code>
			{#if selected.endpoint_count > 1}
				<p class="mt-1 text-xs text-muted-foreground">
					+{selected.endpoint_count - 1} more endpoint{selected.endpoint_count - 1 === 1 ? '' : 's'}
				</p>
			{/if}
		</div>
	{:else if context.proxy_id}
		<p class="text-xs text-destructive">
			The selected proxy is no longer active or has been removed.
		</p>
	{/if}

	<a
		href={ROUTES.settings()}
		class="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
	>
		Manage proxies in Settings
		<ExternalLink class="h-3 w-3" />
	</a>
</div>
