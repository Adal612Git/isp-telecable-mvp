const ENV = window.__ENV__ || {};

const endpoints = {
  facturacion: ENV.VITE_API_FACTURACION_URL || "http://localhost:8002",
  pagos: ENV.VITE_API_PAGOS_URL || "http://localhost:8003",
  reportes: ENV.VITE_API_REPORTES_URL || "http://localhost:8007"
};

function selectPanel(id) {
  document.querySelectorAll("nav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.section === id);
  });
  document.querySelectorAll("main .panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === id);
  });
}

document.querySelectorAll("nav button").forEach((button) => {
  button.addEventListener("click", () => selectPanel(button.dataset.section));
});

async function http(url, options = {}) {
  const config = {
    headers: { "Content-Type": "application/json", Accept: "application/json", ...(options.headers || {}) },
    ...options
  };
  const response = await fetch(url, config);
  if (!response.ok) {
    throw new Error(${response.status} );
  }
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

const facturacionLog = document.getElementById("facturacion-log");
const pagosLog = document.getElementById("pagos-log");
const tablaFacturas = document.getElementById("tabla-facturas");
const tablaPagosPendientes = document.getElementById("tabla-pagos-pendientes");
const tablaPagosConciliados = document.getElementById("tabla-pagos-conciliados");
const reportOutput = document.getElementById("reportes-output");
let ingresosChart;

function appendLog(target, message) {
  const now = new Date().toLocaleTimeString();
  target.textContent = [] \n;
}

function formatoMonto(monto) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(monto || 0));
}

async function cargarStats() {
  const statsGrid = document.getElementById("stats");
  statsGrid.innerHTML = "";
  try {
    const kpis = await http(${endpoints.facturacion}/facturacion/kpis);
    const cards = [
      { label: "Clientes activos", value: kpis?.clientes_activos ?? 0 },
      { label: "Ingresos mensuales", value: formatoMonto(kpis?.ingresos_mensuales ?? 0) },
      { label: "Facturas emitidas", value: kpis?.facturas_emitidas ?? 0 },
      { label: "Morosidad", value: kpis?.morosos ?? 0 }
    ];
    cards.forEach(({ label, value }) => {
      const card = document.createElement("div");
      card.className = "stat-card";
      card.innerHTML = <h3></h3><strong></strong>;
      statsGrid.appendChild(card);
    });
  } catch (error) {
    console.warn("[portal-facturacion] no fue posible obtener kpis", error);
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = <h3>KPIs demo</h3><strong>Sin conexion</strong>;
    statsGrid.appendChild(card);
  }
}

async function cargarFacturas() {
  tablaFacturas.innerHTML = "";
  try {
    const facturas = await http(${endpoints.facturacion}/facturacion/ultimas?limit=10);
    (facturas || []).forEach((fac) => {
      const row = document.createElement("tr");
      row.innerHTML = 
        <td title="">...</td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      ;
      tablaFacturas.appendChild(row);
    });
    if (!tablaFacturas.children.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="5">Sin registros recientes</td>';
      tablaFacturas.appendChild(row);
    }
  } catch (error) {
    console.warn("[portal-facturacion] no fue posible cargar facturas", error);
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="5">Modo demo activo</td>';
    tablaFacturas.appendChild(row);
  }
}

function parseConciliacionCsv(csv) {
  if (!csv) return [];
  const [header, ...rows] = csv.trim().split(/\r?\n/);
  const cols = header.split(",");
  return rows
    .map((line) => line.split(","))
    .filter((parts) => parts.length === cols.length)
    .map(([referencia, monto, estatus, conciliado]) => ({ referencia, monto: Number(monto), estatus, conciliado: conciliado === "true" }));
}

async function cargarPagos() {
  tablaPagosPendientes.innerHTML = "";
  tablaPagosConciliados.innerHTML = "";
  try {
    const pendientes = await http(${endpoints.pagos}/pagos/pendientes);
    (pendientes || []).forEach((pago) => {
      const row = document.createElement("tr");
      row.innerHTML = 
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      ;
      tablaPagosPendientes.appendChild(row);
    });
    if (!tablaPagosPendientes.children.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="4">Sin pagos pendientes</td>';
      tablaPagosPendientes.appendChild(row);
    }
  } catch (error) {
    console.warn("[portal-facturacion] no fue posible obtener pagos pendientes", error);
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="4">Modo demo</td>';
    tablaPagosPendientes.appendChild(row);
  }

  try {
    const conciliacion = await http(${endpoints.pagos}/pagos/conciliar);
    const registros = parseConciliacionCsv(conciliacion?.csv);
    registros
      .filter((item) => item.conciliado)
      .forEach((item) => {
        const row = document.createElement("tr");
        row.innerHTML = 
          <td></td>
          <td></td>
          <td>conciliado</td>
          <td></td>
        ;
        tablaPagosConciliados.appendChild(row);
      });
    if (!tablaPagosConciliados.children.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="4">Aun sin conciliados</td>';
      tablaPagosConciliados.appendChild(row);
    }
  } catch (error) {
    console.warn("[portal-facturacion] no fue posible obtener conciliados", error);
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="4">Modo demo</td>';
    tablaPagosConciliados.appendChild(row);
  }
}

