<script lang="ts">
	import Sparkle from '@lucide/svelte/icons/sparkle';
	import X from '@lucide/svelte/icons/x';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { interestApi } from '$lib/api/interest';
	import { RULE_MODE, type RuleSuggestion } from '$lib/types/interest';

	interface Props {
		suggestion: RuleSuggestion;
		projectId: string;
		onDone: (suggestion: RuleSuggestion) => void;
	}

	let { suggestion, projectId, onDone }: Props = $props();

	let adding = $state(false);

	async function add(): Promise<void> {
		adding = true;
		try {
			await interestApi.createRule(projectId, {
				name: suggestion.name,
				description: suggestion.reason,
				mode: RULE_MODE.QUERY,
				query: suggestion.query,
				kind: suggestion.kind
			});
			toast.success(`${suggestion.name} added. It runs on every scan.`);
			onDone(suggestion);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not add the rule');
		} finally {
			adding = false;
		}
	}
</script>

<div
	class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-info/[0.05] px-4 py-3"
>
	<div class="flex min-w-0 flex-col gap-1">
		<span class="flex flex-wrap items-center gap-2 text-[12.5px] font-medium">
			<span
				class="inline-flex items-center gap-1 rounded border border-info/40 bg-info/10 px-1.5 py-px text-[10px] text-info"
			>
				<Sparkle class="size-2.5" />
				Suggested rule
			</span>
			{suggestion.name}
			<span class="text-[11px] font-normal text-muted-foreground">{suggestion.kind_label}</span>
		</span>
		<span class="font-mono text-[11px] break-all text-muted-foreground">{suggestion.query}</span>
		<span class="text-[11px] text-muted-foreground">
			Matches {suggestion.matches.toLocaleString()}
			{suggestion.matches === 1 ? 'asset' : 'assets'} on this scan. Once added it runs with no model.
		</span>
	</div>
	<div class="flex shrink-0 items-center gap-2">
		<LoadingButton size="sm" loading={adding} loadingLabel="Adding" onclick={add}
			>Add rule</LoadingButton
		>
		<Button variant="ghost" size="sm" onclick={() => onDone(suggestion)}>
			<X class="size-3.5" />
			Not useful
		</Button>
	</div>
</div>
