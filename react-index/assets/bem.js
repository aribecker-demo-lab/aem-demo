(() => {
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
        update();
    });
})();
