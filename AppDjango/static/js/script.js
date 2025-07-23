document.addEventListener('DOMContentLoaded', function () {
  // DESCARGAR FIXTURE Y RESULTADOS
  const toggleDescarga = document.getElementById('toggle-descarga');
  const formDescarga = document.getElementById('form-descarga');

  function toggleFormularioDescarga() {
    if (formDescarga.classList.contains('visible')) {
      formDescarga.classList.remove('visible');
      formDescarga.classList.add('hidden');
    } else {
      formDescarga.classList.remove('hidden');
      formDescarga.classList.add('visible');
    }
  }

  if (toggleDescarga && formDescarga) {
    toggleDescarga.addEventListener('click', toggleFormularioDescarga);
  }

  // CREAR TORNEO
  const toggleCrear = document.getElementById('toggle-crear');
  const formCrear = document.getElementById('form-crear');

  function toggleFormularioCrear() {
    if (formCrear.classList.contains('visible')) {
      formCrear.classList.remove('visible');
      formCrear.classList.add('hidden');
    } else {
      formCrear.classList.remove('hidden');
      formCrear.classList.add('visible');
    }
  }

  if (toggleCrear && formCrear) {
    toggleCrear.addEventListener('click', toggleFormularioCrear);
  }

  // Evitar que el clic en el botón CREAR dispare el toggle
    const btnCrearTorneo = document.getElementById('btnCrearTorneo');
    if (btnCrearTorneo) {
    btnCrearTorneo.addEventListener('click', function (e) {
        e.stopPropagation();  // ✋ Evita que el clic se propague al contenedor
    });
    }
});


document.addEventListener('DOMContentLoaded', function () {

    const menuToggle = document.getElementById('menu-toggle');
    const closeBtn = document.getElementById('close-btn');
    const sideMenu = document.getElementById('side-menu');
    const btn = document.getElementById('scrollToTop');

    if(btn) {
        btn.addEventListener('click', () => {
            document.body.scrollTo({ top: 0, behavior: 'smooth'})
        })
    }

    // Abre menú hamburguesa
    if (menuToggle && sideMenu) {
        menuToggle.addEventListener('click', function () {
        sideMenu.classList.toggle('active');
        });
    }
    // Cierra menú hamburguesa
    if (closeBtn && sideMenu) {
        closeBtn.addEventListener('click', function () {
        sideMenu.classList.remove('active');
        });
    }
    // Cierra el menú cuando se seleccióna un título
    const sideMenuLinks = document.querySelectorAll('#side-menu a');
    sideMenuLinks.forEach(link => {
        link.addEventListener('click', function () {
        console.log('Clic en enlace del menú');
        if (sideMenu) {
            sideMenu.classList.remove('active');
        }
        });
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const filtroToggle = document.getElementById('filtro-toggle');
    const filtroClose = document.getElementById('filtro-close');
    const filtroCaja = document.getElementById('filtro-caja');

    // Mostrar caja de filtros
    if (filtroToggle && filtroCaja) {
        filtroToggle.addEventListener('click', function () {
            filtroCaja.classList.add('active');
        });
    }

    // Cerrar caja de filtros
    if (filtroClose && filtroCaja) {
        filtroClose.addEventListener('click', function () {
            filtroCaja.classList.remove('active');
        });
    }

    // Cierra al hacer clic en el botón de búsqueda
    const botonesBuscar = document.querySelectorAll('.cerrar-filtro-btn');
    botonesBuscar.forEach(btn => {
        btn.addEventListener('click', function () {
            filtroCaja.classList.remove('active');
        });
    });
});

// Botón de volver
// document.getElementById('back-btn').addEventListener('click', function() {
//     window.history.back(); // Navega a la página anterior en el historial del navegador
// });

// Botón de menú
// document.getElementById('menu-toggle').addEventListener('click', function() {
//     const sideMenu = document.getElementById('side-menu');
//     sideMenu.classList.toggle('active');
// });

// Botón de cerrar menú
// document.getElementById('close-btn').addEventListener('click', function() {
//     const sideMenu = document.getElementById('side-menu');
//     sideMenu.classList.remove('active');
// });
// test
// Pantallas Administrativas
// (login-screen, menu-screen, search-screen) NO EXISTEN EN EL HTML, SE COMENTA EL CODIGO PARA EVITAR FALLAS
// document.addEventListener("DOMContentLoaded", function() {
//     showScreen('login-screen');

//     document.querySelector('.login-button').addEventListener('click', function() {
//         showScreen('menu-screen');
//     });

//     document.querySelector('.menu-button').addEventListener('click', function() {
//         showScreen('search-screen');
//     });

//     document.querySelector('.refresh-button').addEventListener('click', function() {
//         alert('Refrescar');
//     });
// });

// function showScreen(screenClass) {
//     document.querySelectorAll('.login-screen, .menu-screen, .search-screen').forEach(function(screen) {
//         screen.style.display = 'none';
//     });
//     document.querySelector('.' + screenClass).style.display = 'flex';
// }

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

// document.getElementById('searchInput').addEventListener('input', filterPlayers);

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

function agregarFila() {
    const table = document.getElementById('partidosTable');
    const row = table.insertRow();
    row.innerHTML = `
        <td>
            <select name="jugador1[]" class="form-select" onchange="actualizarOpciones(this)">
                {% for jugador in jugadores_seleccionados %}
                    <option value="{{ jugador.id }}">{{ jugador.apellido }}, {{ jugador.nombre }}</option>
                {% endfor %}
            </select>
        </td>
        <td>VS</td>
        <td>
            <select name="jugador2[]" class="form-select">
                {% for jugador in jugadores_seleccionados %}
                    <option value="{{ jugador.id }}">{{ jugador.apellido }}, {{ jugador.nombre }}</option>
                {% endfor %}
            </select>
        </td>
        <td><input type="date" name="fecha[]" class="form-control"></td>
        <td><input type="time" name="hora[]" class="form-control"></td>
        <td>
            <button type="button" class="btn btn-danger" onclick="eliminarFila(this)">Eliminar</button>
        </td>
    `;
}

function actualizarOpciones(select) {
    const currentRow = select.closest('tr');
    const jugador1Value = select.value;

    const jugador2Select = currentRow.querySelector('select[name="jugador2[]"]');
    const options = jugador2Select.options;

    for (let i = 0; i < options.length; i++) {
        if (options[i].value === jugador1Value) {
            options[i].disabled = true;
        } else {
            options[i].disabled = false;
        }
    }
}
