<script lang="ts">
	import OverflowPopover from './table/overflow-popover.svelte';
	import ServiceIcon from './services/service-icon.svelte';
	import { isSensitivePort } from '$lib/utilities/scan-correlation';
	import { serviceLabel, type ServiceRead } from '$lib/utilities/services';

	interface Props {
		ports: number[];
		shown: number;
		load: () => Promise<ServiceRead[]>;
		onSelect: (port: number) => void;
	}

	let { ports, shown, load, onSelect }: Props = $props();

	let rows = $state<ServiceRead[] | null>(null);
	let requested = false;

	function svcFor(port: number): ServiceRead | undefined {
		const all = (rows ?? []).filter((r) => r.port === port);
		return all.find((r) => r.product) ?? all[0];
	}

	function fetchOnce(open: boolean) {
		if (!open || requested) return;
		requested = true;
		load()
			.then((list) => (rows = list))
			.catch(() => (rows = []));
	}
</script>

<OverflowPopover
	items={ports.map(String)}
	{shown}
	label="open ports"
	contentClass="w-72"
	onOpenChange={fetchOnce}
	onSelect={(v) => onSelect(Number(v))}
>
	{#snippet item(value)}
		{@const port = Number(value)}
		{@const svc = svcFor(port)}
		<span class="flex min-w-0 items-center gap-1.5">
			<span class="flex w-4 shrink-0 justify-center">
				<ServiceIcon
					service={svc?.service_name ?? null}
					serviceClass={svc?.service_class ?? ''}
					product={svc?.product}
					class="size-3.5"
				/>
			</span>
			<span class="shrink-0 font-mono {isSensitivePort(port) ? 'text-warning' : ''}">{port}</span>
			{#if svc}
				<span class="truncate text-muted-foreground">
					{svc.product ? serviceLabel(svc) : (svc.service_name ?? '')}
				</span>
			{/if}
		</span>
	{/snippet}
</OverflowPopover>
