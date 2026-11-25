(() => {
    const script = document.currentScript;
    const panels = [...document.querySelectorAll("[data-react-index-demo]:not([data-react-index-mounted])")];
    if (!panels.length) return;
    panels.forEach(panel => { panel.dataset.reactIndexMounted = "true"; });

    const base = new URL(".", script.src);
    const load = (name) => new Promise((resolve, reject) => {
        const dependency = document.createElement("script");
        dependency.src = new URL("vendor/" + name, base);
        dependency.onload = resolve;
        dependency.onerror = reject;
        document.head.append(dependency);
    });

    function mount() {
        const { createElement: h, useState } = window.React;
        const initial = Array.from({ length: 5 }, (_, index) => ({
            id: "item-" + (index + 1),
            label: "Elemento número " + ["uno", "dos", "tres", "cuatro", "cinco"][index],
        }));

        function Row({ item }) {
            const [savedLabel] = useState(item.label);
            return h("li", null,
                h("strong", null, savedLabel),
                h("span", null, "Elemento actual del array: " + item.label));
        }

        function ListDemo({ stable }) {
            const [items, setItems] = useState(initial);
            const [revision, setRevision] = useState(0);
            const rotate = () => setItems(([first, ...rest]) => [...rest, first]);
            const reset = () => {
                setItems(initial);
                setRevision(value => value + 1);
            };
            return h(window.React.Fragment, null,
                h("h2", null, stable ? "Clave por ID estable" : "Clave por índice del array"),
                h("p", null, stable
                    ? "Cada fila conserva su estado al moverse porque su clave pertenece al elemento."
                    : "El texto en negrita es el estado inicial de la fila. Al mover elementos, React conserva ese estado en la misma posición."),
                h("button", { type: "button", onClick: rotate }, "Mover el primero al final"),
                h("button", { type: "button", onClick: reset }, "Restablecer"),
                h("p", { className: "wknd-react-list-order", "aria-live": "polite" },
                    "Orden del array: " + items.map(item => item.label).join(" → ")),
                h("ol", { key: revision }, items.map((item, index) =>
                    h(Row, { key: stable ? item.id : index, item }))));
        }

        panels.forEach(panel => {
            window.ReactDOM.createRoot(panel).render(h(ListDemo, { stable: panel.dataset.reactIndexDemo === "stable" }));
        });
    }

    load("react.production.min.js")
        .then(() => load("react-dom.production.min.js"))
        .then(mount)
        .catch(() => {
            panels.forEach(panel => { panel.querySelector("[role=status]").textContent = "No se pudo cargar React."; });
        });
})();
