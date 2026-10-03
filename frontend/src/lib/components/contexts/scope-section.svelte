<script lang="ts">
	import { Label } from '$lib/components/ui/label';
	import StringListField from './string-list-field.svelte';
	import { ipError, pathError, patternError } from './context-form';
	import type { ScanContextRead, ScanContextCreate } from '$lib/types/scan-context';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();
</script>

<div class="space-y-5">
	<div class="flex flex-col gap-3">
		<Label>Excluded subdomain patterns</Label>
		<StringListField
			items={context.excluded_subdomains}
			placeholder="admin"
			validate={patternError}
			onChange={(items) => onChange({ excluded_subdomains: items })}
		/>
		<p class="text-sm text-muted-foreground">
			Keyword, wildcard or regex matched against every discovered subdomain. Matches are recorded as <span
				class="text-warning">excluded</span
			> and skipped by later stages.
		</p>
	</div>

	<div class="flex flex-col gap-3">
		<Label>Excluded paths</Label>
		<StringListField
			items={context.excluded_paths}
			placeholder="/admin"
			validate={pathError}
			onChange={(items) => onChange({ excluded_paths: items })}
		/>
		<p class="text-sm text-muted-foreground">
			Path prefixes or regular expressions excluded from crawling and fuzzing.
		</p>
	</div>

	<div class="flex flex-col gap-3">
		<Label>Excluded IPs / CIDRs</Label>
		<StringListField
			items={context.excluded_ips}
			placeholder="10.0.0.0/8"
			validate={ipError}
			onChange={(items) => onChange({ excluded_ips: items })}
		/>
	</div>

	<div class="flex flex-col gap-3">
		<Label>Included subdomains</Label>
		<StringListField
			items={context.included_subdomains}
			placeholder="api.example.com"
			onChange={(items) => onChange({ included_subdomains: items })}
		/>
		<p class="text-sm text-muted-foreground">An empty list scans every discovered subdomain.</p>
	</div>
</div>
