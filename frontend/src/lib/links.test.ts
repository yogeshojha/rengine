import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { parse } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';
import { sourceFiles } from './test-utils/source-files';

const ROOT = join(import.meta.dirname, '..');

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Node = any;

const GUARD_MODULE = '$lib/utilities/links';
const GUARDS = new Set(['externalHref', 'safeHref']);
const LINK_MODULES = [
	/^\$lib\/config\/routes$/,
	/(^|\/)scope-links$/,
	/^\$lib\/api\//,
	/^\$lib\/stores\/exports/
];
const LINK_ATTR = /^href$|Href$/;
const UNWRAP = new Set([
	'TSAsExpression',
	'TSNonNullExpression',
	'TSSatisfiesExpression',
	'ChainExpression'
]);
const PASSTHROUGH = new Set(['filter', 'slice', 'sort', 'toSorted', 'toReversed', 'reverse']);
const FLOATING = Symbol('floating');

type Owner = Node | null | typeof FLOATING;

type Binding = { fn: Owner } & (
	| { kind: 'import'; source: string; imported: string }
	| { kind: 'prop'; key: string | null }
	| { kind: 'value'; node: Node }
	| { kind: 'each'; collection: Node }
);

interface Scope {
	file: string;
	names: Map<string, Binding[]>;
	pushes: { name: string; at: Node; args: Node[] }[];
	owner: WeakMap<object, Node | null>;
}

const isFunction = (node: Node) => /Function/.test(node?.type ?? '');

function walk(node: Node, visit: (n: Node) => void, intoFunctions = true): void {
	if (!node || typeof node !== 'object') return;
	if (Array.isArray(node)) {
		for (const child of node) walk(child, visit, intoFunctions);
		return;
	}
	if (typeof node.type === 'string') visit(node);
	for (const [key, value] of Object.entries(node)) {
		if (key === 'parent' || key === 'metadata' || !value || typeof value !== 'object') continue;
		if (!intoFunctions && isFunction(value)) continue;
		walk(value, visit, intoFunctions);
	}
}

function annotate(node: Node, fn: Node | null, owner: WeakMap<object, Node | null>): void {
	if (!node || typeof node !== 'object') return;
	if (Array.isArray(node)) {
		for (const child of node) annotate(child, fn, owner);
		return;
	}
	owner.set(node, fn);
	const inner = isFunction(node) ? node : fn;
	for (const [key, value] of Object.entries(node))
		if (key !== 'parent' && key !== 'metadata' && value && typeof value === 'object')
			annotate(value, inner, owner);
}

function collect(file: string, ast: Node): Scope {
	const scope: Scope = { file, names: new Map(), pushes: [], owner: new WeakMap() };
	const add = (name: string, binding: Binding) =>
		scope.names.set(name, [...(scope.names.get(name) ?? []), binding]);
	const declare = (decl: Node, fn: Owner) => {
		if (decl.id.type === 'Identifier')
			return add(decl.id.name, { kind: 'value', node: decl.init, fn });
		const fromProps = decl.init?.type === 'CallExpression' && decl.init.callee.name === '$props';
		for (const p of decl.id.properties ?? decl.id.elements ?? []) {
			let target = p?.type === 'RestElement' ? p.argument : p?.type === 'Property' ? p.value : p;
			if (target?.type === 'AssignmentPattern') target = target.left;
			if (target?.type !== 'Identifier') continue;
			const key = p.type === 'Property' ? (p.key.name ?? p.key.value) : null;
			add(target.name, fromProps ? { kind: 'prop', key, fn } : { kind: 'value', node: null, fn });
		}
	};
	for (const script of [ast.instance, ast.module]) {
		if (!script) continue;
		annotate(script.content, null, scope.owner);
		const fn = (n: Node) => scope.owner.get(n) ?? null;
		walk(script.content, (n) => {
			if (n.type === 'ImportDeclaration')
				for (const spec of n.specifiers)
					add(spec.local.name, {
						kind: 'import',
						source: n.source.value,
						imported: spec.imported?.name ?? 'default',
						fn: null
					});
			else if (n.type === 'VariableDeclarator') declare(n, fn(n));
			else if (n.type === 'FunctionDeclaration' && n.id)
				add(n.id.name, { kind: 'value', node: n, fn: fn(n) });
			else if (n.type === 'AssignmentExpression' && n.left.type === 'Identifier')
				add(n.left.name, { kind: 'value', node: n.right, fn: FLOATING });
			else if (
				n.type === 'CallExpression' &&
				n.callee.type === 'MemberExpression' &&
				n.callee.object.type === 'Identifier' &&
				n.callee.property.name === 'push'
			)
				scope.pushes.push({ name: n.callee.object.name, at: n, args: n.arguments });
		});
	}
	walk(ast.fragment, (n) => {
		if (n.type === 'ConstTag') for (const decl of n.declaration.declarations) declare(decl, null);
		if (n.type === 'EachBlock' && n.context?.type === 'Identifier')
			add(n.context.name, { kind: 'each', collection: n.expression, fn: null });
	});
	return scope;
}

