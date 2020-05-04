// Basic
new SimpleMDE({
	element: document.getElementById("demo1"),
	spellChecker: false,
});

// Autosaving
new SimpleMDE({
	element: document.getElementById("demo2"),
	spellChecker: false,
	autosave: {
		enabled: true,
		unique_id: "demo2",
	},
});