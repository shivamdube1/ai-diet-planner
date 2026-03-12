/* NutriAI — Main JavaScript */

document.addEventListener('DOMContentLoaded', function () {

    // ── Smooth Scroll for Anchor Links ──
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', e => {
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ── Scroll-triggered Fade In ──
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.how-card, .benefit-item, .metric-card').forEach(el => {
        el.classList.add('fade-on-scroll');
        observer.observe(el);
    });

    // ── Tooltip Initialization ──
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));

    // ── Form Validation Highlight ──
    const requiredInputs = document.querySelectorAll('.q-input[required]');
    requiredInputs.forEach(input => {
        input.addEventListener('blur', () => {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
            } else {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
            }
        });
    });

    // ── Auto-collapse Navbar on Mobile Link Click ──
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (navbarCollapse.classList.contains('show')) {
                bootstrap.Collapse.getInstance(navbarCollapse)?.hide();
            }
        });
    });

    // ── Number Input Formatters ──
    document.querySelectorAll('input[type="number"]').forEach(input => {
        input.addEventListener('wheel', e => e.preventDefault()); // Prevent scroll-to-change
    });

    // ── Quick BMI Calculator (for homepage if present) ──
    const bmiForm = document.getElementById('quickBmiForm');
    if (bmiForm) {
        bmiForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const weight = parseFloat(document.getElementById('quickWeight').value);
            const height = parseFloat(document.getElementById('quickHeight').value);
            if (!weight || !height) return;

            try {
                const res = await fetch('/api/bmi-check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ weight, height })
                });
                const data = await res.json();
                if (data.bmi) {
                    document.getElementById('bmiResult').textContent = `BMI: ${data.bmi} (${data.category})`;
                    document.getElementById('bmiResult').style.display = 'block';
                }
            } catch (err) {
                console.error('BMI check error:', err);
            }
        });
    }

});

// ── Fade-on-Scroll CSS injection ──
const style = document.createElement('style');
style.textContent = `
    .fade-on-scroll {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.5s ease, transform 0.5s ease;
    }
    .fade-on-scroll.visible {
        opacity: 1;
        transform: translateY(0);
    }
`;
document.head.appendChild(style);

// ── Utility: Format numbers with commas ──
function formatNumber(num) {
    return new Intl.NumberFormat('en-IN').format(num);
}

// ── Utility: Debounce ──
function debounce(fn, delay) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), delay);
    };
}
