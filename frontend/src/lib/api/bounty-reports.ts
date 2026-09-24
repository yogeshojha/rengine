import {
	ALL_TAB,
	PAID_TAB,
	type BountyAccountSummary,
	type BountyReport,
	type BountyReportFilters,
	type ProgramReports,
	type ReportCounts
} from '$lib/types/bounty-report';
import { api } from './client';
import type { Paged } from './bounty-programs';

function filterParams(f: BountyReportFilters): URLSearchParams {
	const search = new URLSearchParams();
	for (const s of f.states) search.append('state', s);
	for (const p of f.programs) search.append('program', p);
	for (const s of f.severities) search.append('severity', s);
	if (f.q) search.set('q', f.q);
	if (f.from) search.set('submitted_from', f.from);
	if (f.to) search.set('submitted_to', f.to);
	return search;
}

export const bountyReportsApi = {
	async summary(platform: string): Promise<BountyAccountSummary> {
		return api.get<BountyAccountSummary>(`/bounty-reports/${platform}/summary`);
	},

	async programs(platform: string): Promise<ProgramReports[]> {
		return api.get<ProgramReports[]>(`/bounty-reports/${platform}/programs`);
	},

	async counts(platform: string, f: BountyReportFilters): Promise<ReportCounts> {
		return api.get<ReportCounts>(`/bounty-reports/${platform}/counts?${filterParams(f)}`);
	},

	async list(
		platform: string,
		f: BountyReportFilters,
		page: number,
		size: number
	): Promise<Paged<BountyReport>> {
		const search = filterParams(f);
		if (f.tab === PAID_TAB) search.set('paid', 'true');
		else if (f.tab !== ALL_TAB) search.set('stage', f.tab);
		search.set('sort', f.sort);
		search.set('order', f.order);
		search.set('page', String(page));
		search.set('size', String(size));
		return api.get<Paged<BountyReport>>(`/bounty-reports/${platform}?${search}`);
	},

	async sync(platform: string): Promise<void> {
		await api.post(`/bounty-reports/${platform}/sync`);
	}
};
