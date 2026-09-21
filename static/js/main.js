// InternTrack – Professional Client-Side UI Scripts

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Navigation Toggle
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navMenu = document.querySelector('.nav-menu');
    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('open');
        });
    }

    // 2. Alert Dismissal
    const closeButtons = document.querySelectorAll('.alert-close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 200);
            }
        });
    });

    // 3. Client-side File Validation for Resume Upload
    const resumeInputs = document.querySelectorAll('input[type="file"][name="resume"]');
    resumeInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const allowedExts = ['pdf', 'doc', 'docx'];
            const fileExt = file.name.split('.').pop().toLowerCase();
            const maxSize = 5 * 1024 * 1024; // 5 MB

            if (!allowedExts.includes(fileExt)) {
                alert(`Unsupported file format (.${fileExt}). Please select a PDF, DOC, or DOCX document.`);
                input.value = '';
                return;
            }

            if (file.size > maxSize) {
                alert(`File size exceeds 5 MB limit (${(file.size / (1024*1024)).toFixed(2)} MB). Please choose a smaller document.`);
                input.value = '';
                return;
            }
        });
    });

    // 4. Confirm Delete & Destructive Action Handlers
    const confirmForms = document.querySelectorAll('.form-confirm-action');
    confirmForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const promptMsg = form.getAttribute('data-confirm-message') || "Are you sure you want to proceed with this action?";
            const confirmed = confirm(promptMsg);
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});
