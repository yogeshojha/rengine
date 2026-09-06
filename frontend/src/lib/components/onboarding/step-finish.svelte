<script lang="ts">
	import { instanceSettingsApi } from '$lib/api/instanceSettings';
	import { onboardingApi } from '$lib/api/onboarding';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { toast } from 'svelte-sonner';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import HardDriveIcon from '@lucide/svelte/icons/hard-drive';
	import CheckIcon from '@lucide/svelte/icons/check';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	const SCAN_RETENTION = [
		{ value: '30', label: '30 days' },
		{ value: '60', label: '60 days' },
		{ value: '90', label: '90 days' },
		{ value: '180', label: '180 days' },
		{ value: '365', label: '365 days' }
	];

	const SHOT_RETENTION = [
		{ value: '7', label: '7 days' },
		{ value: '14', label: '14 days' },
		{ value: '30', label: '30 days' },
		{ value: '90', label: '90 days' }
	];

	const LABELS = [
		'Bug bounty',
		'Client engagement',
		'Personal research',
		'Internal assessment',
		'Red team exercise',
		'Other'
	];

	let scanRetention = $state('90');
	let shotRetention = $state('30');
	let projectName = $state('');
	let projectDescription = $state('');
	let projectLabel = $state('');
	let busy = $state(false);
	let phase = $state<'idle' | 'retention' | 'project'>('idle');
	let retentionSaved = $state(false);

	let nameInvalid = $derived(projectName.trim() === '');

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLabel: 'Finish setup',
			nextLoading: busy,
			nextDisabled: nameInvalid
		});
	});

	async function handleNext() {
		if (nameInvalid) {
			toast.error('Project name is required');
			return;
		}

		busy = true;
		try {
			if (!retentionSaved) {
				phase = 'retention';
				try {
					await instanceSettingsApi.update({
						scan_history_retention_days: Number(scanRetention),
						screenshot_retention_days: Number(shotRetention)
					});
				} catch (e) {
					toast.error(
						e instanceof Error
							? `Retention settings could not be saved. ${e.message}`
							: 'Retention settings could not be saved.'
					);
					return;
				}
				retentionSaved = true;
			}

			phase = 'project';
			try {
				await onboardingApi.createFirstProject({
					name: projectName.trim(),
					description: projectDescription.trim() || null,
					label: projectLabel || null
				});
			} catch (e) {
				toast.error(
					e instanceof Error
						? `Project could not be created. ${e.message}`
						: 'Project could not be created. Retention settings are saved.'
				);
				return;
			}

			next();
		} finally {
			busy = false;
			phase = 'idle';
		}
	}
</script>

<div class="space-y-6">
	<section class="space-y-5">
		<div class="flex items-center gap-2">
			<HardDriveIcon class="size-4 text-muted-foreground" />
			<h3 class="text-sm font-medium">Data retention</h3>
		</div>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="space-y-1.5">
				<Label class="text-xs">Scan history</Label>
				<Select.Root type="single" bind:value={scanRetention}>
					<Select.Trigger class="h-9 w-full text-sm">
						{SCAN_RETENTION.find((o) => o.value === scanRetention)?.label ?? 'Select'}
					</Select.Trigger>
					<Select.Content>
						{#each SCAN_RETENTION as opt (opt.value)}
							<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
				<p class="text-xs text-muted-foreground">Retention period for completed scans.</p>
			</div>
			<div class="space-y-1.5">
				<Label class="text-xs">Screenshots</Label>
				<Select.Root type="single" bind:value={shotRetention}>
					<Select.Trigger class="h-9 w-full text-sm">
						{SHOT_RETENTION.find((o) => o.value === shotRetention)?.label ?? 'Select'}
					</Select.Trigger>
					<Select.Content>
						{#each SHOT_RETENTION as opt (opt.value)}
							<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
				<p class="text-xs text-muted-foreground">Captured screenshots are pruned after this.</p>
			</div>
		</div>
	</section>

	<section class="space-y-5">
		<div class="space-y-1.5">
			<Label for="project-name" class="text-xs">
				Name <span class="text-destructive">*</span>
			</Label>
			<Input
				id="project-name"
				bind:value={projectName}
				placeholder="e.g. Acme Bug Bounty"
				disabled={busy}
				aria-invalid={nameInvalid}
				class="h-9 text-sm"
			/>
		</div>
		<div class="space-y-1.5">
			<Label for="project-description" class="text-xs">Description</Label>
			<Textarea
				id="project-description"
				bind:value={projectDescription}
				placeholder="Scope or goal of this project"
				disabled={busy}
				rows={3}
				class="text-sm"
			/>
		</div>
		<div class="space-y-1.5">
			<Label class="text-xs">Label</Label>
			<Select.Root type="single" bind:value={projectLabel}>
				<Select.Trigger class="h-9 w-full text-sm">
					{projectLabel || 'Select a label'}
				</Select.Trigger>
				<Select.Content>
					{#each LABELS as label (label)}
						<Select.Item value={label} {label}>{label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
	</section>

	{#if busy || retentionSaved}
		<section class="space-y-2 rounded-md border bg-muted/30 p-3" aria-live="polite">
			<div class="flex items-center gap-2 text-sm">
				{#if retentionSaved}
					<CheckIcon class="size-4 text-foreground" />
				{:else if phase === 'retention'}
					<Spinner class="text-muted-foreground" />
				{:else}
					<span class="size-4"></span>
				{/if}
				<span class={retentionSaved ? 'text-muted-foreground' : ''}>Saving retention settings</span>
			</div>
			<div class="flex items-center gap-2 text-sm">
				{#if phase === 'project'}
					<Spinner class="text-muted-foreground" />
				{:else}
					<span class="size-4"></span>
				{/if}
				<span class={phase === 'project' ? '' : 'text-muted-foreground'}>Creating project</span>
			</div>
		</section>
	{/if}
</div>