function agruparPorMes(facturas) {
  const mapa = new Map();
  (facturas || []).forEach((fac) => {
    if (fac.estatus !== "pagado" && fac.estatus !== "timbrado") return;
    const fecha = fac.fecha_emision ? new Date(fac.fecha_emision) : new Date();
    const llave = ${fecha.getFullYear()}-;
    const acumulado = mapa.get(llave) || 0;
    mapa.set(llave, acumulado + Number(fac.total || 0));
  });
  return Array.from(mapa.entries()).sort(([a], [b]) => (a > b ? 1 : -1));
}

async function renderIngresosChart() {
  const canvas = document.getElementById("ingresos-chart");
  if (!canvas || typeof Chart === "undefined") {
    return;
  }
  try {
    const datos = await http(${endpoints.facturacion}/facturacion/ultimas?limit=24);
    const agrupado = agruparPorMes(datos);
    const etiquetas = agrupado.map(([mes]) => mes);
    const valores = agrupado.map(([, total]) => Number(total.toFixed(2)));
    const dataset = {
      label: "Ingresos mensuales",
      data: valores,
      borderColor: "#1f78ff",
      backgroundColor: "rgba(31, 120, 255, 0.2)",
      tension: 0.3,
      fill: true
    };
    if (!ingresosChart) {
      ingresosChart = new Chart(canvas, {
        type: "line",
        data: { labels: etiquetas, datasets: [dataset] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: true },
            tooltip: { callbacks: { label: (ctx) => ${ctx.formattedValue} MXN } }
          },
          scales: {
            y: {
              ticks: {
                callback: (value) => formatoMonto(value)
              }
            }
          }
        }
      });
    } else {
      ingresosChart.data.labels = etiquetas;
      ingresosChart.data.datasets[0].data = valores;
      ingresosChart.update();
    }
  } catch (error) {
    console.warn("[portal-facturacion] no fue posible dibujar grafica", error);
    const fallback = agruparPorMes([
      { fecha_emision: new Date().toISOString(), total: 399, estatus: "pagado" },
      { fecha_emision: new Date(Date.now() - 86400000 * 30).toISOString(), total: 599, estatus: "pagado" }
    ]);
    if (!ingresosChart) {
      ingresosChart = new Chart(canvas, {
        type: "line",
        data: {
          labels: fallback.map(([mes]) => mes),
          datasets: [{
            label: "Ingresos demo",
            data: fallback.map(([, total]) => total),
            borderColor: "#ff9f1a",
            backgroundColor: "rgba(255, 159, 26, 0.2)",
            fill: true
          }]
        }
      });
    }
  }
}

const formLote = document.getElementById("form-lote");
formLote.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(formLote);
  const action = event.submitter?.dataset.action;
  if (action !== "generar") return;
  try {
    const lote = formData.get("lote");
    const payload = lote ? JSON.parse(String(lote)) : [];
    await http(${endpoints.facturacion}/facturacion/generar-masiva, { method: "POST", body: JSON.stringify(payload) });
    appendLog(facturacionLog, "Lote procesado correctamente.");
    await Promise.all([cargarStats(), cargarFacturas(), renderIngresosChart()]);
  } catch (error) {
    appendLog(facturacionLog, Error generando lote: );
  }
});

formLote.querySelector('[data-action="cancelar"]').addEventListener("click", async () => {
  const uuid = String(new FormData(formLote).get("cancelar") || "");
  if (!uuid) {
    appendLog(facturacionLog, "Proporciona un UUID para cancelar.");
    return;
  }
  try {
    await http(${endpoints.facturacion}/facturacion//cancelar, { method: "POST" });
    appendLog(facturacionLog, Factura  cancelada.);
    await Promise.all([cargarStats(), cargarFacturas(), renderIngresosChart()]);
  } catch (error) {
    appendLog(facturacionLog, Error cancelando factura: );
  }
});

document.getElementById("btn-conciliar").addEventListener("click", async () => {
  try {
    const data = await http(${endpoints.pagos}/pagos/conciliar);
    appendLog(pagosLog, Conciliacion ejecutada. Registros: );
    await cargarPagos();
  } catch (error) {
    appendLog(pagosLog, Error al conciliar: );
  }
});

document.getElementById("btn-exportar").addEventListener("click", async () => {
  try {
    const data = await http(${endpoints.pagos}/pagos/conciliar);
    if (data?.csv) {
      const blob = new Blob([data.csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "conciliacion.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      appendLog(pagosLog, "CSV descargado.");
    }
  } catch (error) {
    appendLog(pagosLog, Error exportando CSV: );
  }
});

document.getElementById("btn-kpis").addEventListener("click", async () => {
  await cargarStats();
  reportOutput.prepend(document.createRange().createContextualFragment('<div class="report-item"><strong>KPIs actualizados</strong><pre>Consulta completada</pre></div>'));
});

document.getElementById("btn-backtest").addEventListener("click", () => {
  const item = document.createElement("div");
  item.className = "report-item";
  item.innerHTML = <strong>Backtest churn</strong><pre>{"mensaje":"Ejecuta make bi-churn para generar CSV","archivo":"Tests/reports/bi/backtest.csv"}</pre>;
  reportOutput.prepend(item);
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((err) => console.warn("SW error", err));
  });
}

selectPanel("dashboard");
(async () => {
  await Promise.all([cargarStats(), cargarFacturas(), cargarPagos(), renderIngresosChart()]);
})();