const modules = new Map<string, Resolver | null>();

function moduleResolver(from: string, source: string): Resolver | null {
	const base = source.startsWith('$lib/')
		? join(ROOT, 'lib', source.slice(5))
		: source.startsWith('.')
			? join(dirname(from), source)
			: null;
	if (!base) return null;
	const path = [`${base}.ts`, `${base}.svelte.ts`, join(base, 'index.ts'), base].find(
		(p) => p.endsWith('.ts') && existsSync(p)
	);
	if (!path) return null;
	if (!modules.has(path)) {
		modules.set(path, null);
		const ast = parse(`<script lang="ts">${readFileSync(path, 'utf8')}</script>`, {
			modern: true
		});
		modules.set(path, new Resolver(collect(path, ast)));
	}
	return modules.get(path) ?? null;
}

class Resolver {
	private active = new Set<Node>();
	constructor(private scope: Scope) {}

	private guarded(node: Node, fn: () => boolean): boolean {
		if (this.active.has(node)) return false;
		this.active.add(node);
		try {
			return fn();
		} finally {
			this.active.delete(node);
		}
	}

	/** The declarations `name` can refer to at `at`, innermost function first. */
	private pick(name: string, at: Node | null): Binding[] {
		const found = this.scope.names.get(name) ?? [];
		const floating = found.filter((b) => b.fn === FLOATING);
		let fn: Node | null = at ? (this.scope.owner.get(at) ?? null) : null;
		for (;;) {
			const here = found.filter((b) => b.fn === fn);
			if (here.length) return [...here, ...floating];
			if (fn === null) return floating;
			fn = this.scope.owner.get(fn) ?? null;
		}
	}

	private all(name: string, at: Node | null, check: (b: Binding) => boolean): boolean {
		const found = this.pick(name, at);
		return found.length > 0 && found.every(check);
	}

	private isLinkSource(b: Binding): boolean {
		if (b.kind !== 'import') return false;
		if (b.source === GUARD_MODULE) return GUARDS.has(b.imported);
		return LINK_MODULES.some((re) => re.test(b.source));
	}

	private foreign(b: Binding): Resolver | null {
		return b.kind === 'import' ? moduleResolver(this.scope.file, b.source) : null;
	}

	/** Every value a declaration holds, through the runes. */
	private values(node: Node): Node[] | null {
		if (!node) return null;
		while (UNWRAP.has(node.type)) node = node.expression;
		if (node.type === 'CallExpression') {
			const callee = node.callee;
			if (callee.type === 'Identifier' && (callee.name === '$derived' || callee.name === '$state'))
				return node.arguments.length ? [node.arguments[0]] : [{ type: 'Literal', value: null }];
			if (callee.object?.name === '$derived' && callee.property?.name === 'by')
				return this.returned(node.arguments[0]);
		}
		return [node];
	}

	private returned(fn: Node): Node[] | null {
		if (!isFunction(fn)) return null;
		if (fn.body.type !== 'BlockStatement') return [fn.body];
		const found: Node[] = [];
		walk(fn.body, (n) => n.type === 'ReturnStatement' && found.push(n.argument), false);
		return found.length ? found : null;
	}

	private every(nodes: Node[] | null, check: (n: Node) => boolean): boolean {
		return !!nodes && nodes.every((n) => !n || check(n));
	}

	private callable(node: Node, check: (n: Node) => boolean): boolean {
		return this.every(this.returned(node), check);
	}

	link(node: Node): boolean {
		return isFunction(node) ? this.callable(node, (r) => this.safe(r)) : this.safe(node);
	}

	safe(node: Node): boolean {
		if (!node) return false;
		while (UNWRAP.has(node.type)) node = node.expression;
		return this.guarded(node, () => {
			switch (node.type) {
				case 'Literal':
					return node.value === null || typeof node.value === 'string';
				case 'TemplateLiteral':
					return node.quasis[0].value.cooked !== '' || this.safe(node.expressions[0]);
				case 'Identifier':
					return node.name === 'undefined' || this.safeName(node.name, node);
				case 'ConditionalExpression':
					return this.safe(node.consequent) && this.safe(node.alternate);
				case 'LogicalExpression':
					return (node.operator === '&&' || this.safe(node.left)) && this.safe(node.right);
				case 'CallExpression':
					return this.safeCall(node);
				case 'MemberExpression':
					return this.safeMember(node, false);
				default:
					return false;
			}
		});
	}

