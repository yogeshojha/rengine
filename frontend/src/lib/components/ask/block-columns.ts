import { ABOUT_SEPARATOR } from '$lib/config/ask';
import { ROUTES } from '$lib/config/routes';
import { MAX_QUERY_LENGTH, SurfaceDimension, surfaceSpec } from '$lib/config/surface';
import { hostPort } from '$lib/utilities/net';
import { exactToken } from '$lib/utilities/scan-insights';
import { scopeClause, withClause } from '$lib/components/dashboard/scope-links';
import type { BlockRow } from '$lib/types/ask';

export type Cell =
	| { kind: 'mono'; text: string; strong?: boolean }
	| { kind: 'text'; text: string; muted?: boolean }
	| { kind: 'status'; code: number | null }
	| { kind: 'severity'; value: string | null; count?: number | null; kev?: boolean }
	| { kind: 'tech'; items: string[]; more: number }
	| { kind: 'country'; code: string | null }
	| { kind: 'evidence'; value: string | null }
	| { kind: 'kev'; on: boolean }
	| { kind: 'empty' };

export interface BlockColumn {
	key: string;
	label: string;
	width: string;
	cell: (row: BlockRow) => Cell;
}

const MAX_TECH = 3;

const str = (v: unknown): string => (v == null ? '' : String(v));
const num = (v: unknown): number | null => (typeof v === 'number' ? v : null);
const list = (v: unknown): string[] => (Array.isArray(v) ? v.map(String) : []);
const text = (v: unknown, muted = false): Cell =>
	str(v) ? { kind: 'text', text: str(v), muted } : { kind: 'empty' };

function tech(v: unknown): Cell {
	const items = list(v);
	if (!items.length) return { kind: 'empty' };
	return { kind: 'tech', items: items.slice(0, MAX_TECH), more: items.length - MAX_TECH };
}

function hostOf(url: unknown): string {
	const raw = str(url);
	const rest = raw.split('://', 2)[1] ?? raw;
	return rest.split('/', 1)[0];
}

function pathOf(url: unknown): string {
	const raw = str(url);
	const rest = raw.split('://', 2)[1] ?? raw;
	const at = rest.indexOf('/');
	return at >= 0 ? rest.slice(at) : '/';
}

const product = (row: BlockRow): string =>
	[str(row.product), str(row.version)].filter(Boolean).join(' ');

