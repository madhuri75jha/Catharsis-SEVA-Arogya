// Sidebar Management
let currentUserRole = null;
let currentUserProfile = null;

// Open sidebar (mobile)
function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

// Close sidebar (mobile)
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

// Fetch user profile and role
async function fetchUserProfile() {
    try {
        const response = await fetch('/api/v1/profile');
        if (!response.ok) {
            throw new Error('Failed to fetch user profile');
        }
        
        const data = await response.json();
        if (data.success) {
            currentUserProfile = data.profile;
            currentUserRole = data.profile.role;
            return data.profile;
        } else {
            throw new Error(data.error?.message || 'Failed to fetch profile');
        }
    } catch (error) {
        console.error('Error fetching user profile:', error);
        return null;
    }
}

// Render menu items returned by backend RBAC profile
function renderMenuItems(menuItems) {
    const menuContainer = document.getElementById('sidebar-menu');
    if (!menuContainer) return;

    const items = Array.isArray(menuItems) ? menuItems : [];
    const currentPath = window.location.pathname;

    let menuHTML = '<ul class="space-y-1">';

    items.forEach(item => {
        const path = item.route || item.path || '#';
        const label = item.label || 'Menu';
        const icon = item.icon || 'menu';
        const isActive = currentPath === path ||
                        (path !== '/' && currentPath.startsWith(path));

        menuHTML += `
            <li>
                <a href="${path}" 
                   class="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                       isActive 
                           ? 'bg-primary/10 text-primary' 
                           : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                   }">
                    <span class="material-symbols-outlined text-[20px]">${icon}</span>
                    <span class="text-sm font-medium">${label}</span>
                </a>
            </li>
        `;
    });
    
    menuHTML += '</ul>';
    menuContainer.innerHTML = menuHTML;
}

// Render user profile section
function renderUserProfile(profile) {
    const nameElement = document.getElementById('sidebar-user-name');
    const roleElement = document.getElementById('sidebar-user-role');
    
    if (nameElement && profile.name) {
        nameElement.textContent = profile.name;
    }
    
    if (roleElement && (profile.role_display || profile.role)) {
        roleElement.textContent = profile.role_display || profile.role;
    }
}

// Initialize sidebar
async function initializeSidebar() {
    const profile = await fetchUserProfile();
    
    if (profile) {
        renderMenuItems(profile.menu_items);
        renderUserProfile(profile);
    } else {
        renderMenuItems([]);
        
        const nameElement = document.getElementById('sidebar-user-name');
        const roleElement = document.getElementById('sidebar-user-role');
        
        if (nameElement) nameElement.textContent = 'User';
        if (roleElement) roleElement.textContent = 'Unknown';
    }
}

// Close sidebar on navigation (mobile)
window.addEventListener('popstate', () => {
    if (window.innerWidth < 768) {
        closeSidebar();
    }
});

// Close sidebar when clicking a link (mobile)
document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link && link.closest('#sidebar-menu') && window.innerWidth < 768) {
        // Small delay to allow navigation to start
        setTimeout(closeSidebar, 100);
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeSidebar);