	safeName(name: string, at: Node | null): boolean {
		return this.all(name, at, (b) => {
			if (b.kind === 'prop') return LINK_ATTR.test(b.key ?? '');
			if (b.kind === 'import')
				return this.isLinkSource(b) || !!this.foreign(b)?.safeName(b.imported, null);
			if (b.kind === 'each') return false;
			return this.every(this.values(b.node), (v) => this.safe(v));
		});
	}

	callableName(name: string, at: Node | null): boolean {
		return this.all(name, at, (b) => {
			if (b.kind === 'prop') return LINK_ATTR.test(b.key ?? '');
			if (b.kind === 'import')
				return this.isLinkSource(b) || !!this.foreign(b)?.callableName(b.imported, null);
			if (b.kind !== 'value') return false;
			return this.every(this.values(b.node), (v) => this.callable(v, (r) => this.safe(r)));
		});
	}

	private safeCall(node: Node): boolean {
		const callee = node.callee;
		if (callee.type === 'Identifier')
			return callee.name === 'String'
				? this.safe(node.arguments[0])
				: this.callableName(callee.name, callee);
		return callee.type === 'MemberExpression' && this.safeMember(callee, true);
	}

	private linkRoot(node: Node): boolean {
		while (
			UNWRAP.has(node.type) ||
			node.type === 'MemberExpression' ||
			node.type === 'CallExpression'
		)
			node = node.type === 'CallExpression' ? node.callee : (node.object ?? node.expression);
		if (node.type !== 'Identifier') return false;
		return this.guarded(node, () =>
			this.all(node.name, node, (b) => {
				if (this.isLinkSource(b)) return true;
				if (b.kind !== 'value') return false;
				return this.every(this.values(b.node), (v) => this.linkRoot(v));
			})
		);
	}

	private safeMember(node: Node, call: boolean): boolean {
		if (this.linkRoot(node.object)) return true;
		return (
			node.property.type === 'Identifier' && this.safeProp(node.object, node.property.name, call)
		);
	}

	/** The property `name` of every object `node` can be. */
	safeProp(node: Node, name: string, call: boolean): boolean {
		if (!node) return true;
		while (UNWRAP.has(node.type)) node = node.expression;
		const value = (v: Node) => (call ? this.callable(v, (r) => this.safe(r)) : this.safe(v));
		return this.guarded(node, () => {
			switch (node.type) {
				case 'ObjectExpression': {
					const prop = node.properties.find(
						(p: Node) => p.type === 'Property' && (p.key.name ?? p.key.value) === name
					);
					if (prop) return value(prop.value);
					return node.properties
						.filter((p: Node) => p.type === 'SpreadElement')
						.every((p: Node) => this.safeProp(p.argument, name, call));
				}
				case 'Identifier':
					return this.all(node.name, node, (b) => {
						if (b.kind === 'import')
							return this.isLinkSource(b) || !!this.foreign(b)?.exportProp(b.imported, name, call);
						if (b.kind === 'each') return this.safeElements(b.collection, name, call);
						if (b.kind !== 'value') return false;
						return this.every(this.values(b.node), (v) => this.safeProp(v, name, call));
					});
				case 'ConditionalExpression':
					return (
						this.safeProp(node.consequent, name, call) && this.safeProp(node.alternate, name, call)
					);
				case 'LogicalExpression':
					return this.safeProp(node.left, name, call) && this.safeProp(node.right, name, call);
				case 'Literal':
				case 'TemplateLiteral':
					return true;
				default:
					return false;
			}
		});
	}

	exportProp(exported: string, name: string, call: boolean): boolean {
		return this.safeProp({ type: 'Identifier', name: exported }, name, call);
	}

