<script lang="ts">
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { evidenceToken } from '$lib/config/evidence';
	import { exactToken } from '$lib/utilities/scan-insights';
	import type { CveLadderStep } from '$lib/types/cve';

	interface Props {
		cve: string;
		ladder: CveLadderStep[];
	}

	let { cve, ladder }: Props = $props();

	const software = SURFACE[SurfaceDimension.SOFTWARE];
	const findings = SURFACE[SurfaceDimension.VULNERABILITIES];

	function query(step: CveLadderStep): string {
		return `${exactToken('cve', cve)} ${evidenceToken(step.evidence)}`;
	}
	function softwareHref(step: CveLadderStep): string {
		return ROUTES.surface(software.tab, { [software.queryParam]: query(step) });
	}
	function findingsHref(step: CveLadderStep): string {
		return ROUTES.surface(findings.tab, { [findings.queryParam]: query(step) });
	}
</script>

<div class="grid grid-cols-2 divide-y divide-border sm:grid-cols-4 sm:divide-x sm:divide-y-0">
	{#each ladder as step, i (step.evidence)}
		<div
			class="flex min-w-0 flex-col gap-2 px-5 py-4 {i % 2 === 0
				? 'max-sm:border-r'
				: ''} {step.count === 0 ? 'text-muted-foreground' : ''}"
		>
			<Hint text={step.help}>
				{#snippet child(props)}
					<span {...props} class="flex h-5 items-center">
						<EvidenceMark evidence={step.evidence} hint={false} />
					</span>
				{/snippet}
			</Hint>
			<span class="text-2xl leading-none font-semibold tabular-nums">
				{step.count.toLocaleString()}
			</span>
			<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs">
				{#if step.software > 0}
					<a href={softwareHref(step)} class="hover:underline">
						{step.software.toLocaleString()} in {software.label}
					</a>
				{/if}
				{#if step.findings > 0}
					<a href={findingsHref(step)} class="hover:underline">
						{step.findings.toLocaleString()} in {findings.label}
					</a>
				{/if}
				{#if step.count === 0}
					<span>None</span>
				{/if}
			</span>
		</div>
	{/each}
</div>
