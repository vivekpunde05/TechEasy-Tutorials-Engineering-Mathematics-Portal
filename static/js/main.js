/**
 * TechEasy Tutorials - Engineering Mathematics Portal
 * Core Client JavaScript (Theme Switcher, Toasts, Video Modal, MathJax)
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Theme Switcher (Dark / Light Mode)
    const themeBtn = document.getElementById('themeToggleBtn');
    const savedTheme = localStorage.getItem('techeasy_theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('techeasy_theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        if (!themeBtn) return;
        themeBtn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
        themeBtn.setAttribute('title', `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`);
    }

    // 2. Auto-dismiss Toast Alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 400);
        }, 4500);
    });

    // 3. Mobile Menu Toggle
    const mobileBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.getElementById('navMenu');
    if (mobileBtn && navMenu) {
        mobileBtn.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            if (navMenu.classList.contains('active')) {
                navMenu.style.display = 'flex';
                navMenu.style.flexDirection = 'column';
                navMenu.style.position = 'absolute';
                navMenu.style.top = '72px';
                navMenu.style.left = '0';
                navMenu.style.right = '0';
                navMenu.style.background = 'var(--bg-card)';
                navMenu.style.padding = '20px';
                navMenu.style.boxShadow = 'var(--shadow-xl)';
            } else {
                navMenu.style.display = '';
            }
        });
    }

    // 4. Video Lecture Modal
    const videoModal = document.getElementById('videoPlayerModal');
    const videoIframe = document.getElementById('videoPlayerIframe');
    const modalTitle = document.getElementById('videoModalTitle');
    const modalClose = document.getElementById('videoModalClose');

    window.openVideoModal = function(youtubeId, title) {
        if (!videoModal || !videoIframe) return;
        videoIframe.src = `https://www.youtube.com/embed/${youtubeId}?autoplay=1&rel=0`;
        if (modalTitle) modalTitle.textContent = title || 'Engineering Mathematics Lecture';
        videoModal.classList.add('active');
    };

    window.closeVideoModal = function() {
        if (!videoModal || !videoIframe) return;
        videoIframe.src = '';
        videoModal.classList.remove('active');
    };

    if (modalClose) {
        modalClose.addEventListener('click', closeVideoModal);
    }
    if (videoModal) {
        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) closeVideoModal();
        });
    }

    // 5. Typeset MathJax
    window.renderMath = function() {
        if (window.MathJax && MathJax.typesetPromise) {
            MathJax.typesetPromise().catch((err) => console.log('MathJax error:', err));
        }
    };
    renderMath();

    // 6. Global Password Visibility Toggle
    const eyeIconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
    const eyeOffIconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>';

    window.togglePasswordVisibility = function(targetInputId, btnElement) {
        const input = document.getElementById(targetInputId);
        if (!input) return;
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        if (btnElement) {
            btnElement.innerHTML = isPassword ? eyeOffIconSvg : eyeIconSvg;
            btnElement.setAttribute('title', isPassword ? 'Hide password' : 'Show password');
            btnElement.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        }
    };
});