	/** The property `name` of every element of the array `node`. */
	private safeElements(node: Node, name: string, call: boolean): boolean {
		if (!node) return false;
		while (UNWRAP.has(node.type)) node = node.expression;
		return this.guarded(node, () => {
			switch (node.type) {
				case 'ArrayExpression':
					return node.elements.every((el: Node) =>
						el?.type === 'SpreadElement'
							? this.safeElements(el.argument, name, call)
							: this.safeProp(el, name, call)
					);
				case 'Identifier':
					return this.all(node.name, node, (b) => {
						if (b.kind !== 'value') return false;
						const pushed = this.scope.pushes
							.filter((p) => p.name === node.name && this.pick(p.name, p.at).includes(b))
							.flatMap((p) => p.args);
						return (
							this.every(this.values(b.node), (v) => this.safeElements(v, name, call)) &&
							pushed.every((arg) => this.safeProp(arg, name, call))
						);
					});
				case 'CallExpression': {
					const callee = node.callee;
					if (callee.type !== 'MemberExpression') return false;
					const method = callee.property.name;
					if (PASSTHROUGH.has(method)) return this.safeElements(callee.object, name, call);
					if (method === 'map')
						return this.callable(node.arguments[0], (r) => this.safeProp(r, name, call));
					return false;
				}
				case 'ConditionalExpression':
					return (
						this.safeElements(node.consequent, name, call) &&
						this.safeElements(node.alternate, name, call)
					);
				case 'LogicalExpression':
					return (
						this.safeElements(node.left, name, call) && this.safeElements(node.right, name, call)
					);
				default:
					return false;
			}
		});
	}
}

function offenders(file: string, source = readFileSync(file, 'utf8')): string[] {
	const ast = parse(source, { modern: true });
	const resolver = new Resolver(collect(file, ast));
	const name = file.slice(ROOT.length + 1);
	const found: string[] = [];
	walk(ast.fragment, (n) => {
		if (n.type !== 'Attribute' || !LINK_ATTR.test(n.name) || n.value === true) return;
		const parts = Array.isArray(n.value) ? n.value : [n.value];
		const head = parts.find((p: Node) => p.type !== 'Text' || p.data.trim());
		if (!head || head.type === 'Text') return;
		if (!resolver.link(head.expression))
			found.push(`${name}: ${n.name}=${source.slice(head.start, head.end).replace(/\s+/g, ' ')}`);
	});
	return found;
}

const FIXTURE = join(ROOT, 'lib', 'fixture.svelte');
const ROUTES_IMPORT = "import { ROUTES } from '$lib/config/routes';";
const GUARD_IMPORT = "import { externalHref } from '$lib/utilities/links';";
const script = (body: string) => `<script lang="ts">${body}</script>`;

describe('link attribute check', () => {
	it.each([
		`${script('let { row } = $props();')}<a href={row.url}>x</a>`,
		`${script('let { row } = $props(); let u = $derived(row.url);')}<a href={u}>x</a>`,
		`${script('let { url } = $props();')}<a href={url}>x</a>`,
		`${script('let { a } = $props();')}<a href={\`\${a}/x\`}>x</a>`,
		`${script('let { row } = $props();')}<Sheet openHref={row.url} />`,
		`${script('let { row } = $props();')}<a href=" {row.url}">x</a>`,
		`${script(`${ROUTES_IMPORT} let { items } = $props(); let rows = $derived(items.map((i) => ({ href: i.url })));`)}{#each rows as r}<a href={r.href}>x</a>{/each}`
	])('refuses %s', (source) => {
		expect(offenders(FIXTURE, source)).toHaveLength(1);
	});

	it.each([
		`${script(`${GUARD_IMPORT} let { row } = $props();`)}<a href={externalHref(row.url)}>x</a>`,
		`${script(`${ROUTES_IMPORT} let { items } = $props(); let rows = $derived(items.map((i) => ({ href: ROUTES.scan(i.id) })));`)}{#each rows as r}<a href={r.href}>x</a>{/each}`,
		`${script('let { href } = $props();')}<a {href}>x</a>`,
		'<a href="/scans">x</a><a href={`https://nvd.nist.gov/vuln/detail/${cve}`}>x</a>'
	])('accepts %s', (source) => {
		expect(offenders(FIXTURE, source)).toEqual([]);
	});
});

describe('links', () => {
	it('binds every link attribute to a route, a literal or the link guard', () => {
		expect(sourceFiles(ROOT, /\.svelte$/).flatMap((file) => offenders(file))).toEqual([]);
	});

	it('opens a window through openExternal alone', () => {
		const opened = sourceFiles(ROOT, /\.(svelte|ts)$/)
			.filter((path) => !path.endsWith('utilities/links.ts') && !path.endsWith('.test.ts'))
			.filter((path) => /\bwindow\.open\(/.test(readFileSync(path, 'utf8')))
			.map((path) => path.slice(ROOT.length + 1));
		expect(opened).toEqual([]);
	});
});