export const BLOCK_COLUMNS: Record<string, BlockColumn[]> = {
	[SurfaceDimension.WEB_ASSETS]: [
		{
			key: 'name',
			label: 'Web asset',
			width: 'min-w-[14rem]',
			cell: (r) => ({ kind: 'mono', text: str(r.name), strong: true })
		},
		{
			key: 'status',
			label: 'Status',
			width: 'w-16',
			cell: (r) => ({ kind: 'status', code: num(r.http_status) })
		},
		{
			key: 'title',
			label: 'Title',
			width: 'min-w-[12rem] max-w-[20rem]',
			cell: (r) => text(r.page_title)
		},
		{ key: 'tech', label: 'Technology', width: 'min-w-[18rem]', cell: (r) => tech(r.tech) },
		{
			key: 'findings',
			label: 'Findings',
			width: 'w-28',
			cell: (r) =>
				r.vuln_severity
					? {
							kind: 'severity',
							value: str(r.vuln_severity),
							count: num(r.vuln_count),
							kev: !!r.vuln_kev
						}
					: { kind: 'empty' }
		}
	],
	[SurfaceDimension.ENDPOINTS]: [
		{
			key: 'path',
			label: 'Endpoint',
			width: 'min-w-[16rem]',
			cell: (r) => ({ kind: 'mono', text: str(r.path) || pathOf(r.url), strong: true })
		},
		{
			key: 'host',
			label: 'Web asset',
			width: 'min-w-[10rem]',
			cell: (r) => ({ kind: 'mono', text: str(r.host) || hostOf(r.url) })
		},
		{
			key: 'status',
			label: 'Status',
			width: 'w-16',
			cell: (r) => ({ kind: 'status', code: num(r.status_code) })
		},
		{ key: 'type', label: 'Type', width: 'w-32', cell: (r) => text(r.content_type, true) },
		{
			key: 'params',
			label: 'Parameters',
			width: 'w-24',
			cell: (r) => (num(r.param_count) ? text(`${r.param_count}`, true) : { kind: 'empty' })
		}
	],
	[SurfaceDimension.SERVICES]: [
		{
			key: 'endpoint',
			label: 'Service',
			width: 'min-w-[11rem]',
			cell: (r) => ({ kind: 'mono', text: hostPort(str(r.ip), str(r.port)), strong: true })
		},
		{ key: 'service', label: 'Protocol', width: 'w-28', cell: (r) => text(r.service_name) },
		{ key: 'product', label: 'Product', width: 'min-w-[10rem]', cell: (r) => text(product(r)) },
		{
			key: 'title',
			label: 'Title',
			width: 'min-w-[8rem] max-w-[14rem]',
			cell: (r) => text(r.title, true)
		},
		{
			key: 'hosts',
			label: 'Web assets',
			width: 'min-w-[10rem]',
			cell: (r) => text(list(r.hosts).slice(0, 2).join(', '), true)
		}
	],
	[SurfaceDimension.IPS]: [
		{
			key: 'ip',
			label: 'Address',
			width: 'min-w-[9rem]',
			cell: (r) => ({ kind: 'mono', text: str(r.ip), strong: true })
		},
		{
			key: 'network',
			label: 'Network',
			width: 'min-w-[12rem]',
			cell: (r) => text([r.asn ? `AS${r.asn}` : '', str(r.asn_org)].filter(Boolean).join(' '))
		},
		{
			key: 'country',
			label: 'Country',
			width: 'w-20',
			cell: (r) => ({ kind: 'country', code: str(r.country) || null })
		},
		{
			key: 'ports',
			label: 'Ports',
			width: 'min-w-[7rem]',
			cell: (r) => text(list(r.ports).slice(0, 5).join(', '), true)
		},
		{
			key: 'hosts',
			label: 'Web assets',
			width: 'w-24',
			cell: (r) => (num(r.host_count) ? text(`${r.host_count}`, true) : { kind: 'empty' })
		}
	],
	[SurfaceDimension.VULNERABILITIES]: [
		{
			key: 'severity',
			label: 'Severity',
			width: 'w-24',
			cell: (r) => ({ kind: 'severity', value: str(r.severity) || null })
		},
		{
			key: 'check',
			label: 'Check',
			width: 'min-w-[14rem]',
			cell: (r) => text(r.template_name || r.template_id)
		},
		{
			key: 'host',
			label: 'Location',
			width: 'min-w-[12rem]',
			cell: (r) => ({ kind: 'mono', text: str(r.host) || hostOf(r.matched_at) })
		},
		{
			key: 'cve',
			label: 'CVE',
			width: 'w-36',
			cell: (r) =>
				list(r.cve_ids)[0] ? { kind: 'mono', text: list(r.cve_ids)[0] } : { kind: 'empty' }
		},
		{ key: 'kev', label: 'KEV', width: 'w-14', cell: (r) => ({ kind: 'kev', on: !!r.is_kev }) }
	],
	[SurfaceDimension.SOFTWARE]: [
		{
			key: 'severity',
			label: 'Severity',
			width: 'w-24',
			cell: (r) => ({ kind: 'severity', value: str(r.severity) || null })
		},
		{
			key: 'cve',
			label: 'CVE',
			width: 'w-36',
			cell: (r) => ({ kind: 'mono', text: str(r.cve), strong: true })
		},
		{
			key: 'product',
			label: 'Software',
			width: 'min-w-[10rem]',
			cell: (r) => text([str(r.product || r.name), str(r.version)].filter(Boolean).join(' '))
		},
		{
			key: 'host',
			label: 'Location',
			width: 'min-w-[12rem]',
			cell: (r) => ({ kind: 'mono', text: str(r.host) || str(r.ip) })
		},
		{
			key: 'evidence',
			label: 'Evidence',
			width: 'w-32',
			cell: (r) => ({ kind: 'evidence', value: str(r.evidence) || null })
		}
	]
};

