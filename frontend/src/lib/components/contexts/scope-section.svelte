<script lang="ts">
	import { Label } from '$lib/components/ui/label';
	import { Switch } from '$lib/components/ui/switch';
	import { Separator } from '$lib/components/ui/separator';
	import * as Select from '$lib/components/ui/select';
	import StringListField from './string-list-field.svelte';
	import type { ScanContextRead, ScanContextCreate } from '$lib/types/scan-context';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();

	function validatePath(v: string): string | null {
		return v.startsWith('/') ? null : 'Path must start with /';
	}

	// IP or CIDR — mirror backend ipaddress.ip_network(strict=False) tolerance.
	function validateIp(v: string): string | null {
		const cidr = v.split('/');
		if (cidr.length > 2) return 'Enter a valid IP or CIDR';
		const ip = cidr[0];
		const v4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
		const v6 = /^[0-9a-fA-F:]+$/;
		const isV4 = v4.test(ip) && ip.split('.').every((o) => Number(o) <= 255);
		const isV6 = v6.test(ip) && ip.includes(':');
		if (!isV4 && !isV6) return 'Enter a valid IP or CIDR';
		if (cidr.length === 2) {
			const n = Number(cidr[1]);
			const maxPrefix = isV6 ? 128 : 32;
			if (cidr[1].trim() === '' || !Number.isInteger(n) || n < 0 || n > maxPrefix) {
				return 'Invalid CIDR prefix';
			}
		}
		return null;
	}
</script>

<div class="space-y-5">
	<div class="space-y-1.5">
		<Label class="text-xs">Excluded subdomains</Label>
		<StringListField
			items={context.excluded_subdomains}
			placeholder="staging.example.com"
			onChange={(items) => onChange({ excluded_subdomains: items })}
		/>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Excluded paths</Label>
		<StringListField
			items={context.excluded_paths}
			placeholder="/admin/*"
			validate={validatePath}
			onChange={(items) => onChange({ excluded_paths: items })}
		/>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Excluded IPs / CIDRs</Label>
		<StringListField
			items={context.excluded_ips}
			placeholder="10.0.0.0/8"
			validate={validateIp}
			onChange={(items) => onChange({ excluded_ips: items })}
		/>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Included subdomains</Label>
		<p class="text-xs text-muted-foreground">empty = scan everything discovered</p>
		<StringListField
			items={context.included_subdomains}
			placeholder="api.example.com"
			onChange={(items) => onChange({ included_subdomains: items })}
		/>
	</div>

	<Separator />

	<!-- DEFERRED baseline comparison — rendered disabled -->
	<div class="space-y-3 opacity-70">
		<div class="flex items-center justify-between gap-4">
			<div>
				<Label class="text-xs">Scan only new assets</Label>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Limit the scan to assets not seen in the baseline.
				</p>
			</div>
			<Switch checked={context.scan_only_new_assets} disabled />
		</div>

		<div class="space-y-1.5">
			<Label class="text-xs">Compare against baseline scan</Label>
			<Select.Root type="single" disabled>
				<Select.Trigger class="h-9 w-full text-sm">No baseline available</Select.Trigger>
				<Select.Content />
			</Select.Root>
		</div>

		<p class="text-xs text-muted-foreground">
			Available once this target has a completed baseline scan.
		</p>
	</div>
</div>
