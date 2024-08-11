//boton de volver
document.getElementById('back-btn').addEventListener('click', function() {
     window.history.back(); // Navega a la página anterior en el historial del navegador
});

  
document.getElementById('menu-toggle').addEventListener('click', function() {
    const sideMenu = document.getElementById('side-menu');
    sideMenu.classList.toggle('active');
});

document.getElementById('close-btn').addEventListener('click', function() {
    const sideMenu = document.getElementById('side-menu');
    sideMenu.classList.remove('active');
});

/*administrador*/
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


/*base de datos*/
const express = require('express');
const bodyParser = require('body-parser');
const multer = require('multer');
const mysql = require('mysql');

const app = express();
const port = 3000;

// Configuración de MySQL
const db = mysql.createConnection({
    host: 'localhost',
    user: ' c1342381_apur',
    password: 'ZIne61maza',
    database: 'c1342381_apur' // Nombre de tu base de datos
});

db.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Conectado a la base de datos MySQL');
});

// Configuración de multer para subida de archivos (foto)
const upload = multer({ dest: 'uploads/' });

// Middleware para procesar datos de formulario
app.use(bodyParser.urlencoded({ extended: true }));

// Endpoint para agregar nuevo jugador
app.post('/api/nuevo-jugador', upload.single('foto'), (req, res) => {
    const { nombre, apellido, dni, sexo } = req.body;
    const foto = req.file ? req.file.buffer : null; // Guarda la foto como un BLOB en la base de datos si se proporciona

    const nuevoJugador = {
        nombre,
        apellido,
        dni,
        sexo,
        foto
    };

    const sql = 'INSERT INTO jugador SET ?';

    db.query(sql, nuevoJugador, (err, result) => {
        if (err) {
            console.error('Error al agregar jugador:', err);
            res.status(500).send('Error al agregar jugador');
        } else {
            console.log('Jugador agregado correctamente');
            res.status(200).send('Jugador agregado correctamente');
        }
    });
});

app.listen(port, () => {
    console.log(`Servidor escuchando en http://localhost:${port}`);
});

/*BUSCADOR JUGADORES ADMIN*/
const searchInput = document.getElementById('searchInput');
const results = document.getElementById('results');

// Datos para mostrar en la búsqueda (pueden ser reemplazados por una llamada a una API, por ejemplo)
const items = [
    'Manzana',
    'Banana',
    'Cereza',
    'Dátil',
    'Higo',
    'Uva',
    'Kiwi',
    'Mango',
    'Naranja',
    'Pera'
];

// Filtra los resultados basados en la entrada del usuario
function filterResults(query) {
    results.innerHTML = ''; // Limpia los resultados anteriores
    if (query) {
        const filteredItems = items.filter(item => item.toLowerCase().includes(query.toLowerCase()));
        filteredItems.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            li.addEventListener('click', () => {
                searchInput.value = item;
                results.innerHTML = '';
            });
            results.appendChild(li);
        });
    }
}

// Maneja la entrada del usuario
searchInput.addEventListener('input', () => {
    filterResults(searchInput.value);
});


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
