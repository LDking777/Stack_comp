// ========================================== //
// LÓGICA DEL LOGIN - REVENGE AI              //
// ========================================== //

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.querySelector('form');
    const submitBtn = document.querySelector('button[type="submit"]');

    if (loginForm) {
        loginForm.addEventListener('submit', () => {
            // Cambia el texto del botón y añade un icono de carga
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Entrando...';
            // Desactiva visualmente el botón para evitar doble clic
            submitBtn.classList.add('opacity-75', 'cursor-not-allowed');
            submitBtn.style.pointerEvents = 'none';
        });
    }
});