<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Play from '@lucide/svelte/icons/play';
	import Search from '@lucide/svelte/icons/search';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Select from '$lib/components/ui/select';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { INVALID_TARGET_MESSAGE, TARGET_FORMATS } from '$lib/components/scans/launch/targets';
	import {
		decodeSelection,
		defaultSelection,
		encodeSelection,
		quickScanPlan,
		type QuickScanSelection
	} from '$lib/utilities/quick-scan';

	interface Props {
		heading: string;
		sub: string;
		onStarted?: () => void;
	}

	let { heading, sub, onStarted }: Props = $props();

	let value = $state('');
	let selection = $state<QuickScanSelection | null>(null);
	let starting = $state(false);
	let problem = $state<string | null>(null);

	let project = $derived(projectsStore.activeProject);
	let presets = $derived(engineCatalogStore.presets);
	let engines = $derived(scanEnginesStore.engines);
	let ready = $derived(engineCatalogStore.hasFetched || !!engineCatalogStore.error);
	let label = $derived.by(() => {
		const s = selection;
		if (!s) return 'Configuration';
		return s.kind === 'recipe'
			? (presets.find((p) => p.name === s.preset)?.title ?? 'Configuration')
			: (engines.find((e) => e.id === s.engineId)?.name ?? 'Configuration');
	});

	$effect(() => {
		const pid = project?.id;
		if (!pid) return;
		untrack(() => {
			if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
			if (scanEnginesStore.fetchedProjectId !== pid) scanEnginesStore.fetchEngines(pid);
		});
	});

	$effect(() => {
		const available = presets;
		untrack(() => {
			if (!selection && available.length) selection = defaultSelection(available);
		});
	});

	async function start() {
		const raw = value.trim();
		const pid = project?.id;
		if (!raw || !pid || !selection) return;
		starting = true;
		problem = null;
		try {
			const check = await targetsApi.validate({ target_value: raw });
			if (!check.valid || !check.target_type) {
				problem = `${INVALID_TARGET_MESSAGE}: ${raw}. ${TARGET_FORMATS}`;
				return;
			}
			const scans = await scansStore.launchScans(pid, {
				...quickScanPlan(selection, presets),
				target_values: [check.target_value || raw]
			});
			if (!scans?.length) {
				problem = scansStore.error ?? 'The scan could not be started.';
				return;
			}
			value = '';
			toast.success(`Scan queued against ${scans[0].execution_config.target_value}.`);
			dashboardStore.refresh();
			onStarted?.();
		} catch (e) {
			problem = e instanceof Error ? e.message : 'The scan could not be started.';
		} finally {
			starting = false;
		}
	}
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-col gap-1">
		<h2 class="text-xl font-semibold tracking-tight sm:text-2xl">{heading}</h2>
		<p class="text-sm text-muted-foreground">{sub}</p>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<div class="relative min-w-[16rem] flex-1">
			<Search
				class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value
				class="h-11 pl-9 font-mono text-sm"
				placeholder="Domain, IP address, CIDR range, URL or ASN"
				aria-label="Target"
				aria-invalid={problem ? 'true' : undefined}
				oninput={() => (problem = null)}
				onkeydown={(e) => {
					if (e.key === 'Enter') {
						e.preventDefault();
						void start();
					}
				}}
			/>
		</div>

		{#if ready}
			<Select.Root
				type="single"
				value={selection ? encodeSelection(selection) : ''}
				onValueChange={(v) => (selection = decodeSelection(v))}
			>
				<Select.Trigger
					class="w-full data-[size=default]:h-11 sm:w-auto sm:min-w-[11rem]"
					aria-label="Configuration"
				>
					{label}
				</Select.Trigger>
				<Select.Content>
					{#if engines.length}
						<Select.Group>
							<Select.Label>Scan engines</Select.Label>
							{#each engines as engine (engine.id)}
								<Select.Item value="engine:{engine.id}" label={engine.name}>
									{engine.name}
								</Select.Item>
							{/each}
						</Select.Group>
					{/if}
					<Select.Group>
						<Select.Label>Presets</Select.Label>
						{#each presets as preset (preset.name)}
							<Select.Item value="recipe:{preset.name}" label={preset.title}>
								{preset.title}
							</Select.Item>
						{/each}
					</Select.Group>
				</Select.Content>
			</Select.Root>
		{:else}
			<Skeleton class="h-11 w-full rounded-md sm:w-44" />
		{/if}

		<LoadingButton
			class="h-11 px-5"
			loading={starting}
			loadingLabel="Starting"
			disabled={!value.trim() || !selection}
			onclick={start}
		>
			<Play class="size-4" />
			Start scan
		</LoadingButton>
	</div>

	{#if problem}
		<p class="text-sm text-destructive">{problem}</p>
	{/if}
</div>
