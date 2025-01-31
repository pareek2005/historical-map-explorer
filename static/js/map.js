let currentMarkers = [];

const map = L.map('map').setView([20, 0], 3);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

function formatYear(year) {
    return year < 0 ? Math.abs(year) + ' BCE' : year + ' CE';
}

function parseYear(yearStr) {
    if (yearStr.includes('BCE')) {
        return -parseInt(yearStr.replace(' BCE', ''));
    }
    return parseInt(yearStr.replace(' CE', ''));
}

function setTimePeriod(start, end) {
    document.getElementById('startYear').value = formatYear(start);
    document.getElementById('endYear').value = formatYear(end);
}

function clearMarkers() {
    currentMarkers.forEach(marker => map.removeLayer(marker));
    currentMarkers = [];
}

map.on('click', async function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    console.log('Click at:', lat, lng);
    
    clearMarkers();
    
    try {
        const startYear = document.getElementById('startYear').value;
        const endYear = document.getElementById('endYear').value;
        
        const response = await fetch(`/api/articles?lat=${lat}&lng=${lng}&startYear=${encodeURIComponent(startYear)}&endYear=${encodeURIComponent(endYear)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const articles = await response.json();
        console.log('Articles received:', articles);
        
        if (articles.length === 0) {
            const marker = L.marker([lat, lng]).addTo(map);
            marker.bindPopup(`
                <div class="historical-popup">
                    <h3>No Historical Events Found</h3>
                    <p>No notable historical events found in this area.</p>
                    <p>Coordinates: ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
                </div>
            `).openPopup();
            currentMarkers.push(marker);
        } else {
            articles.forEach(article => {
                const marker = L.marker([article.lat, article.lon]).addTo(map);
                marker.bindPopup(`
                    <div class="historical-popup">
                        <h3>${article.title}</h3>
                        <p>${article.extract}</p>
                        <p><strong>Distance:</strong> ${(article.distance/1000).toFixed(1)}km from clicked point</p>
                        <a href="${article.url}" target="_blank" rel="noopener noreferrer">Read more on Wikipedia</a>
                    </div>
                `);
                currentMarkers.push(marker);
            });
            currentMarkers[0].openPopup();
        }
    } catch (error) {
        console.error('Error:', error);
    }
});

document.getElementById('startYear').addEventListener('change', function() {
    const startYear = parseYear(this.value);
    const endYear = parseYear(document.getElementById('endYear').value);
    if (startYear > endYear) {
        alert('Start year cannot be later than end year');
        this.value = '3000 BCE';
    }
});

document.getElementById('endYear').addEventListener('change', function() {
    const startYear = parseYear(document.getElementById('startYear').value);
    const endYear = parseYear(this.value);
    if (endYear < startYear) {
        alert('End year cannot be earlier than start year');
        this.value = '2024 CE';
    }
});