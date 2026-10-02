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
	<div class="space-y-1.5">
		<Label class="text-xs">Excluded subdomain patterns</Label>
		<p class="text-xs text-muted-foreground">
			Keyword, wildcard or regex matched against every discovered subdomain. Matches are recorded as <span
				class="text-warning">excluded</span
			> and skipped by later stages.
		</p>
		<StringListField
			items={context.excluded_subdomains}
			placeholder="admin"
			validate={patternError}
			onChange={(items) => onChange({ excluded_subdomains: items })}
		/>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Excluded paths</Label>
		<p class="text-xs text-muted-foreground">
			Path prefixes or regular expressions excluded from crawling and fuzzing.
		</p>
		<StringListField
			items={context.excluded_paths}
			placeholder="/admin"
			validate={pathError}
			onChange={(items) => onChange({ excluded_paths: items })}
		/>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Excluded IPs / CIDRs</Label>
		<StringListField
			items={context.excluded_ips}
			placeholder="10.0.0.0/8"
			validate={ipError}
			onChange={(items) => onChange({ excluded_ips: items })}
		/>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Included subdomains</Label>
		<p class="text-xs text-muted-foreground">An empty list scans every discovered subdomain.</p>
		<StringListField
			items={context.included_subdomains}
			placeholder="api.example.com"
			onChange={(items) => onChange({ included_subdomains: items })}
		/>
	</div>
</div>
