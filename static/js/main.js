/**
 * main.js — Global JavaScript for AgentHire
 * Handles: mobile menu, flash message auto-dismiss, keyboard shortcuts
 */

document.addEventListener('DOMContentLoaded', () => {

  // ── Mobile Menu Toggle ───────────────────────────────────────────────────
  const menuBtn  = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const hamburger  = document.getElementById('hamburger-icon');
  const closeIcon  = document.getElementById('close-icon');

  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      const isOpen = !mobileMenu.classList.contains('hidden');
      mobileMenu.classList.toggle('hidden', isOpen);
      hamburger?.classList.toggle('hidden', !isOpen);
      closeIcon?.classList.toggle('hidden', isOpen);
    });
  }

  // ── Auto-dismiss flash messages ──────────────────────────────────────────
  const flashMessages = document.querySelectorAll('.flash-msg');
  flashMessages.forEach((msg) => {
    setTimeout(() => {
      msg.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
      msg.style.opacity = '0';
      msg.style.transform = 'translateY(-8px)';
      setTimeout(() => msg.remove(), 500);
    }, 5000);
  });

  // ── Auto-focus first empty input on forms ────────────────────────────────
  const forms = document.querySelectorAll('form');
  forms.forEach((form) => {
    const firstInput = form.querySelector(
      'input:not([type="hidden"]):not([type="submit"]):not([type="file"]), textarea'
    );
    if (firstInput && !firstInput.value) {
      firstInput.focus();
    }
  });

  // ── Enter key submits focused button ────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
      const activeForm = e.target.closest('form');
      if (activeForm) {
        const submitBtn = activeForm.querySelector('[type="submit"]');
        if (submitBtn && e.target.tagName !== 'BUTTON') {
          // Already handled by browser default
        }
      }
    }
  });

});
