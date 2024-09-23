// Botón de volver
document.getElementById('back-btn').addEventListener('click', function() {
    window.history.back(); // Navega a la página anterior en el historial del navegador
});

// Botón de menú
document.getElementById('menu-toggle').addEventListener('click', function() {
    const sideMenu = document.getElementById('side-menu');
    sideMenu.classList.toggle('active');
});

// Botón de cerrar menú
document.getElementById('close-btn').addEventListener('click', function() {
    const sideMenu = document.getElementById('side-menu');
    sideMenu.classList.remove('active');
});
// test
// Pantallas Administrativas
document.addEventListener("DOMContentLoaded", function() {
    showScreen('login-screen');

    document.querySelector('.login-button').addEventListener('click', function() {
        showScreen('menu-screen');
    });

    document.querySelector('.menu-button').addEventListener('click', function() {
        showScreen('search-screen');
    });

    document.querySelector('.refresh-button').addEventListener('click', function() {
        alert('Refrescar');
    });
});

function showScreen(screenClass) {
    document.querySelectorAll('.login-screen, .menu-screen, .search-screen').forEach(function(screen) {
        screen.style.display = 'none';
    });
    document.querySelector('.' + screenClass).style.display = 'flex';
}

// Buscador de Jugadores
const players = [
    'Jugador 1',
    'Jugador 2',
    'Jugador 3',
    // Agrega más jugadores aquí
];

function filterPlayers() {
    const input = document.getElementById('searchInput').value.toLowerCase();
    const suggestions = document.getElementById('suggestions');
    suggestions.innerHTML = '';

    if (input.length === 0) {
        suggestions.style.display = 'none';
        return;
    }

    const filteredPlayers = players.filter(player => player.toLowerCase().includes(input));

    if (filteredPlayers.length > 0) {
        filteredPlayers.forEach(player => {
            const li = document.createElement('li');
            li.textContent = player;
            li.onclick = () => selectPlayer(player);
            suggestions.appendChild(li);
        });
        suggestions.style.display = 'block';
    } else {
        suggestions.style.display = 'none';
    }
}

function selectPlayer(playerName) {
    localStorage.setItem('selectedPlayer', playerName);
    window.location.href = `player_details.html?player=${encodeURIComponent(playerName)}`;
}

document.getElementById('searchInput').addEventListener('input', filterPlayers);

// Slider
function slide(n) {
    const container = document.querySelector('.slider-container');
    const slides = document.querySelectorAll('.slide');
    const currentIndex = [...slides].findIndex(slide => slide.offsetLeft === container.scrollLeft);
    const newIndex = currentIndex + n;

    if (newIndex >= 0 && newIndex < slides.length) {
        container.scrollTo({
            left: slides[newIndex].offsetLeft,
            behavior: 'smooth'
        });
    }
}


//MUESTRA EL RESULTADO DE LO CARGADO POR EL FORMULARIO
function mostrarResumen() {
    // Obtener los valores ingresados
    var nombre = document.getElementById('nombre').value;
    var apellido = document.getElementById('apellido').value;
    var dni = document.getElementById('dni').value;
    var sexo = document.getElementById('sexo').value;
    var torneo = document.getElementById('toreno').value;
    var categoria = document.getElementById('categoria').value;

    // Mostrar los valores en el resumen
    document.getElementById('resumen-nombre').innerText = "Nombre: " + nombre;
    document.getElementById('resumen-apellido').innerText = "Apellido: " + apellido;
    document.getElementById('resumen-dni').innerText = "DNI: " + dni;
    document.getElementById('resumen-sexo').innerText = "Sexo: " + sexo;
    document.getElementById('resumen-torneo').innerText = "Torneo: " + torneo;
    document.getElementById('resumen-categoria').innerText = "Categoría: " + categoria;

    // Mostrar el resumen y el botón de confirmar
    document.getElementById('resumen-datos').style.display = "block";
    document.getElementById('confirmar').style.display = "block";
}

function editarDatos() {
    // Ocultar el resumen para permitir la edición
    document.getElementById('resumen-datos').style.display = "none";
    document.getElementById('confirmar').style.display = "none";
}

