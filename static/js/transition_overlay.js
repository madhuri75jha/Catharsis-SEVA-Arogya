// Transition Overlay Management
class TransitionOverlay {
    constructor() {
        this.overlay = document.getElementById('transition-overlay');
        this.icon = document.getElementById('transition-icon');
        this.isShowing = false;
        this.duration = 500; // milliseconds
    }

    show() {
        if (!this.overlay || this.isShowing) return;
        
        this.isShowing = true;
        
        // Make overlay visible
        this.overlay.classList.remove('pointer-events-none');
        this.overlay.classList.remove('opacity-0');
        this.overlay.classList.add('opacity-100');
        
        // Animate icon slide up
        if (this.icon) {
            this.icon.classList.remove('translate-y-4');
            this.icon.classList.add('translate-y-0');
        }
    }

    hide() {
        if (!this.overlay || !this.isShowing) return;
        
        // Fade out overlay
        this.overlay.classList.remove('opacity-100');
        this.overlay.classList.add('opacity-0');
        
        // Reset icon position
        if (this.icon) {
            this.icon.classList.remove('translate-y-0');
            this.icon.classList.add('translate-y-4');
        }
        
        // Remove pointer events after animation completes
        setTimeout(() => {
            this.overlay.classList.add('pointer-events-none');
            this.isShowing = false;
        }, this.duration);
    }

    showAndHide(duration = 800) {
        this.show();
        setTimeout(() => this.hide(), duration);
    }
}

// Global instance
let transitionOverlay = null;

// Setup route interception for navigation
function setupRouteInterception() {
    // Intercept all internal link clicks
    document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        
        // Only intercept internal links
        if (link && 
            link.href && 
            link.href.startsWith(window.location.origin) &&
            !link.hasAttribute('target') &&
            !link.hasAttribute('download') &&
            !link.classList.contains('no-transition')) {
            
            e.preventDefault();
            
            if (transitionOverlay) {
                transitionOverlay.show();
                
                // Navigate after showing overlay
                setTimeout(() => {
                    window.location.href = link.href;
                }, 300);
            } else {
                // Fallback if overlay not initialized
                window.location.href = link.href;
            }
        }
    });

    // Intercept form submissions that redirect
    document.addEventListener('submit', (e) => {
        const form = e.target;
        
        // Only intercept forms with data-transition attribute
        if (form && form.hasAttribute('data-transition')) {
            if (transitionOverlay) {
                transitionOverlay.show();
            }
        }
    });

    // Show overlay on page load, then hide
    if (transitionOverlay && document.readyState === 'complete') {
        transitionOverlay.showAndHide(400);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    transitionOverlay = new TransitionOverlay();
    setupRouteInterception();
    
    // Show and hide overlay on initial page load
    if (document.readyState === 'complete') {
        transitionOverlay.showAndHide(400);
    }
});

// Handle page load complete
window.addEventListener('load', () => {
    if (transitionOverlay && !transitionOverlay.isShowing) {
        transitionOverlay.showAndHide(400);
    }
});

// Handle browser back/forward navigation
window.addEventListener('pageshow', (event) => {
    if (event.persisted && transitionOverlay) {
        // Page was loaded from cache (back/forward button)
        transitionOverlay.showAndHide(400);
    }
});
