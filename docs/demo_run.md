# Demo Telecable MVP · Setup Inteligente

Este documento explica cómo usar el nuevo **Setup Inteligente** para preparar y
levantar la demo integral (portal cliente/técnico/ventas, microservicios y
simulador de router) tanto en Linux como en Windows. El sistema está compuesto
por un orquestador en Python y wrappers específicos para cada plataforma que
pueden ejecutarse con doble click.

## 1. Scripts disponibles

| Script | Descripción |
| --- | --- |
| `scripts/setup_linux.sh` | Wrapper para Linux. Verifica Python 3.10+, delega al orquestador y mantiene la terminal abierta. |
| `scripts/setup_windows.ps1` | Wrapper de PowerShell para Windows. Comprueba Python, detecta `winget/choco` y lanza el orquestador. |
| `scripts/setup_windows.bat` | Archivo doble-click que invoca al script PowerShell con `ExecutionPolicy Bypass`. |
| `scripts/setup_orchestrator.py` | Script principal en Python que realiza todas las etapas: dependencias, configuración, puertos, arranque, health checks y demo opcional. |
| `scripts/port_helper.py` | Utilidad auxiliar para validar puertos específicos. |
| `scripts/tests_smoke.sh` / `scripts/tests_smoke.ps1` | Pruebas de humo para validar `/health` y los portales una vez que el setup terminó. |

## 2. Ejecución en Linux (Ubuntu)

1. Asegúrate de marcar el script como ejecutable (una sola vez):
   ```bash
   chmod +x scripts/setup_linux.sh
   ```
2. Desde el gestor de archivos puedes hacer doble click y seleccionar *"Ejecutar en una terminal"*. Si tu gestor no ofrece esta opción, abre manualmente una terminal y ejecuta:
   ```bash
   ./scripts/setup_linux.sh
   ```
3. El orquestador mostrará un dashboard paso a paso:
   - **Etapa 0** valida SO, Python y Git.
   - **Etapa 1** revisa Docker, Node.js, pnpm/npm, Playwright, etc. Si falta algo propondrá instalar con `sudo apt install ...`.
   - **Etapa 2** verifica `.env`, `.env.ports` y directorios críticos (`infra/postgres`, `infra/minio-data`, `services/router_simulator`).
   - **Etapa 3** asigna puertos libres dentro de `PORT_RANGE` (por defecto `3000-3999`) y actualiza `.env.ports`.
   - **Etapa 4** ejecuta `docker compose up -d --build` si existe `docker-compose.yml` y levanta los portales Vite en segundo plano.
   - **Etapa 5** realiza health checks (`http://localhost:<puerto>/health`).
   - **Etapa 6** (opcional) ejecuta la demo automática (`--demo`).
4. El script es interactivo: ante un fallo mostrará ✅ lo que pasó, ❌ lo que falló y 🛠️ los comandos sugeridos. Puedes elegir `(R)etry`, `(A)uto-fix`, `(S)kip` o `(Q)uit`.
5. Al finalizar mostrará un resumen con los puertos asignados y dejará la terminal abierta para que presiones ENTER.

### 2.1 Ejemplo de mensajes

```
INICIANDO SETUP INTELIGENTE — ISP TELECABLE MVP
1/7 Verificando Docker... OK (docker version: 24.0.5)
PUERTO 3000 OCUPADO por PID 5678 (node). Reasignar a 3001? (Y/n)
ERROR: Docker no responde: 'Cannot connect to the Docker daemon'. Posibles causas: Docker no está corriendo. Solución rápida: sudo systemctl start docker. Intentar restart? (Y/n)
LISTO ✅ El demo está corriendo. URLs: Cliente: http://localhost:3000 Técnico: http://localhost:3001 Ventas: http://localhost:3002 RouterSim: http://localhost:4000. Logs: logs/setup.log. Presiona ENTER para cerrar.
```

### 2.2 Prueba de humo

Una vez que la demo esté arriba puedes ejecutar la prueba rápida:
```bash
./scripts/tests_smoke.sh
```
Esto consultará `/health` en la API de clientes y en el router simulator, además de validar que el portal cliente responde.

## 3. Ejecución en Windows

