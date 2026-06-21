<script lang="ts">
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Label } from '$lib/components/ui/label';
	import { Textarea } from '$lib/components/ui/textarea';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import * as Select from '$lib/components/ui/select';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { X, Key, ChevronDown } from 'lucide-svelte';
	import type { Snippet } from 'svelte';
	import type { DiscoveryConfig, ExpansionConfig, DepthConfig } from '$lib/types/engine';
	import { PHASE_COLORS } from '$lib/types/engine';
	import { CAPABILITIES } from '$lib/types/capabilities';

	interface Props {
		capabilityId: string | null;
		phase: 'discovery' | 'expansion' | 'depth' | null;
		config: DiscoveryConfig | ExpansionConfig | DepthConfig | null;
		onChange?: (updates: Record<string, unknown>) => void;
		onClose?: () => void;
	}

	let { capabilityId, phase, config, onChange, onClose }: Props = $props();

	let phaseColor = $derived(phase ? PHASE_COLORS[phase] : null);
	let capability = $derived(capabilityId ? CAPABILITIES.find((c) => c.id === capabilityId) : null);
	let capLabel = $derived(capability?.label ?? capabilityId ?? '');

	let localConfig = $state<Record<string, unknown>>({});

	$effect(() => {
		if (config) {
			localConfig = JSON.parse(JSON.stringify(config));
		}
	});

	function get<T>(path: string, fallback: T): T {
		const parts = path.split('.');
		let cur: unknown = localConfig;
		for (const p of parts) {
			if (cur == null || typeof cur !== 'object') return fallback;
			cur = (cur as Record<string, unknown>)[p];
		}
		return cur === undefined ? fallback : (cur as T);
	}

	function set(path: string, value: unknown) {
		const parts = path.split('.');
		let cur = localConfig as Record<string, unknown>;
		for (let i = 0; i < parts.length - 1; i++) {
			if (cur[parts[i]] == null || typeof cur[parts[i]] !== 'object') {
				cur[parts[i]] = {};
			}
			cur = cur[parts[i]] as Record<string, unknown>;
		}
		cur[parts[parts.length - 1]] = value;
		onChange?.(localConfig);
	}

	function toggleArray(path: string, val: string) {
		const arr = get<string[]>(path, []);
		const next = arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
		set(path, next);
	}

	function toggleIntArray(path: string, val: number) {
		const arr = get<number[]>(path, []);
		const next = arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
		set(path, next);
	}

	function hasInArray(path: string, val: string): boolean {
		return get<string[]>(path, []).includes(val);
	}

	function hasInIntArray(path: string, val: number): boolean {
		return get<number[]>(path, []).includes(val);
	}

	let openSections = $state<Record<string, boolean>>({});

	function sectionOpen(key: string): boolean {
		return openSections[key] !== false;
	}
</script>

