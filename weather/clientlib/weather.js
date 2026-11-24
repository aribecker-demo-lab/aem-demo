(() => {
    const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

    async function showWeather(widget) {
        if (widget.dataset.weatherLoaded) return;
        widget.dataset.weatherLoaded = "true";
        const status = widget.querySelector("[data-weather-status]");
        try {
            const response = await fetch(widget.dataset.weatherUrl, {
                headers: { Accept: "application/json" },
                signal: AbortSignal.timeout(12000),
            });
            if (!response.ok) throw new Error("Weather unavailable");
            const weather = await response.json();
            const show = (name, value) => {
                widget.querySelector(`[data-weather-${name}]`).textContent = value;
            };
            show("temperature", `${number.format(weather.temperature)} °C`);
            show("condition", weather.condition);
            show("humidity", `${number.format(weather.humidity)}%`);
            show("wind", `${number.format(weather.wind)} km/h`);
            show("source", `Source: ${weather.source}`);
            widget.querySelector("[data-weather-result]").hidden = false;
            status.textContent = "";
            status.hidden = true;
        } catch (error) {
            status.textContent = "Current weather is temporarily unavailable.";
        }
    }

    function initialize() {
        document.querySelectorAll("[data-weather-url]").forEach(showWeather);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
        initialize();
    }
    document.addEventListener("foundation-contentloaded", initialize);
})();