1. Abre el explorador de archivos y haz doble click en `scripts\setup_windows.bat`. Esto abrirá PowerShell con la política `Bypass` y ejecutará `scripts/setup_windows.ps1`.
2. Si Windows bloquea la ejecución de scripts, verás el mensaje correspondiente. Sigue las instrucciones mostradas (por ejemplo, ejecuta manualmente `powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1`).
3. El wrapper verificará Python 3.10+. Si no está disponible sugerirá instalarlo con `winget` o `choco` y mantendrá la ventana abierta.
4. El orquestador Python ejecutará las mismas etapas que en Linux, adaptando los mensajes y sugerencias (por ejemplo, `taskkill /PID <pid> /F` para cerrar procesos en puertos ocupados).
5. Al terminar dejará la ventana abierta esperando ENTER.

### 3.1 Prueba de humo

Con los servicios arriba ejecuta en PowerShell:
```powershell
./scripts/tests_smoke.ps1
```

## 4. Modo automático / CI

El orquestador acepta banderas adicionales:

- `--auto` / `--yes`: modo no interactivo, acepta los auto-fix disponibles.
- `--demo`: ejecuta la demo automática que crea un cliente, apaga y vuelve a encender su router.
- `--ci`: modo pensado para pipelines, evita prompts y retorna códigos de salida (`0` éxito, `1` parcial, `2` fatal en futuras ampliaciones).
- `--verbose`: imprime los logs detallados además de guardarlos en `logs/setup.log`.

Ejemplo en Linux:
```bash
./scripts/setup_linux.sh --auto --demo
```

## 5. Archivos generados

- `.env.ports`: mapa actualizado de puertos (`HOST_CLIENTES_PORT`, `HOST_TECH_PORT`, etc.).
- `logs/setup.log`: bitácora estructurada con timestamps.
- `logs/last_state.json`: último estado de cada etapa y puertos reservados.
- `logs/demo_transcript.txt`: sólo si ejecutas `--demo`, contiene la transcripción del flujo automático.

## 6. Problemas frecuentes y soluciones

| Problema | Causa probable | Solución sugerida |
| --- | --- | --- |
| Docker no responde | Docker Desktop detenido / servicio docker apagado | En Linux: `sudo systemctl start docker`. En Windows: abre Docker Desktop. Usa la opción `(R)etry` cuando esté activo. |
| Puerto ocupado | Otro servicio usa el puerto preferido | El orquestador propondrá reasignar automáticamente. También puedes cerrar el proceso con `kill <PID>` (Linux) o `taskkill /PID <PID> /F` (Windows). |
| Falta Playwright | Dependencia de pruebas E2E | `npm install -g playwright` o `npx playwright install`. El orquestador mostrará el comando exacto. |
| No existe `.env` | Variables de entorno no definidas | Copia el archivo de ejemplo o crea uno nuevo siguiendo la documentación interna. |

## 7. Demo manual

Si prefieres validar el flujo manualmente:

1. Abre `http://localhost:<HOST_CLIENTES_PORT>/cliente`.
   - Usa el botón **“Autocompletar demo”** o completa el formulario.
   - Tras registrar, observa el `router_id`, el estado y usa los botones para apagar/encender (WebSocket activo).
2. Abre `http://localhost:<HOST_TECH_PORT>/tecnico` y revisa el listado de routers. Puedes ejecutar reinicios rápidos.
3. Abre `http://localhost:<HOST_SALES_PORT>/ventas` para explorar los planes comerciales.

## 8. Resumen rápido

1. **Linux**: doble click en `setup_linux.sh` (asegúrate de permitir "Ejecutar en terminal").
2. **Windows**: doble click en `setup_windows.bat`. Si PowerShell avisa sobre políticas, usa el comando que se muestra.
3. Sigue las instrucciones en pantalla. Cada etapa indica con iconos si fue exitosa y qué hacer si falla.
4. Consulta `logs/setup.log` y `logs/last_state.json` para diagnósticos detallados.

Con estos scripts dispones de un arranque multiplataforma robusto, con opciones de auto-reparación, logging detallado y una demo automática que valida el flujo extremo a extremo.
