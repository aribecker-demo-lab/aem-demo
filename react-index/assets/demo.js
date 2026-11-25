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
            label: "Text for item number " + ["one", "two", "three", "four", "five"][index],
        }));

        function Row({ item, index, reactKey, moved }) {
            const [savedLabel] = useState(item.label);
            const result = savedLabel === item.label ? "match" : "mismatch";
            return h("tr", { "data-moved-result": moved ? result : undefined },
                h("td", null, index),
                h("td", null, h("code", null, reactKey)),
                h("td", null, item.label),
                h("td", null, h("strong", null, savedLabel),
                    moved && h("span", { className: "wknd-react-move-result" },
                        result === "match" ? "State moved with item" : "State mismatch")));
        }

        function ListDemo({ stable }) {
            const [{ items, movedId }, setList] = useState({ items: initial, movedId: null });
            const [revision, setRevision] = useState(0);
            const rotate = () => setList(({ items: [first, ...rest] }) => ({
                items: [...rest, first], movedId: first.id,
            }));
            const reset = () => {
                setList({ items: initial, movedId: null });
                setRevision(value => value + 1);
            };
            return h(window.React.Fragment, null,
                h("h2", null, stable ? "Stable ID as key" : "Array index as key"),
                h("p", null, stable
                    ? "The row state follows each item when it moves."
                    : "After a move, the row state stays at the same index."),
                h("div", { className: "wknd-react-list-actions" },
                    h("button", { type: "button", onClick: rotate }, "Move first to end"),
                    h("button", { type: "button", onClick: reset }, "Reset")),
                h("div", { className: "wknd-react-list-table" },
                    h("table", { "aria-label": stable ? "Stable ID keys" : "Array index keys" },
                        h("thead", null, h("tr", null,
                            ["Array index", "React key", "Item text", "Row state (useState)"].map(label =>
                                h("th", { key: label, scope: "col" }, label)))),
                        h("tbody", { key: revision }, items.map((item, index) => {
                            const reactKey = stable ? item.id : index;
                            return h(Row, { key: reactKey, item, index, reactKey, moved: movedId === item.id });
                        })))));
        }

        panels.forEach(panel => {
            window.ReactDOM.createRoot(panel).render(h(ListDemo, { stable: panel.dataset.reactIndexDemo === "stable" }));
        });
    }

    load("react.production.min.js")
        .then(() => load("react-dom.production.min.js"))
        .then(mount)
        .catch(() => {
            panels.forEach(panel => { panel.querySelector("[role=status]").textContent = "React could not be loaded."; });
        });
})();
