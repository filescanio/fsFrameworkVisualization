document.addEventListener('DOMContentLoaded', () => {
    // --- Get Elements ---
    const scatterCanvas = document.getElementById('landscapeChart');
    const radarCanvas = document.getElementById('radarChart');
    const useCaseSelect = document.getElementById('use-case-select');
    const sliders = document.querySelectorAll('.kpi-slider');
    const radarVendorSelector = document.getElementById('radar-vendor-selector');

    // --- Basic Element Check ---
    if (!scatterCanvas || !radarCanvas || !useCaseSelect || !radarVendorSelector || sliders.length !== kpiKeys.length ) {
        console.error('Required elements not found or mismatch.');
        if(document.body) document.body.innerHTML = '<p style="color: red;">Error: Could not initialize application components.</p>';
        return;
    }

    const scatterCtx = scatterCanvas.getContext('2d');
    const radarCtx = radarCanvas.getContext('2d');
    let landscapeChart;
    let radarChart;
    let allRadarDatasets = []; // Store all fetched radar datasets globally

    // --- Chart Configurations ---
    const scatterChartOptions = {
        responsive: true, maintainAspectRatio: false,
        layout: { padding: { top: 45, right: 45, bottom: 10, left: 10 } }, // Keep padding
        scales: {
            x: { type: 'linear', position: 'bottom', title: { display: true, text: axisLabels.x }, min: 0, max: 100 },
            y: { type: 'linear', position: 'left', title: { display: true, text: axisLabels.y }, min: 0, max: 100 }
        },
        plugins: {
            tooltip: { callbacks: { label: function(context) { const dp = context.raw; let lines = []; const dateStr = dp.test_date !== 'N/A' ? ` (${dp.test_date})` : ''; lines.push(`${dp.vendor || 'Vendor'}${dateStr}:`); lines.push(`  (${dp.x.toFixed(1)}%, ${dp.y.toFixed(1)}%)`); let m = []; if (dp.fp_rate !== 'N/A') m.push(`FP: ${dp.fp_rate}%`); if (dp.fn_rate !== 'N/A') m.push(`FN: ${dp.fn_rate}%`); if (dp.avg_speed !== 'N/A') m.push(`Speed: ${dp.avg_speed}s`); if (m.length > 0) { lines.push(`  ${m.join(' | ')}`); } return lines; } } },
            legend: { display: true, position: 'bottom', labels: { usePointStyle: true } },
            title: { display: true, text: 'Quadrant View (Weighted)' },
            datalabels: { anchor: 'end', align: (ctx) => { const p=ctx.dataset.data[ctx.dataIndex]; if(!p) return 'top'; if(p.y > 90) return 'bottom'; if(p.x > 90) return 'left'; return 'top';}, offset: 6, clamp: true, formatter: (v, ctx) => ctx.dataset.data[ctx.dataIndex]?.vendor || null, font: { size: 12, weight: 'bold' }, color: '#444' }
        }
    };
    const radarChartOptions = {
         responsive: true, maintainAspectRatio: false,
         scales: { r: { min: 0, max: 10, ticks: { stepSize: 2 }, pointLabels: { font: { size: 11 } } } },
         plugins: {
            tooltip: { callbacks: { label: function(context) { let l=context.dataset.label||''; if(l){l+=': ';} if(context.parsed.r!==null){l+=context.parsed.r.toFixed(1);} return l; } } },
            legend: { display: false },
            title: { display: true, text: 'Overall KPI Profile (Raw Scores 0-10)' },
            datalabels: { display: false }
         }
    };

    // --- Helper: Debounce ---
    function debounce(func, wait) { let timeout; return function executedFunction(...args) { const later = () => { clearTimeout(timeout); func(...args); }; clearTimeout(timeout); timeout = setTimeout(later, wait); }; }

    // --- Populate Radar Vendor Checkboxes ---
    function populateRadarVendorSelector() {
        radarVendorSelector.innerHTML = '<h5>Show Vendors on Radar:</h5>'; // Clear previous & add title
        if (!allRadarDatasets || allRadarDatasets.length === 0) {
             radarVendorSelector.innerHTML += '<p>No vendor data for radar.</p>';
             return;
        }

        allRadarDatasets.forEach((dataset, index) => {
            const vendorName = dataset.label;
            const color = dataset.borderColor;

            const itemDiv = document.createElement('div');
            itemDiv.classList.add('vendor-checkbox-item');

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `radar-vendor-${index}`;
            checkbox.value = vendorName;
            checkbox.checked = !dataset.hidden; // Initialize based on current state
            checkbox.dataset.index = index;

            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.style.cursor = 'pointer';

            const swatch = document.createElement('span');
            swatch.classList.add('color-swatch');
            swatch.style.backgroundColor = color;

            label.appendChild(swatch);
            label.appendChild(document.createTextNode(` ${vendorName}`));

            itemDiv.appendChild(checkbox);
            itemDiv.appendChild(label);
            radarVendorSelector.appendChild(itemDiv);

            checkbox.addEventListener('change', (event) => {
                 const idx = parseInt(event.target.dataset.index, 10);
                 if (!isNaN(idx) && allRadarDatasets[idx]) {
                    allRadarDatasets[idx].hidden = !event.target.checked; // Update stored state
                    if (radarChart) {
                        // Update live chart visibility
                        radarChart.setDatasetVisibility(idx, event.target.checked);
                        radarChart.update('none');
                    }
                 }
            });
        });
    }

    // --- Core Update Logic ---
    async function updateScatterChart() {
        const params = new URLSearchParams();
        kpiKeys.forEach(key => { const slider=document.getElementById(key); if (slider){ params.append(key, slider.value);}});
        try {
            const response = await fetch(`/api/data?${params.toString()}`);
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`);}
            const datasets = await response.json();
            if (!Array.isArray(datasets)) { throw new Error("Invalid data format received.");}
            const chartTitle = useCaseSelect.value==='Custom'?'Quadrant View (Custom Weights)':`Quadrant View (${useCaseSelect.value})`;
            if(landscapeChart){ landscapeChart.data.datasets=datasets; landscapeChart.options.plugins.title.text=chartTitle; landscapeChart.update('none');}
            else{ Chart.register(ChartDataLabels); landscapeChart=new Chart(scatterCtx, {type:'scatter', data:{datasets:datasets}, options:scatterChartOptions}); landscapeChart.options.plugins.title.text=chartTitle; landscapeChart.update();}
        } catch(error){ console.error('Error fetching/updating scatter:', error); if(scatterCanvas?.parentElement){scatterCanvas.parentElement.innerHTML='<p style="color: red;">Error loading scatter data.</p>';}}
    }

    async function updateRadarChart() {
         try {
            const response = await fetch(`/api/rawscores`);
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            const radarData = await response.json();
            if (!radarData || !Array.isArray(radarData.datasets) || !Array.isArray(radarData.labels)) { throw new Error("Invalid radar data format."); }

            allRadarDatasets = radarData.datasets.map(ds => ({...ds, hidden: false })); // Store & ensure all visible initially
            populateRadarVendorSelector();

             if (radarChart) {
                 radarChart.data.labels = radarData.labels;
                 radarChart.data.datasets = allRadarDatasets;
                 radarChart.update(); // Full update
             } else {
                 radarChart = new Chart(radarCtx, {
                     type: 'radar',
                     data: { labels: radarData.labels, datasets: allRadarDatasets },
                     options: radarChartOptions
                 });
             }
         } catch (error) {
             console.error('Error fetching or updating radar chart:', error);
              if (radarCanvas && radarCanvas.parentElement) { radarCanvas.parentElement.innerHTML = '<p style="color: red;">Error loading radar chart data.</p>';}
         }
    }

    const debouncedUpdateScatterChart = debounce(updateScatterChart, 250);

    // --- Event Listeners ---
    useCaseSelect.addEventListener('change', (event) => {
        const selectedPreset = event.target.value;
        if (selectedPreset !== 'Custom' && weightProfiles[selectedPreset]) {
            const presetWeights = weightProfiles[selectedPreset];
            sliders.forEach(slider => {
                const kpiKey = slider.id;
                const newValue = presetWeights[kpiKey] !== undefined ? presetWeights[kpiKey] : 5;
                slider.value = newValue;
                const valueDisplay = document.getElementById(`${kpiKey}-value`);
                if (valueDisplay) { valueDisplay.textContent = newValue; }
            });
            updateScatterChart(); // Only scatter updates based on weights
        }
    });
    sliders.forEach(slider => {
        const valueDisplay = document.getElementById(`${slider.id}-value`);
        slider.addEventListener('input', () => {
            if (valueDisplay) { valueDisplay.textContent = slider.value; }
            useCaseSelect.value = 'Custom';
            debouncedUpdateScatterChart(); // Only scatter updates based on weights
        });
    });

    // --- Initial Load ---
    updateScatterChart();
    updateRadarChart();

});