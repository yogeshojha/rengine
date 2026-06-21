interface Piece {
	x: number;
	y: number;
	vx: number;
	vy: number;
	rot: number;
	vr: number;
	size: number;
	color: string;
	life: number;
}

function resolveColors(): string[] {
	const fallback = ['#0a0a0a', '#404040', '#737373', '#a3a3a3', '#d4d4d4'];
	if (typeof document === 'undefined') return fallback;
	const styles = getComputedStyle(document.documentElement);
	const accents = ['--chart-1', '--chart-2', '--chart-3']
		.map((v) => styles.getPropertyValue(v).trim())
		.filter(Boolean);
	const neutral = ['--foreground', '--muted-foreground', '--border']
		.map((v) => styles.getPropertyValue(v).trim())
		.filter(Boolean);
	const palette = [...neutral, ...accents];
	return palette.length ? palette : fallback;
}

export function fireConfetti(): void {
	if (typeof window === 'undefined' || typeof document === 'undefined') return;

	const canvas = document.createElement('canvas');
	canvas.style.cssText =
		'position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;';
	document.body.appendChild(canvas);

	const ctx = canvas.getContext('2d');
	if (!ctx) {
		canvas.remove();
		return;
	}

	const dpr = window.devicePixelRatio || 1;
	const w = window.innerWidth;
	const h = window.innerHeight;
	canvas.width = w * dpr;
	canvas.height = h * dpr;
	ctx.scale(dpr, dpr);

	const colors = resolveColors();
	const cx = w / 2;
	const cy = h * 0.38;
	const pieces: Piece[] = [];

	for (let i = 0; i < 120; i++) {
		const angle = Math.random() * Math.PI * 2;
		const speed = 4 + Math.random() * 9;
		pieces.push({
			x: cx + (Math.random() - 0.5) * 80,
			y: cy + (Math.random() - 0.5) * 40,
			vx: Math.cos(angle) * speed,
			vy: Math.sin(angle) * speed - 4,
			rot: Math.random() * Math.PI,
			vr: (Math.random() - 0.5) * 0.3,
			size: 5 + Math.random() * 6,
			color: colors[Math.floor(Math.random() * colors.length)],
			life: 1
		});
	}

	const gravity = 0.22;
	const drag = 0.99;
	let raf = 0;

	function frame() {
		if (!ctx) return;
		ctx.clearRect(0, 0, w, h);
		let alive = false;

		for (const p of pieces) {
			p.vy += gravity;
			p.vx *= drag;
			p.x += p.vx;
			p.y += p.vy;
			p.rot += p.vr;
			p.life -= 0.012;
			if (p.life <= 0 || p.y > h + 40) continue;
			alive = true;

			ctx.save();
			ctx.globalAlpha = Math.max(0, p.life);
			ctx.translate(p.x, p.y);
			ctx.rotate(p.rot);
			ctx.fillStyle = p.color;
			ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
			ctx.restore();
		}

		if (alive) {
			raf = requestAnimationFrame(frame);
		} else {
			cancelAnimationFrame(raf);
			canvas.remove();
		}
	}

	raf = requestAnimationFrame(frame);
}
