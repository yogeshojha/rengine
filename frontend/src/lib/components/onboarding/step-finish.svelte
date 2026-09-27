<script lang="ts">
	import { onboardingApi } from '$lib/api/onboarding';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { toast } from 'svelte-sonner';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	const LABELS = [
		'Bug bounty',
		'Client engagement',
		'Personal research',
		'Internal assessment',
		'Red team exercise',
		'Other'
	];

	let projectName = $state('');
	let projectDescription = $state('');
	let projectLabel = $state('');
	let busy = $state(false);

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
			await onboardingApi.createFirstProject({
				name: projectName.trim(),
				description: projectDescription.trim() || null,
				label: projectLabel || null
			});
			next();
		} catch (e) {
			toast.error(
				e instanceof Error ? `Project not created. ${e.message}` : 'Project not created.'
			);
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<section class="space-y-5">
		<div class="space-y-1.5">
			<Label for="project-name" class="text-xs">
				Name <span class="text-destructive">*</span>
			</Label>
			<Input
				id="project-name"
				bind:value={projectName}
				placeholder="Acme Bug Bounty"
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
</div>
