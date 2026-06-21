<script lang="ts">
	import { Label } from '$lib/components/ui/label/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import { instanceSettingsApi } from '$lib/api/instanceSettings';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { InstanceMode, coerceInstanceMode } from '$lib/config/capabilities';
	import { toast } from 'svelte-sonner';
	import type { StepProps } from '$lib/types/onboarding';
	import type { Component } from 'svelte';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import TargetIcon from '@lucide/svelte/icons/target';
	import Building2Icon from '@lucide/svelte/icons/building-2';
	import InfoIcon from '@lucide/svelte/icons/info';
	import StepHeader from './step-header.svelte';

	let { data, next, setFooter }: StepProps = $props();

	const MODES: { value: InstanceMode; title: string; icon: Component; desc: string; unlocks: string }[] = [
		{
			value: InstanceMode.BugBounty,
			title: 'Bug Bounty',
			icon: TargetIcon,
			desc: 'Hunting on public and private programs.',
			unlocks: 'Enables HackerOne integration, program import, and breadth-tuned recon presets.'
		},
		{
			value: InstanceMode.Corporate,
			title: 'Corporate',
			icon: Building2Icon,
			desc: 'Securing your own organization.',
			unlocks: 'Asset-centric workflows and internal scope controls. Bug-bounty features (HackerOne, program import) stay hidden.'
		}
	];

	let selected = $state<string>(coerceInstanceMode(data.mode));
	let busy = $state(false);

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy });
	});

	async function handleNext() {
		busy = true;
		try {
			await instanceSettingsApi.update({ mode: selected });
			data.mode = selected;
			capabilitiesStore.setMode(selected);
			toast.success(`Mode set to ${MODES.find((m) => m.value === selected)?.title ?? selected}`);
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save mode');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<StepHeader
		icon={CompassIcon}
		title="How will you use reNgine?"
		description="Pick one — it tailors which features appear. Corporate hides bug-bounty tooling entirely. You can switch anytime in Settings."
	/>

	<RadioGroup.Root value={selected} onValueChange={(v) => (selected = v)} class="grid gap-3">
		{#each MODES as mode (mode.value)}
			{@const Icon = mode.icon}
			<Label
				class="flex cursor-pointer items-start gap-4 rounded-lg border border-input bg-transparent p-4 transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
				data-active={selected === mode.value}
			>
				<div
					class="flex size-9 items-center justify-center rounded-lg border bg-muted data-[active=true]:bg-background"
					data-active={selected === mode.value}
				>
					<Icon class="size-[18px] text-foreground" />
				</div>
				<div class="min-w-0 flex-1 space-y-1">
					<div class="flex items-center justify-between gap-2">
						<span class="text-sm font-medium">{mode.title}</span>
						<RadioGroup.Item value={mode.value} />
					</div>
					<p class="text-sm text-muted-foreground">{mode.desc}</p>
					<p class="text-xs text-muted-foreground">{mode.unlocks}</p>
				</div>
			</Label>
		{/each}
	</RadioGroup.Root>

	<p class="flex items-start gap-2 text-xs text-muted-foreground">
		<InfoIcon class="mt-px size-4 shrink-0" />
		<span>reNgine runs in a single mode — it's not both. Corporate mode keeps the workspace
			focused by hiding bug-bounty-only features like the HackerOne integration.</span>
	</p>
</div>
