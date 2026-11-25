(() => {
    const sourceUrl = new URL("bem-sass.json", document.currentScript.src);
    const descriptions = {
        "main.scss": "Entry point: assembles the seven folders with @use.",
        abstracts: "Shared Sass variables for colors, borders and radius.",
        base: "Default styles scoped to this demo.",
        components: "The card block, its elements and its BEM modifiers.",
        layout: "Responsive layout for the card and the source explorer.",
        pages: "Annotations and source explorer styles specific to BEM Demo.",
        themes: "Default and warm colors used by the theme switcher.",
        vendors: "The adapter for the WKND theme’s global button styles.",
    };
    const files = fetch(sourceUrl).then(response => {
        if (!response.ok) throw new Error("Sass source unavailable");
        return response.json();
    });

    document.querySelectorAll("[data-bem-demo]:not([data-bem-ready])").forEach(demo => {
        demo.dataset.bemReady = "true";
        const card = demo.querySelector(".bem-card");
        const button = demo.querySelector("[data-bem-toggle]");
        const details = demo.querySelector("[data-bem-details]");
        const labels = new Map();
        demo.querySelectorAll("[data-bem-label]").forEach(element => {
            const label = document.createElement("code");
            label.className = "wknd-bem-label";
            element.before(label);
            labels.set(element, label);
        });
        const update = () => labels.forEach((label, element) => {
            label.textContent = Array.from(element.classList, name => "." + name).join(" ");
            label.hidden = element.hidden;
        });
        button.addEventListener("click", () => {
            const expanded = details.hidden;
            details.hidden = !expanded;
            card.classList.toggle("bem-card--expanded", expanded);
            button.setAttribute("aria-expanded", String(expanded));
            button.textContent = expanded ? "Hide details" : "Show details";
            update();
        });
        demo.querySelector("[data-bem-theme-select]").addEventListener("change", event => {
            demo.dataset.bemTheme = event.target.value;
        });
        const explorer = demo.querySelector("[data-bem-sass-files]");
        files.then(sources => {
            const ordered = ["main.scss", "abstracts", "base", "components", "layout", "pages", "themes", "vendors"];
            explorer.replaceChildren(...ordered.map(group => {
                const source = sources.find(file => file.path.split("/")[0] === group);
                const fold = document.createElement("details");
                const heading = document.createElement("summary");
                const description = document.createElement("p");
                const pre = document.createElement("pre");
                const code = document.createElement("code");
                heading.textContent = source.path;
                description.textContent = descriptions[group];
                code.textContent = source.contents;
                pre.tabIndex = 0;
                pre.append(code);
                fold.append(heading, description, pre);
                return fold;
            }));
        }).catch(() => { explorer.textContent = "The Sass source could not be loaded."; });
        update();
    });
})();
