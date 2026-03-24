document.addEventListener('DOMContentLoaded', function () {
    console.log("Initializing splash screen...");
    // Create splash overlay
    var splash = document.createElement('div');
    splash.id = 'whe-splash';
    splash.innerHTML = 'Loading\u2026';
    document.body.appendChild(splash);

    // Poll until Bokeh has at least one document (app is rendered)
    var check = setInterval(function () {
        if (window.Bokeh && window.Bokeh.documents && window.Bokeh.documents.length > 0) {
            splash.classList.add('whe-splash-hide');
            setTimeout(function () {
                if (splash.parentNode) splash.parentNode.removeChild(splash);
            }, 500);
            clearInterval(check);
            console.log("Bokeh app detected, hiding splash screen.");
        }
    }, 100);
});