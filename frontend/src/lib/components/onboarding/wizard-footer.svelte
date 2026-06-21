<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';

	interface Props {
		onBack: () => void;
		onNext: () => void;
		onSkip?: () => void;
		nextLabel?: string;
		nextLoading?: boolean;
		nextDisabled?: boolean;
		canSkip?: boolean;
		isFirst?: boolean;
		backLabel?: string;
	}

	let {
		onBack,
		onNext,
		onSkip,
		nextLabel = 'Continue',
		nextLoading = false,
		nextDisabled = false,
		canSkip = false,
		isFirst = false,
		backLabel = 'Back'
	}: Props = $props();
</script>

<div class="flex items-center gap-2">
	{#if !isFirst}
		<Button variant="ghost" onclick={onBack}>
			<ChevronLeftIcon class="mr-1 size-4" />
			{backLabel}
		</Button>
	{/if}

	<div class="flex-1"></div>

	{#if canSkip && onSkip}
		<Button variant="ghost" class="text-muted-foreground" onclick={onSkip} disabled={nextLoading}>
			Skip for now
		</Button>
	{/if}

	<Button onclick={onNext} disabled={nextDisabled || nextLoading}>
		{#if nextLoading}
			<Spinner class="mr-2" />
		{/if}
		{nextLabel}
	</Button>
</div>