/** What a row is called when a person points at it. */
export function rowLabel(dimension: string, row: BlockRow): string {
	switch (dimension) {
		case SurfaceDimension.WEB_ASSETS:
			return str(row.name);
		case SurfaceDimension.ENDPOINTS:
			return str(row.url);
		case SurfaceDimension.SERVICES:
			return hostPort(str(row.ip), str(row.port));
		case SurfaceDimension.IPS:
			return str(row.ip);
		case SurfaceDimension.VULNERABILITIES:
			return `${str(row.template_name || row.template_id)} on ${str(row.host) || hostOf(row.matched_at)}`;
		case SurfaceDimension.SOFTWARE:
			return `${str(row.cve)} on ${str(row.host) || str(row.ip)}`;
		default:
			return '';
	}
}

export function aboutRow(dimension: string, row: BlockRow): string {
	return `${dimension}${ABOUT_SEPARATOR}${rowLabel(dimension, row)}`;
}

/** The row's own sheet in the scan that recorded it. */
export function rowHref(dimension: string, row: BlockRow): string | null {
	const spec = surfaceSpec(dimension);
	if (!spec) return null;
	const scan = str(row._scan_id) || null;
	switch (dimension) {
		case SurfaceDimension.WEB_ASSETS:
			return ROUTES.results(spec.tab, scan, { [spec.sheetParam ?? 'asset']: str(row.name) });
		case SurfaceDimension.IPS:
			return ROUTES.surface(spec.tab, { [spec.sheetParam ?? 'ip']: str(row.ip) });
		case SurfaceDimension.VULNERABILITIES:
			return row._id
				? ROUTES.results(spec.tab, scan, { [spec.sheetParam ?? 'vuln']: str(row._id) })
				: null;
		case SurfaceDimension.ENDPOINTS:
			return ROUTES.results(spec.tab, scan, {
				[spec.queryParam]: exactToken('url', str(row.url)),
				...spec.rowView
			});
		case SurfaceDimension.SERVICES:
			return ROUTES.results(spec.tab, scan, {
				[spec.queryParam]: `${exactToken('ip', str(row.ip))} ${exactToken('port', str(row.port))}`
			});
		case SurfaceDimension.SOFTWARE:
			return ROUTES.results(spec.tab, scan, {
				[spec.queryParam]: `${exactToken('cve', str(row.cve))} ${exactToken('host', str(row.host))}`
			});
		default:
			return null;
	}
}

/** The dimension's page holding exactly the rows a block counted; none for an empty scope. */
export function blockHref(
	dimension: string | null,
	query: string | null,
	scopeValues: string[] | null,
	scanId: string | null = null
): string | null {
	const spec = dimension ? surfaceSpec(dimension) : undefined;
	if (!spec || scopeValues?.length === 0) return null;
	if (scanId) {
		const q = query ?? '';
		if (q.length > MAX_QUERY_LENGTH) return null;
		return ROUTES.scanTab(scanId, spec.tab, {
			...(q ? { [spec.queryParam]: q } : {}),
			...spec.rowView
		});
	}
	const clause = scopeValues?.length ? scopeClause(scopeValues) : '';
	const q = withClause(clause, query ?? '');
	if (q.length > MAX_QUERY_LENGTH) return null;
	return ROUTES.surface(spec.tab, { ...(q ? { [spec.queryParam]: q } : {}), ...spec.rowView });
}

export function groupQuery(blockQuery: string | null, groupQuery: string | null): string {
	if (!groupQuery) return blockQuery ?? '';
	return blockQuery ? `(${blockQuery}) and ${groupQuery}` : groupQuery;
}
