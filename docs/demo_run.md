# Demo Telecable MVP · Router Simulator + Portales

Este documento explica cómo levantar la demo integral (portal cliente/técnico/ventas y los microservicios necesarios), ejecutar pruebas E2E y depurar problemas comunes tanto en Linux como en Windows.

## 1. Scripts disponibles

| Script | Descripción |
| --- | --- |
| `scripts/run_demo.sh` | Orquestación principal en Linux/macOS: detecta puertos libres, instala dependencias básicas, levanta los microservicios FastAPI y los tres portales Vite, y actualiza `.env.ports`. |
| `scripts/run_demo.ps1` | Variante para Windows que replica la asignación de puertos y abre nuevas ventanas de PowerShell con cada servicio. |

Ambos scripts generan/actualizan el archivo `.env.ports` con los puertos asignados:

```
HOST_CLIENTES_PORT=<puerto portal-cliente>
HOST_TECH_PORT=<puerto portal-tecnico>
HOST_SALES_PORT=<puerto portal-ventas>
HOST_ROUTER_SIM_PORT=<puerto router-simulator>
HOST_CLIENTES_API_PORT=<puerto servicio clientes>
```

## 2. Ejecución en Linux (Ubuntu)

1. Asegúrate de tener Python 3.11+, Node.js 18+ y npm.
2. Concede permisos de ejecución al script (una sola vez):
   ```bash
   chmod +x scripts/run_demo.sh
   ```
3. Ejecuta la orquestación:
   ```bash
   ./scripts/run_demo.sh
   ```
   El script instalará dependencias mínimas (`pip install …` y `npm install` cuando falten), levantará cada servicio y escribirá los logs en `logs/*.service.log`. Si `xdg-open` está disponible abrirá automáticamente los portales en el navegador.
4. Las URL finales (mencionadas también en consola) quedan así:
   - Portal Cliente: `http://localhost:<HOST_CLIENTES_PORT>/cliente`
   - Portal Técnico: `http://localhost:<HOST_TECH_PORT>/tecnico`
   - Portal Ventas: `http://localhost:<HOST_SALES_PORT>/ventas`

### 2.1 Pruebas Playwright

Tras ejecutar la demo, carga las variables de puerto y corre Playwright:
```bash
source .env.ports
cd Tests/e2e
npx playwright test tests/test_router_flow.spec.ts
```
La prueba `test_router_flow` valida el alta del cliente y el control del router (apagar/encender) sobre el portal cliente.

### 2.2 Depuración y logs

- **Logs de servicios**: `tail -f logs/router-simulator.service.log`, `tail -f logs/clientes-api.service.log`, etc.
- **Reiniciar sólo un servicio**: usa `pkill -f <nombre>` (por ejemplo `pkill -f portal-cliente`) y vuelve a ejecutar `./scripts/run_demo.sh`; detectará que falta y lo recreará.
- **Regenerar puertos**: elimina `.env.ports` y relanza el script. También puedes editar manualmente el archivo si deseas forzar puertos específicos antes de la ejecución.

## 3. Ejecución en Windows

Requisitos: Windows 10/11, PowerShell, Python y Node.js en PATH.

1. Abre PowerShell como usuario normal (no requiere privilegios de administrador).
2. Ejecuta el script (desbloquea la política si es necesario):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1
   ```
3. El script asignará puertos, instalará dependencias si faltan y abrirá nuevas ventanas de PowerShell, una por servicio (router-simulator, clientes API y cada portal Vite). No cierres esas ventanas mientras uses la demo.
4. Las URL son las mismas que en Linux, sustituyendo los puertos definidos en `.env.ports`.

### 3.1 Notas específicas de Windows

- Si falta `python` o `npm`, el script lo indicará y deberás ejecutar manualmente los comandos mostrados.
- Los procesos quedan ligados a las ventanas abiertas; ciérralas para detenerlos.

## 4. Flujo manual para validar la demo

1. Abre `http://localhost:<HOST_CLIENTES_PORT>/cliente`.
   - Usa el botón **“Autocompletar demo”** o llena el formulario con tus datos.
   - Registra al cliente: verás el `router_id`, el estado “Encendido” y podrás apagar/encender el router con actualizaciones en tiempo real (WebSocket/polling).
2. Abre `http://localhost:<HOST_TECH_PORT>/tecnico`.
   - Usa la opción *Routers* para visualizar todos los routers simulados y ejecutar reinicios/remociones rápidas.
3. Abre `http://localhost:<HOST_SALES_PORT>/ventas`.
   - Genera propuestas seleccionando uno de los planes disponibles y revisa el historial generado.

## 5. Cambios de puerto y regeneración

- Edita manualmente `.env.ports` antes de ejecutar el script si quieres forzar algún puerto (el script respetará los libres).
- Para regenerar completamente la asignación: elimina `.env.ports` y vuelve a correr `scripts/run_demo.sh` o `scripts/run_demo.ps1`.

## 6. Comandos útiles de depuración

| Propósito | Comando |
| --- | --- |
| Ver logs en vivo | `tail -f logs/run_demo.log` |
| Ver logs de un servicio concreto | `tail -f logs/router-simulator.service.log` |
| Forzar reinstalación npm | `npm install --prefix apps/portal-ventas` |
| Forzar reinicio router-simulator | `pkill -f router-simulator` seguido de `./scripts/run_demo.sh` |
| Ejecutar Playwright completo | `source .env.ports && cd Tests/e2e && npx playwright test` |

Con esto dispones de una demo integral con los tres portales, el simulador de router (FastAPI + WebSocket) y la automatización necesaria para mostrar el flujo completo de alta, monitoreo y venta.

## 7. Changelog rápido

- `services/router_simulator/app/main.py`, `state.py`: servicio FastAPI que gestiona la simulación de routers (estado, uptime, WebSocket y acciones de energía).
- `services/clientes/app/routers/clientes.py`: creación y consulta de clientes con provisión automática de routers y endpoints proxy hacia el simulador.
- `apps/portal-cliente/`: interfaz cliente con página "Mi Router", formulario de alta, control de energía y streaming de estado.
- `apps/portal-tecnico/`: panel técnico para monitorear routers y ejecutar reinicios rápidos.
- `apps/portal-ventas/`: portal ligero con planes y generador de propuestas.
- `scripts/run_demo.sh` / `scripts/run_demo.ps1`: orquestación multiplataforma para levantar servicios y frontends.
- `Tests/e2e/tests/test_router_flow.spec.ts`: prueba Playwright que verifica el flujo de alta y control de router desde la UI.
