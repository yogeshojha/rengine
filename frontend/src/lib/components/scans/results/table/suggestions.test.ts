import { describe, expect, it } from 'vitest';
import {
	dropSuggestion,
	holdsSuggestion,
	joinSuggestion,
	toolbarChips,
	valuesLabel,
	type FacetSpec,
	type SignalSpec
} from './filter-toolbar';
import {
	appliedLeadChips,
	clearLeadSearch,
	countedSuggestions,
	holdsNew,
	overlaps,
	removeToken,
	suggestionCandidates,
	tokenRule,
	withNew
} from './suggestions';

const noop = () => {};

describe('joining a lead onto the search', () => {
	it('sets the lead alone on an empty search', () => {
		expect(joinSuggestion('', 'is:kev')).toBe('is:kev');
		expect(joinSuggestion('  ', 'is:kev')).toBe('is:kev');
	});

	it('appends with and, parenthesising whichever side carries a top-level or', () => {
		expect(joinSuggestion('host:a', 'is:kev')).toBe('host:a and is:kev');
		expect(joinSuggestion('host:a', 'is:kev or is:cve')).toBe('host:a and (is:kev or is:cve)');
		expect(joinSuggestion('tech:nginx or tech:apache', 'status:500')).toBe(
			'(tech:nginx or tech:apache) and status:500'
		);
	});

	it('matches an applied lead as a whole clause, never a substring', () => {
		expect(holdsSuggestion('x and port:8080', 'port:80')).toBe(false);
		expect(dropSuggestion('x and port:8080', 'port:80')).toBe('x and port:8080');
		expect(holdsSuggestion('port:80 and x', 'port:80')).toBe(true);
		expect(dropSuggestion('port:80 and x', 'port:80')).toBe('x');
		expect(dropSuggestion('(tech:a or tech:b) and status:500', 'status:500')).toBe(
			'(tech:a or tech:b)'
		);
	});

	it('reads an applied lead back and removes it', () => {
		const search = joinSuggestion(joinSuggestion('', 'is:kev'), 'severity:critical');
		expect(holdsSuggestion(search, 'is:kev')).toBe(true);
		expect(holdsSuggestion(search, 'severity:critical')).toBe(true);
		expect(holdsSuggestion(search, 'severity:high')).toBe(false);
		expect(dropSuggestion(search, 'severity:critical')).toBe('is:kev');
		expect(dropSuggestion(search, 'is:kev')).toBe('severity:critical');
		expect(dropSuggestion('is:kev', 'is:kev')).toBe('');
	});

	it('clears every applied lead at once', () => {
		const leads = [
			{ query: 'is:kev', description: '' },
			{ query: 'cvss>=9', description: '' }
		];
		expect(clearLeadSearch(leads, 'is:kev and cvss>=9')).toBe('');
		expect(clearLeadSearch(leads, 'host:a and is:kev')).toBe('host:a');
	});

	it('toggles the is:new token', () => {
		expect(withNew('', true)).toBe('is:new');
		expect(withNew('is:new host:a', false)).toBe('host:a');
		expect(withNew('is:new', true)).toBe('is:new');
	});

	it('removes a negated or connected token without leaving a dangling word', () => {
		expect(holdsNew('not is:new')).toBe(false);
		expect(holdsNew('tech:a and is:new')).toBe(true);
		expect(withNew('not is:new', false)).toBe('');
		expect(withNew('tech:a or is:new', false)).toBe('tech:a');
		expect(withNew('is:new and tech:a', false)).toBe('tech:a');
		expect(removeToken('tech:a and not is:kev and is:cve', 'is:kev')).toBe('tech:a and is:cve');
	});
});

