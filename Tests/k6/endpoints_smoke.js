import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '1m',
  thresholds: {
    'http_req_duration{ep:clientes}': ['p(95)<1200'],
    'http_req_duration{ep:planes}': ['p(95)<800'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // POST /clientes
  const baseClientes = 'http://app-clientes:8000';
  const payload = JSON.stringify({
    nombre: 'VU ' + __VU + ' I ' + __ITER,
    rfc: 'AAA010101AAA',
    email: `vu${__VU}_${__ITER}@example.com`,
    telefono: '5555555555',
    plan_id: 'INT100',
    domicilio: { calle:'x', numero:'1', colonia:'c', cp:'01000', ciudad:'CDMX', estado:'CDMX', zona:'NORTE' },
    contacto: { nombre:'VU', email:`vu${__VU}_${__ITER}@example.com`, telefono:'5555555555' },
    consentimiento: { marketing:true, terminos:true },
    idem: `${__VU}-${__ITER}`
  });
  const r1 = http.post(`${baseClientes}/clientes`, payload, { headers: { 'Content-Type': 'application/json' }, tags: { ep: 'clientes' } });
  check(r1, { 'POST /clientes 200': (r) => r.status === 200 });

  // GET /catalogo/planes
  const baseCat = 'http://app-catalogo:8001';
  const r2 = http.get(`${baseCat}/catalogo/planes?zona=NORTE&velocidad=100`, { tags: { ep: 'planes' } });
  check(r2, { 'GET /catalogo/planes 200': (r) => r.status === 200 });

  sleep(0.2);
}
