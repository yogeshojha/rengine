<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { SUBMISSION_STATE_LABELS } from '$lib/config/bounty-programs';
	import { SubmissionState } from '$lib/types/bounty-program';

	let { submission }: { submission: string } = $props();
</script>

{#if submission !== SubmissionState.Open && submission !== SubmissionState.Unknown}
	<Badge variant="warning">
		Submissions {SUBMISSION_STATE_LABELS[submission as SubmissionState]?.toLowerCase() ??
			submission}
	</Badge>
{/if}
