// Transition Overlay Management
class TransitionOverlay {
    constructor() {
        this.overlay = document.getElementById('transition-overlay');
        this.icon = document.getElementById('transition-icon');
        this.duration = 500; // milliseconds
        this.isShowing = Boolean(this.overlay && this.overlay.classList.contains('opacity-100'));
        this.isNavigating = false;
    }

    show() {
        if (!this.overlay) return;

        this.isShowing = true;
        this.overlay.classList.remove('pointer-events-none', 'opacity-0');
        this.overlay.classList.add('opacity-100');

        if (this.icon) {
            this.icon.classList.remove('translate-y-4');
            this.icon.classList.add('translate-y-0');
        }
    }

    hide() {
        if (!this.overlay) return;

        this.overlay.classList.remove('opacity-100');
        this.overlay.classList.add('opacity-0');

        if (this.icon) {
            this.icon.classList.remove('translate-y-0');
            this.icon.classList.add('translate-y-4');
        }

        setTimeout(() => {
            this.overlay.classList.add('pointer-events-none');
            this.isShowing = false;
        }, this.duration);
    }

    navigate(url, { replace = false, delay = this.duration } = {}) {
        if (!url || this.isNavigating) return;

        this.isNavigating = true;
        this.show();

        setTimeout(() => {
            if (replace) {
                window.location.replace(url);
                return;
            }
            window.location.href = url;
        }, Math.max(delay, 0));
    }
}

let transitionOverlay = null;

function directNavigate(url, options = {}) {
    if (!url) return;
    if (!transitionOverlay) {
        if (options.replace) {
            window.location.replace(url);
            return;
        }
        window.location.href = url;
        return;
    }
    transitionOverlay.navigate(url, options);
}

function setupRouteInterception() {
    document.addEventListener('click', (e) => {
        if (e.defaultPrevented || e.button !== 0) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

        const link = e.target.closest('a[href]');
        if (!link) return;
        if (link.classList.contains('no-transition')) return;
        if (link.hasAttribute('download') || link.hasAttribute('target')) return;

        const href = link.getAttribute('href');
        if (!href || href.startsWith('#')) return;

        const destination = new URL(link.href, window.location.origin);
        if (destination.origin !== window.location.origin) return;

        const isSameDocumentAnchor = destination.pathname === window.location.pathname &&
            destination.search === window.location.search &&
            destination.hash;
        if (isSameDocumentAnchor) return;

        e.preventDefault();
        directNavigate(destination.href);
    });

    document.addEventListener('submit', (e) => {
        const form = e.target;
        if (!form || !form.hasAttribute('data-transition')) return;

        e.preventDefault();
        if (transitionOverlay) transitionOverlay.show();
        setTimeout(() => form.submit(), transitionOverlay ? transitionOverlay.duration : 0);
    });
}

window.navigateWithTransition = (url, options = {}) => {
    directNavigate(url, options);
};

document.addEventListener('DOMContentLoaded', () => {
    transitionOverlay = new TransitionOverlay();
    setupRouteInterception();

    const hideOverlay = () => {
        if (!transitionOverlay) return;
        requestAnimationFrame(() => transitionOverlay.hide());
    };

    if (document.readyState === 'complete') {
        hideOverlay();
    } else {
        window.addEventListener('load', hideOverlay, { once: true });
    }
});

window.addEventListener('pageshow', (event) => {
    if (!event.persisted || !transitionOverlay) return;
    transitionOverlay.show();
    requestAnimationFrame(() => transitionOverlay.hide());
});