{#if capabilityId}
	<div class="config-panel">
		<div class="panel-header">
			<div class="header-content">
				<div class="header-text">
					<span
						class="phase-dot"
						style="background: {phaseColor?.accent ?? 'var(--muted-foreground)'};"
					></span>
					<span class="cap-title">{capLabel}</span>
				</div>
				<Button variant="ghost" size="icon-sm" onclick={() => onClose?.()}>
					<X size={16} />
				</Button>
			</div>
		</div>

		<ScrollArea class="panel-body">
			<div class="body-inner">
				{#if capabilityId === 'dns-whois'}
					{#snippet dnsBody()}
						{@render numberRow('Timeout (s)', 'dns_timeout', 10)}
						{@render numberRow('Threads', 'dns_threads', 100)}
					{/snippet}
					{@render section('dns', 'DNS Settings', dnsBody)}
					{#snippet whoisBody()}
						{@render numberRow('Timeout (s)', 'whois_timeout', 30)}
					{/snippet}
					{@render section('whois', 'WHOIS', whoisBody)}
					{#snippet rdnsBody()}
						{@render toggleRow('Reverse DNS lookups', 'ip_reverse_dns', true)}
					{/snippet}
					{@render section('rdns', 'Reverse DNS', rdnsBody)}

				{:else if capabilityId === 'related-domains'}
					{#snippet methodsBody()}
						{@render toggleRow('WHOIS registrant', 'related_by_whois_registrant', false)}
						{@render toggleRow('Nameservers', 'related_by_nameservers', false)}
						{@render toggleRow('Cert SAN', 'related_by_cert_san', false)}
						{@render toggleRow('IP neighbors', 'related_by_ip_neighbors', false)}
						{@render toggleRow('Google Analytics ID', 'related_by_ga_id', false)}
						{@render toggleRow('Favicon hash', 'related_by_favicon_hash', false)}
						{@render toggleRow('ASN', 'related_by_asn', false)}
					{/snippet}
					{@render section('methods', 'Discovery Methods', methodsBody)}
					{#snippet tldBody()}
						{@render toggleRow('Enable TLD variations', 'related_tld_variations', false)}
						<p class="hint">Comma-separated TLDs (e.g. com, net, org)</p>
						<Textarea
							class="text-xs font-mono"
							value={get<string[]>('related_tlds', []).join(', ')}
							oninput={(e) => set('related_tlds', e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean))}
						/>
					{/snippet}
					{@render section('tld', 'TLD Variations', tldBody)}
					{#snippet confidenceBody()}
						{@render numberRow('Threshold (0-100)', 'related_confidence_threshold', 80)}
					{/snippet}
					{@render section('confidence', 'Confidence', confidenceBody)}
					{#snippet confirmBody()}
						{@render toggleRow('Confirm before adding', 'related_require_confirmation', true)}
					{/snippet}
					{@render section('confirm', 'Require Confirmation', confirmBody)}
					{#snippet actionBody()}
						{@render radioGroup('related_action', 'report_only', [
							{ value: 'scan', label: 'Scan related domains' },
							{ value: 'report_only', label: 'Report only' }
						])}
					{/snippet}
					{@render section('action', 'Action', actionBody)}

				{:else if capabilityId === 'org-asn'}
					{#snippet sourcesBody()}
						{@render toggleKey('WHOIS org search', 'org_whois_search', false, 'WHOISXML')}
						{@render toggleRow('Certificate transparency', 'org_cert_transparency', false)}
						{@render toggleRow('ASN lookup', 'org_asn_lookup', false)}
					{/snippet}
					{@render section('sources', 'Org Sources', sourcesBody)}
					{#snippet variationsBody()}
						<p class="hint">One name variation per line</p>
						<Textarea
							class="text-xs font-mono"
							value={get<string[]>('org_name_variations', []).join('\n')}
							oninput={(e) => set('org_name_variations', e.currentTarget.value.split('\n').map((s) => s.trim()).filter(Boolean))}
						/>
					{/snippet}
					{@render section('variations', 'Name Variations', variationsBody)}
					{#snippet patternsBody()}
						<p class="hint">One pattern per line</p>
						<Textarea
							class="text-xs font-mono"
							value={get<string[]>('org_custom_patterns', []).join('\n')}
							oninput={(e) => set('org_custom_patterns', e.currentTarget.value.split('\n').map((s) => s.trim()).filter(Boolean))}
						/>
					{/snippet}
					{@render section('patterns', 'Custom Patterns', patternsBody)}
					{#snippet asnModeBody()}
						{@render radioGroup('asn_scan_mode', 'smart', [
							{ value: 'smart', label: 'Smart (recommended)' },
							{ value: 'sample', label: 'Sample' },
							{ value: 'full', label: 'Full scan' }
						])}
					{/snippet}
					{@render section('asn-mode', 'ASN Scan Mode', asnModeBody)}
					{#snippet cidrBody()}
						{@render toggleRow('Skip RFC1918 (private ranges)', 'cidr_skip_rfc1918', true)}
						{@render toggleRow('Skip CDN ranges', 'cidr_skip_cdn_ranges', true)}
					{/snippet}
					{@render section('cidr', 'CIDR Filtering', cidrBody)}

				{:else if capabilityId === 'subdomain-enum'}
					{#snippet passiveBody()}
						{@render toggleRow('Enable passive enumeration', 'subdomain_passive', false)}
						{@render checkGroup('subdomain_passive_tools', [
							{ value: 'subfinder', label: 'Subfinder' },
							{ value: 'amass', label: 'Amass (passive)' },
							{ value: 'crtsh', label: 'crt.sh' }
						])}
						<p class="hint">API-key sources</p>
						{@render toggleKey('SecurityTrails', 'subdomain_securitytrails', false, 'SecurityTrails')}
						{@render toggleKey('Censys', 'subdomain_censys', false, 'Censys')}
						{@render toggleKey('VirusTotal', 'subdomain_virustotal', false, 'VirusTotal')}
						{@render toggleKey('Chaos', 'subdomain_chaos', false, 'Chaos')}
						{@render toggleKey('BinaryEdge', 'subdomain_binaryedge', false, 'BinaryEdge')}
					{/snippet}
					{@render section('passive', 'Passive', passiveBody)}
					{#snippet activeBody()}
						{@render toggleRow('Enable active brute force', 'subdomain_active', false)}
						{@render selectRow('Wordlist', 'subdomain_wordlist', '', [
							{ value: '', label: 'Default' },
							{ value: 'small', label: 'Small (fast)' },
							{ value: 'medium', label: 'Medium' },
							{ value: 'large', label: 'Large' },
							{ value: 'custom', label: 'Custom' }
						])}
						{@render toggleRow('Use Amass config', 'amass_config', false)}
						{@render toggleRow('Use Subfinder config', 'subfinder_config', false)}
					{/snippet}
					{@render section('active', 'Active', activeBody)}
					{#snippet tlsBody()}
						{@render toggleRow('TLS certificate discovery', 'subdomain_tls_discovery', false)}
					{/snippet}
					{@render section('tls', 'TLS Discovery', tlsBody)}
					{#snippet scrapingBody()}
						{@render toggleRow('Scrape pages for subdomains', 'subdomain_scraping', false)}
					{/snippet}
					{@render section('scraping', 'Web Scraping', scrapingBody)}
					{#snippet permBody()}
						{@render toggleRow('Enable permutations', 'subdomain_permutation', false)}
						{@render checkGroup('subdomain_permutation_tools', [
							{ value: 'gotator', label: 'Gotator' },
							{ value: 'alterx', label: 'AlterX' },
							{ value: 'dnsgen', label: 'DNSGen' }
						])}
						{@render toggleRow('AI-assisted permutation', 'subdomain_ai_permutation', false)}
					{/snippet}
					{@render section('perm', 'Permutations', permBody)}
					{#snippet dnsTechBody()}
						{@render toggleRow('NOERROR detection', 'subdomain_noerror', false)}
						{@render toggleRow('Recursive resolution', 'subdomain_recursive', false)}
					{/snippet}
					{@render section('dns-tech', 'DNS Techniques', dnsTechBody)}

				{:else if capabilityId === 'takeover-dns'}
					{#snippet takeoverBody()}
						{@render toggleRow('Subdomain takeover check', 'subdomain_takeover', false)}
					{/snippet}
					{@render section('takeover', 'Takeover', takeoverBody)}
					{#snippet zoneBody()}
						{@render toggleRow('DNS zone transfer (AXFR)', 'dns_zone_transfer', false)}
					{/snippet}
					{@render section('zone', 'Zone Transfer', zoneBody)}

				{:else if capabilityId === 'cloud-recon'}
					{#snippet bucketBody()}
						{@render toggleKey('Cloud bucket enumeration', 'cloud_bucket_enum', false, 'Shodan')}
						<p class="hint">Uses S3Scanner and cloud_enum to find exposed buckets across AWS, GCP, and Azure.</p>
					{/snippet}
					{@render section('bucket', 'Bucket Enumeration', bucketBody)}
					{#snippet reverseIpBody()}
						{@render toggleRow('Reverse IP lookup', 'reverse_ip_lookup', false)}
						<p class="hint">Resolves co-hosted hostnames per IP via hakip2host.</p>
					{/snippet}
					{@render section('reverse-ip', 'Reverse IP Lookup', reverseIpBody)}

				{:else if capabilityId === 'port-scan'}
					{#snippet portsBody()}
						{@render radioGroup('port_scan_ports', 'top-100', [
							{ value: 'top-100', label: 'Top 100 ports (fast)' },
							{ value: 'top-1000', label: 'Top 1000 ports' },
							{ value: 'full', label: 'Full range (1-65535)' }
						])}
						<div class="field-col">
							<Label for="ps-custom" class="field-sub">Custom (comma / range)</Label>
							<Input id="ps-custom" placeholder="80,443,8000-9000" value={get('port_scan_ports', 'top-100')} oninput={(e) => set('port_scan_ports', e.currentTarget.value)} class="text-sm font-mono" />
						</div>
					{/snippet}
					{@render section('ports', 'Port Range', portsBody)}
					{#snippet rateBody()}
						{@render numberRow('Rate limit (pkts/s)', 'port_scan_rate_limit', 1000)}
						{@render numberRow('Timeout (ms)', 'port_scan_timeout', 3000)}
						{@render numberRow('Threads', 'port_scan_threads', 50)}
					{/snippet}
					{@render section('rate', 'Rate / Timeout / Threads', rateBody)}
					{#snippet passivePortsBody()}
						{@render toggleKey('Use Shodan for passive port data', 'port_scan_passive_shodan', false, 'Shodan')}
					{/snippet}
					{@render section('passive-ports', 'Passive (Shodan)', passivePortsBody)}
					{#snippet nmapBody()}
						{@render toggleRow('Enable Nmap', 'nmap_enabled', false)}
						<div class="field-col">
							<Label for="nmap-cmd" class="field-sub">Command flags</Label>
							<Input id="nmap-cmd" placeholder="-sV -sC -O" value={get('nmap_cmd', '')} oninput={(e) => set('nmap_cmd', e.currentTarget.value)} class="text-sm font-mono" />
						</div>
						<div class="field-col">
							<Label for="nmap-script" class="field-sub">Script</Label>
							<Input id="nmap-script" placeholder="vuln,auth" value={get('nmap_script', '')} oninput={(e) => set('nmap_script', e.currentTarget.value)} class="text-sm font-mono" />
						</div>
						<div class="field-col">
							<Label for="nmap-args" class="field-sub">Script args</Label>
							<Input id="nmap-args" placeholder="script arguments..." value={get('nmap_script_args', '')} oninput={(e) => set('nmap_script_args', e.currentTarget.value)} class="text-sm font-mono" />
						</div>
					{/snippet}
					{@render section('nmap', 'Nmap', nmapBody)}

				{:else if capabilityId === 'http-probe'}
					{#snippet probingBody()}
						{@render toggleRow('HTTP probing & crawl', 'http_crawl', true)}
						<p class="hint">httpx probes live services and records titles, status & favicon hashes.</p>
					{/snippet}
					{@render section('probing', 'Probing', probingBody)}
					{#snippet cdnBody()}
						{@render toggleRow('Detect CDN', 'cdn_detection', true)}
					{/snippet}
					{@render section('cdn', 'CDN Detection', cdnBody)}
					{#snippet wafBody()}
						{@render toggleRow('Detect WAF', 'waf_detection', true)}
					{/snippet}
					{@render section('waf', 'WAF Detection', wafBody)}
					{#snippet geoBody()}
						{@render toggleRow('Geolocate IPs', 'ip_geolocation', false)}
					{/snippet}
					{@render section('geo', 'IP Geolocation', geoBody)}
					{#snippet techBody()}
						{@render toggleRow('Detect tech stack', 'tech_detection', true)}
					{/snippet}
					{@render section('tech', 'Technology Detection', techBody)}
					{#snippet cmsBody()}
						{@render toggleRow('Detect CMS', 'cms_detection', false)}
						<p class="hint">CMSeeK fingerprints WordPress, Drupal, Joomla & more.</p>
					{/snippet}
					{@render section('cms', 'CMS Detection', cmsBody)}
					{#snippet probeVhostBody()}
						{@render toggleRow('VHost bruteforce', 'vhost_bruteforce', false)}
						<p class="hint">Host-header fuzzing to surface virtual hosts not resolvable via DNS.</p>
					{/snippet}
					{@render section('probe-vhost', 'VHost Bruteforce', probeVhostBody)}
					{#snippet faviconBody()}
						<p class="hint">httpx records favicon hashes automatically for related-asset pivots — no extra config.</p>
					{/snippet}
					{@render section('favicon', 'Favicon', faviconBody)}

				{:else if capabilityId === 'screenshot'}
					{#snippet screenshotBody()}
						{@render toggleRow('Capture screenshots', 'screenshot', true)}
						{@render numberRow('Timeout (s)', 'screenshot_timeout', 15)}
						{@render numberRow('Threads', 'screenshot_threads', 10)}
						<p class="hint">Renders live hosts with gowitness / EyeWitness.</p>
					{/snippet}
					{@render section('screenshot', 'Screenshot', screenshotBody)}

				{:else if capabilityId === 'url-discovery'}
					{#snippet urlToolsBody()}
						{@render checkGroup('url_discovery_tools', [
							{ value: 'katana', label: 'Katana' },
							{ value: 'gau', label: 'gau' },
							{ value: 'waybackurls', label: 'Wayback Machine' },
							{ value: 'gospider', label: 'GoSpider' }
						])}
					{/snippet}
					{@render section('url-tools', 'Tools', urlToolsBody)}
					{#snippet gfBody()}
						{@render checkChips('url_gf_patterns', ['sqli', 'ssrf', 'xss', 'lfi', 'rce', 'idor', 'redirect', 'debug'])}
					{/snippet}
					{@render section('gf', 'GF Patterns', gfBody)}
					{#snippet dedupBody()}
						{@render toggleRow('Deduplicate URLs', 'url_dedup', true)}
						<div class="field-col">
							<Label for="url-dedup-fields" class="field-sub">Dedup fields (csv)</Label>
							<Input id="url-dedup-fields" placeholder="path,query" value={get<string[]>('url_dedup_fields', []).join(',')} oninput={(e) => set('url_dedup_fields', e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean))} class="text-sm font-mono" />
						</div>
					{/snippet}
					{@render section('dedup', 'Deduplication', dedupBody)}
					{#snippet urlIgnoreBody()}
						<div class="field-col">
							<Label for="url-ignore-ext" class="field-sub">Extensions (csv)</Label>
							<Input id="url-ignore-ext" placeholder="css,png,jpg,gif" value={get<string[]>('url_ignore_extensions', []).join(',')} oninput={(e) => set('url_ignore_extensions', e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean))} class="text-sm font-mono" />
						</div>
					{/snippet}
					{@render section('url-ignore', 'Ignore Extensions', urlIgnoreBody)}

				{:else if capabilityId === 'dir-fuzz'}
					{#snippet fuzzWordlistBody()}
						{@render selectRow('Wordlist', 'dir_fuzz_wordlist', '', [
							{ value: '', label: 'Default' },
							{ value: 'small', label: 'Small' },
							{ value: 'medium', label: 'Medium' },
							{ value: 'large', label: 'Large' },
							{ value: 'raft-medium', label: 'Raft Medium' }
						])}
					{/snippet}
					{@render section('fuzz-wordlist', 'Wordlist', fuzzWordlistBody)}
					{#snippet fuzzExtBody()}
						<div class="field-col">
							<Label for="fuzz-ext" class="field-sub">Extensions (csv)</Label>
							<Input id="fuzz-ext" placeholder="php,asp,html,js" value={get<string[]>('dir_fuzz_extensions', []).join(',')} oninput={(e) => set('dir_fuzz_extensions', e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean))} class="text-sm font-mono" />
						</div>
					{/snippet}
					{@render section('fuzz-ext', 'Extensions', fuzzExtBody)}
					{#snippet fuzzDepthBody()}
						{@render numberRow('Recursive depth', 'dir_fuzz_recursive_depth', 2)}
					{/snippet}
					{@render section('fuzz-depth', 'Recursion Depth', fuzzDepthBody)}
					{#snippet fuzzStatusBody()}
						{@render checkChipsInt('dir_fuzz_match_status', [200, 201, 204, 301, 302, 307, 401, 403])}
					{/snippet}
					{@render section('fuzz-status', 'Match Status Codes', fuzzStatusBody)}
					{#snippet fuzzRateBody()}
						{@render numberRow('Rate limit (req/s)', 'dir_fuzz_rate_limit', 150)}
						{@render numberRow('Threads', 'dir_fuzz_threads', 50)}
					{/snippet}
					{@render section('fuzz-rate', 'Rate / Threads', fuzzRateBody)}
					{#snippet fuzzCalibBody()}
						{@render toggleRow('Auto-calibration', 'dir_fuzz_auto_calibration', true)}
					{/snippet}
					{@render section('fuzz-calib', 'Auto-calibration', fuzzCalibBody)}

				{:else if capabilityId === 'param-vhost'}
					{#snippet paramBody()}
						{@render toggleRow('Enable parameter discovery', 'param_discovery', false)}
						{@render checkGroup('param_discovery_tools', [
							{ value: 'x8', label: 'x8' },
							{ value: 'arjun', label: 'Arjun' }
						])}
						<p class="hint">Surfaces hidden GET/POST parameters on discovered endpoints.</p>
					{/snippet}
					{@render section('param', 'Parameter Discovery', paramBody)}

				{:else if capabilityId === 'vuln-scan'}
					{#snippet nucleiBody()}
						{@render toggleRow('Enable Nuclei', 'nuclei_enabled', true)}
						<p class="hint">Severity</p>
						{@render checkChips('nuclei_severities', ['unknown', 'info', 'low', 'medium', 'high', 'critical'])}
						<div class="field-col">
							<Label for="nuclei-tags" class="field-sub">Tags (csv)</Label>
							<Input id="nuclei-tags" placeholder="cve,oast,rce" value={get<string[]>('nuclei_tags', []).join(',')} oninput={(e) => set('nuclei_tags', e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean))} class="text-sm font-mono" />
						</div>
						<p class="hint">Templates</p>
						{@render boolRadioGroup('nuclei_use_config', false, [
							{ value: false, label: 'Default templates' },
							{ value: true, label: 'Custom config' }
						])}
						{@render numberRow('Concurrency', 'nuclei_concurrency', 25)}
						{@render numberRow('Rate limit (req/s)', 'nuclei_rate_limit', 150)}
						{@render numberRow('Retries', 'nuclei_retries', 1)}
						{@render numberRow('Timeout (s)', 'nuclei_timeout', 10)}
					{/snippet}
					{@render section('nuclei', 'Nuclei', nucleiBody)}
					{#snippet corsBody()}
						{@render toggleRow('CORS misconfiguration', 'cors_check', false)}
					{/snippet}
					{@render section('cors', 'CORS', corsBody)}
					{#snippet xssBody()}
						{@render toggleRow('Dalfox XSS scanner', 'dalfox_enabled', false)}
					{/snippet}
					{@render section('xss', 'XSS', xssBody)}
					{#snippet otherBody()}
						{@render toggleRow('CRLFuzz (CRLF injection)', 'crlfuzz_enabled', false)}
						{@render toggleRow('SQLMap (SQL injection)', 'sqlmap_enabled', false)}
						{@render toggleRow('SSRF check', 'ssrf_enabled', false)}
						{@render toggleRow('403 bypass', 'bypass_403', false)}
						{@render toggleRow('HTTP smuggling', 'http_smuggling', false)}
						{@render toggleRow('Prototype pollution', 'prototype_pollution', false)}
						{@render toggleRow('GraphQL introspection', 'graphql_detection', false)}
					{/snippet}
					{@render section('other', 'Other Scanners', otherBody)}

				{:else if capabilityId === 'tls-ssl'}
					{#snippet tlsSslBody()}
						{@render toggleRow('Enable TLS/SSL analysis', 'ssl_tls_analysis', false)}
						<p class="hint">Inspects certificate chain, weak ciphers, expiry & HSTS via testssl / tlsx.</p>
					{/snippet}
					{@render section('tls-ssl', 'TLS / SSL Analysis', tlsSslBody)}

				{:else if capabilityId === 'js-secrets'}
					{#snippet jsToolsBody()}
						{@render toggleRow('Enable JS secret scanning', 'js_secret_scan', false)}
						{@render checkGroup('js_secret_tools', [
							{ value: 'secretfinder', label: 'SecretFinder' },
							{ value: 'mantra', label: 'Mantra' }
						])}
					{/snippet}
					{@render section('js-tools', 'Tools', jsToolsBody)}

				{:else if capabilityId === 'reporting'}
					{#snippet reportFormatsBody()}
						{@render checkChips('report_formats', ['html', 'json', 'csv', 'pdf'], true)}
					{/snippet}
					{@render section('report-formats', 'Formats', reportFormatsBody)}
					{#snippet reportAiBody()}
						{@render toggleRow('AI-powered executive summary', 'report_ai_summary', false)}
					{/snippet}
					{@render section('report-ai', 'AI Summary', reportAiBody)}
					{#snippet reportNotifyBody()}
						{@render toggleRow('Slack', 'report_notify_slack', false)}
						{@render toggleRow('Discord', 'report_notify_discord', false)}
						{@render toggleRow('Telegram', 'report_notify_telegram', false)}
						<div class="field-col">
							<Label for="report-webhook" class="field-sub">Webhook URL</Label>
							<Input id="report-webhook" placeholder="https://hooks.example.com/..." value={get('report_webhook_url', '')} oninput={(e) => set('report_webhook_url', e.currentTarget.value)} class="text-sm" />
						</div>
					{/snippet}
					{@render section('report-notify', 'Notifications', reportNotifyBody)}
					{#snippet reportOnBody()}
						{@render radioGroup('report_send_on', 'completion', [
							{ value: 'completion', label: 'Scan completion' },
							{ value: 'each_phase', label: 'Each phase' },
							{ value: 'both', label: 'Both' }
						])}
					{/snippet}
					{@render section('report-on', 'Send On', reportOnBody)}
				{/if}
			</div>
		</ScrollArea>

		<div class="panel-footer">
			<Button variant="outline" class="w-full" onclick={() => onClose?.()}>Close</Button>
		</div>
	</div>
{/if}

{#snippet section(key: string, title: string, body: Snippet)}
	<Collapsible.Root bind:open={() => sectionOpen(key), (v) => (openSections[key] = v)}>
		<Collapsible.Trigger class="section-trigger">
			<span class="section-title">{title}</span>
			<ChevronDown size={14} class="section-chevron" data-open={sectionOpen(key)} />
		</Collapsible.Trigger>
		<Collapsible.Content class="sect-body">
			{@render body()}
		</Collapsible.Content>
	</Collapsible.Root>
{/snippet}

{#snippet toggleRow(label: string, path: string, fallback: boolean)}
	<div class="toggle-row">
		<Label class="field-label" for="sw-{path}">{label}</Label>
		<Switch id="sw-{path}" checked={get(path, fallback)} onCheckedChange={(v) => set(path, v)} />
	</div>
{/snippet}

{#snippet toggleKey(label: string, path: string, fallback: boolean, keyName: string)}
	<div class="toggle-row">
		<Label class="field-label" for="sw-{path}">
			{label}
			<Badge variant="outline" class="key-badge"><Key size={9} />{keyName}</Badge>
		</Label>
		<Switch id="sw-{path}" checked={get(path, fallback)} onCheckedChange={(v) => set(path, v)} />
	</div>
{/snippet}

{#snippet numberRow(label: string, path: string, fallback: number)}
	<div class="toggle-row">
		<Label class="field-label" for="num-{path}">{label}</Label>
		<Input id="num-{path}" type="number" value={get(path, fallback)} oninput={(e) => set(path, Number(e.currentTarget.value))} class="w-24 text-sm" />
	</div>
{/snippet}

{#snippet radioGroup(path: string, fallback: string, options: { value: string; label: string }[])}
	<RadioGroup.Root value={get(path, fallback)} onValueChange={(v) => set(path, v)} class="gap-2">
		{#each options as opt (opt.value)}
			<div class="radio-row">
				<RadioGroup.Item value={opt.value} id="{path}-{opt.value}" />
				<Label for="{path}-{opt.value}" class="field-label">{opt.label}</Label>
			</div>
		{/each}
	</RadioGroup.Root>
{/snippet}

{#snippet boolRadioGroup(path: string, fallback: boolean, options: { value: boolean; label: string }[])}
	<RadioGroup.Root value={String(get(path, fallback))} onValueChange={(v) => set(path, v === 'true')} class="gap-2">
		{#each options as opt (String(opt.value))}
			<div class="radio-row">
				<RadioGroup.Item value={String(opt.value)} id="{path}-{String(opt.value)}" />
				<Label for="{path}-{String(opt.value)}" class="field-label">{opt.label}</Label>
			</div>
		{/each}
	</RadioGroup.Root>
{/snippet}

{#snippet checkGroup(path: string, options: { value: string; label: string }[])}
	<div class="check-group">
		{#each options as opt (opt.value)}
			<div class="check-row">
				<Checkbox id="{path}-{opt.value}" checked={hasInArray(path, opt.value)} onCheckedChange={() => toggleArray(path, opt.value)} />
				<Label for="{path}-{opt.value}" class="check-label">{opt.label}</Label>
			</div>
		{/each}
	</div>
{/snippet}

{#snippet checkChips(path: string, values: string[], upper = false)}
	<div class="chip-wrap">
		{#each values as v (v)}
			<div class="chip-row">
				<Checkbox id="{path}-{v}" checked={hasInArray(path, v)} onCheckedChange={() => toggleArray(path, v)} />
				<Label for="{path}-{v}" class="chip-label">{upper ? v.toUpperCase() : v}</Label>
			</div>
		{/each}
	</div>
{/snippet}

{#snippet checkChipsInt(path: string, values: number[])}
	<div class="chip-wrap">
		{#each values as v (v)}
			<div class="chip-row">
				<Checkbox id="{path}-{v}" checked={hasInIntArray(path, v)} onCheckedChange={() => toggleIntArray(path, v)} />
				<Label for="{path}-{v}" class="chip-label">{v}</Label>
			</div>
		{/each}
	</div>
{/snippet}

{#snippet selectRow(label: string, path: string, fallback: string, options: { value: string; label: string }[])}
	<div class="field-col">
		<Label class="field-sub">{label}</Label>
		<Select.Root type="single" value={get(path, fallback)} onValueChange={(v) => set(path, v ?? '')}>
			<Select.Trigger class="w-full text-sm">
				{options.find((o) => o.value === get(path, fallback))?.label ?? 'Select…'}
			</Select.Trigger>
			<Select.Content>
				{#each options as opt (opt.value)}
					<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>
{/snippet}

<style>
	:global(.config-panel) {
		width: 384px;
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--card);
		border-left: 1px solid var(--border);
		overflow: hidden;
	}

	:global(.panel-header) {
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
	}

	:global(.header-content) {
		padding: 14px 18px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}

	:global(.header-text) {
		display: flex;
		align-items: center;
		gap: 9px;
		min-width: 0;
	}

	:global(.phase-dot) {
		width: 8px;
		height: 8px;
		border-radius: 999px;
		flex-shrink: 0;
	}

	:global(.cap-title) {
		font-size: 15px;
		font-weight: 600;
		color: var(--foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	:global(.panel-body) {
		flex: 1;
		min-height: 0;
	}

	:global(.body-inner) {
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	:global(.sect-body) {
		padding: 12px 4px 4px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	:global(.field-col) {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	:global(.field-sub) {
		font-size: 12px;
		color: var(--muted-foreground);
	}

	:global(.check-group) {
		display: flex;
		flex-direction: column;
		gap: 9px;
	}

	:global(.chip-wrap) {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 16px;
	}

	:global(.hint) {
		font-size: 12px;
		color: var(--muted-foreground);
		line-height: 1.5;
	}

	:global(.panel-footer) {
		padding: 10px 16px;
		border-top: 1px solid var(--border);
		flex-shrink: 0;
		display: flex;
		gap: 8px;
	}

	:global(.section-trigger) {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 8px 12px;
		background: var(--muted);
		border-radius: 8px;
		border: 1px solid var(--border);
		cursor: pointer;
		user-select: none;
		transition: background 0.12s;
	}

	:global(.section-trigger:hover) {
		background: var(--accent);
	}

	:global(.section-title) {
		font-size: 10px;
		font-weight: 700;
		color: var(--foreground);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	:global(.section-chevron) {
		color: var(--muted-foreground);
		transition: transform 0.15s ease;
	}

	:global(.section-chevron[data-open='false']) {
		transform: rotate(-90deg);
	}

	:global(.toggle-row) {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}

	:global(.field-label) {
		font-size: 12px;
		color: var(--foreground);
		flex: 1;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
	}

	:global(.radio-row),
	:global(.check-row) {
		display: flex;
		align-items: center;
		gap: 9px;
	}

	:global(.check-label) {
		flex: 1;
		font-size: 12px;
		color: var(--foreground);
		cursor: pointer;
	}

	:global(.chip-row) {
		display: inline-flex;
		align-items: center;
		gap: 7px;
	}

	:global(.chip-label) {
		font-size: 12px;
		color: var(--foreground);
		cursor: pointer;
		font-family: var(--font-mono);
	}

	:global(.key-badge) {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		font-size: 9px;
		font-weight: 600;
		padding: 1px 5px;
	}
</style>
