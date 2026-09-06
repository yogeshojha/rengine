import { SectionRole } from '$lib/config/reports';
import type { ReportTemplate, SectionCatalogEntry, SectionEntry } from '$lib/types/report';

/** What one report will contain, seeded from a template and changed for this report only. */
export class ReportPlan {
	catalog = $state<SectionCatalogEntry[]>([]);
	entries = $state<SectionEntry[]>([]);
	baseline = $state<SectionEntry[]>([]);

	spec(name: string) {
		return this.catalog.find((s) => s.name === name);
	}

	private rank(name: string) {
		const index = this.catalog.findIndex((s) => s.name === name);
		return index === -1 ? this.catalog.length : index;
	}

	get content() {
		return this.catalog.filter((s) => s.role !== SectionRole.FURNITURE);
	}

	get furniture() {
		return this.catalog.filter((s) => s.role === SectionRole.FURNITURE && this.enabled(s.name));
	}

	get enabledCount() {
		return this.entries.filter((e) => e.enabled).length;
	}

	get changed() {
		return JSON.stringify(this.entries) !== JSON.stringify(this.baseline);
	}

	enabled(name: string) {
		return this.entries.some((e) => e.section === name && e.enabled);
	}

	config(name: string): Record<string, unknown> {
		const entry = this.entries.find((e) => e.section === name);
		return { ...(this.spec(name)?.defaults ?? {}), ...(entry?.config ?? {}) };
	}

	/** Fields a section asks to surface at generate time rather than only in the builder. */
	launchFields(name: string) {
		return (this.spec(name)?.fields ?? []).filter((f) => f.launch);
	}

	changedFields(name: string) {
		const was = this.baseline.find((e) => e.section === name)?.config ?? {};
		const now = this.entries.find((e) => e.section === name)?.config ?? {};
		const keys = [...Object.keys(was), ...Object.keys(now)];
		return keys.filter(
			(key, index) =>
				keys.indexOf(key) === index && JSON.stringify(was[key]) !== JSON.stringify(now[key])
		);
	}

	seed(catalog: SectionCatalogEntry[], template: ReportTemplate | undefined) {
		this.catalog = catalog;
		const from = template?.sections?.length
			? template.sections.map((s) => ({ ...s, config: { ...s.config } }))
			: catalog
					.filter((s) => s.default_enabled)
					.map((s) => ({ section: s.name, enabled: true, title: '', config: {} }));
		this.entries = from;
		this.baseline = from.map((s) => ({ ...s, config: { ...s.config } }));
	}

	toggle(name: string) {
		const index = this.entries.findIndex((e) => e.section === name);
		if (index >= 0) {
			const next = [...this.entries];
			next[index] = { ...next[index], enabled: !next[index].enabled };
			this.entries = next;
			return;
		}
		// a section the template omitted takes the position its group implies
		const at = this.entries.findIndex((e) => this.rank(e.section) > this.rank(name));
		const entry: SectionEntry = { section: name, enabled: true, title: '', config: {} };
		this.entries =
			at === -1
				? [...this.entries, entry]
				: [...this.entries.slice(0, at), entry, ...this.entries.slice(at)];
	}

	setField(name: string, field: string, value: unknown) {
		const index = this.entries.findIndex((e) => e.section === name);
		if (index < 0) return;
		const next = [...this.entries];
		next[index] = { ...next[index], config: { ...next[index].config, [field]: value } };
		this.entries = next;
	}

	resetSection(name: string) {
		const was = this.baseline.find((e) => e.section === name);
		const index = this.entries.findIndex((e) => e.section === name);
		if (index < 0) return;
		const next = [...this.entries];
		next[index] = { ...next[index], config: { ...(was?.config ?? {}) } };
		this.entries = next;
	}

	reset() {
		this.entries = this.baseline.map((s) => ({ ...s, config: { ...s.config } }));
	}
}