describe('suggestion candidates', () => {
	const leads = [
		{ query: 'is:kev', description: 'exploited', count: 8, capped: false },
		{ query: 'severity:critical', description: 'critical', count: 5, capped: false },
		{ query: 'is:new', description: 'new', count: 0, capped: false },
		{ query: 'tag:panel', description: 'panels', count: 21, capped: false }
	];

	it('drops applied, overlapping, empty and view-wide leads', () => {
		const overlapping = overlaps([[/\bseverity:/, true]]);
		const kept = suggestionCandidates(leads, 'is:kev', overlapping, 21).map((l) => l.query);
		expect(kept).toEqual([]);
	});

	it('keeps leads a click would narrow with', () => {
		const kept = suggestionCandidates(leads, '', () => false, 21).map((l) => l.query);
		expect(kept).toEqual(['is:kev', 'severity:critical']);
	});

	it('shows the lead count at rest and the joined count when only text is typed', () => {
		const counts = { counts: { 'host:a and is:kev': 3 }, capped: {} };
		const atRest = countedSuggestions(leads.slice(0, 2), '', true, counts, 21);
		expect(atRest.map((s) => s.count)).toEqual([8, 5]);
		const typed = countedSuggestions(leads.slice(0, 2), 'host:a', true, counts, 21);
		expect(typed.map((s) => s.count)).toEqual([3, null]);
		const narrowed = countedSuggestions(leads.slice(0, 2), 'host:a', false, counts, 21);
		expect(narrowed.map((s) => s.count)).toEqual([null, null]);
	});

	it('drops a counted lead that equals the view', () => {
		const counts = { counts: { 'host:a and is:kev': 4 }, capped: {} };
		expect(countedSuggestions(leads.slice(0, 1), 'host:a', true, counts, 4)).toEqual([]);
	});

	it('turns an applied lead into a removable chip', () => {
		let search = 'host:a and is:kev';
		const chips = appliedLeadChips(leads, search, (next) => (search = next));
		expect(chips.map((c) => c.label)).toEqual(['is:kev']);
		chips[0].onRemove();
		expect(search).toBe('host:a');
	});
});

describe('toolbar chips', () => {
	const facet: FacetSpec = {
		key: 'severity',
		label: 'Severity',
		options: [
			{ value: 'critical', label: 'Critical' },
			{ value: 'high', label: 'High' },
			{ value: 'medium', label: 'Medium' }
		],
		selected: ['critical', 'high', 'medium'],
		onChange: noop
	};
	const signals: SignalSpec[] = [
		{ key: 'kev', label: 'Known exploited', on: true, onToggle: noop },
		{ key: 'static', label: 'Hide static', on: true, quiet: true, onToggle: noop },
		{ key: 'cve', label: 'Has a CVE', on: false, onToggle: noop }
	];

	it('labels a facet with its option labels and folds the rest', () => {
		const chips = toolbarChips([facet], [], []);
		expect(chips).toHaveLength(1);
		expect(chips[0].values).toEqual(['Critical', 'High', 'Medium']);
		expect(valuesLabel(chips[0].values)).toBe('Critical, High +1');
	});

	it('shows an on signal, never a quiet or off one', () => {
		const chips = toolbarChips([], signals, [{ id: 'x', label: 'is:kev', onRemove: noop }]);
		expect(chips.map((c) => c.label)).toEqual(['Known exploited', 'is:kev']);
	});

	it('lets an applied query own the chip of the token it holds', () => {
		const tokened: SignalSpec[] = [{ ...signals[0], token: 'is:kev' }];
		const chips = toolbarChips([], tokened, [
			{ id: 'lead', label: 'is:kev and is:firm', mono: true, onRemove: noop }
		]);
		expect(chips.map((c) => c.label)).toEqual(['is:kev and is:firm']);
	});

	it('keeps the signal label when the applied query is the token alone', () => {
		const tokened: SignalSpec[] = [{ ...signals[0], token: 'is:kev' }];
		const chips = toolbarChips([], tokened, [
			{ id: 'lead', label: 'is:kev', mono: true, onRemove: noop }
		]);
		expect(chips.map((c) => c.label)).toEqual(['Known exploited']);
	});

	it('a token rule matches the token as a whole word', () => {
		const overlapping = overlaps([tokenRule('is:kev', true), tokenRule('is:new', false)]);
		expect(overlapping('is:kev and is:firm')).toBe(true);
		expect(overlapping('is:kevlar')).toBe(false);
		expect(overlapping('is:new')).toBe(false);
	});
});
