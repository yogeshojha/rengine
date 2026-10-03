<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';

	interface Props {
		onBack: () => void;
		onNext: () => void;
		onSkip?: () => void;
		nextLabel?: string;
		nextLoading?: boolean;
		nextLoadingLabel?: string;
		nextDisabled?: boolean;
		canSkip?: boolean;
		isFirst?: boolean;
	}

	let {
		onBack,
		onNext,
		onSkip,
		nextLabel = 'Continue',
		nextLoading = false,
		nextLoadingLabel = 'Saving',
		nextDisabled = false,
		canSkip = false,
		isFirst = false
	}: Props = $props();
</script>

<div class="flex items-center gap-2">
	{#if !isFirst}
		<Button variant="ghost" onclick={onBack} disabled={nextLoading}>
			<ChevronLeftIcon class="size-4" />
			Back
		</Button>
	{/if}

	<div class="flex-1"></div>

	{#if canSkip && onSkip}
		<Button variant="ghost" class="text-muted-foreground" onclick={onSkip} disabled={nextLoading}>
			Skip
		</Button>
	{/if}

	<LoadingButton
		onclick={onNext}
		loading={nextLoading}
		loadingLabel={nextLoadingLabel}
		disabled={nextDisabled}
	>
		{nextLabel}
	</LoadingButton>
</div>
