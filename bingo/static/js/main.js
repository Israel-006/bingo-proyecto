/* =========================================
   MAIN JS - Lógica de Interfaz y Tema
   ========================================= */

document.addEventListener('DOMContentLoaded', () => {
    const themeElement = document.getElementById('theme-element');
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');

    // 1. CARGAR PREFERENCIA GUARDADA
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    // 2. ESCUCHAR EL CLIC DEL INTERRUPTOR
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = themeElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // 3. FUNCIÓN PARA APLICAR EL TEMA
    function applyTheme(theme) {
        // Cambiamos el atributo en el <html> (Esto activa el CSS de Bootstrap y base.css)
        themeElement.setAttribute('data-bs-theme', theme);
        
        // Cambiamos el icono (Sol o Luna)
        if (theme === 'dark') {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            themeIcon.style.color = '#facc15'; // Color amarillo sol
        } else {
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            themeIcon.style.color = ''; // Color por defecto
        }
    }
});

// Lógica para cerrar alertas automáticamente después de 5 segundos
window.setTimeout(function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    });
}, 5000);