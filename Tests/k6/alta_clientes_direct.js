import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<800'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.K6_CLIENTES_URL
  || (__ENV.HOST_CLIENTES_PORT ? `http://localhost:${__ENV.HOST_CLIENTES_PORT}` : 'http://app-clientes:8000');

export default function () {
  const payload = JSON.stringify({
    nombre: 'Carga ' + __VU + '-' + __ITER,
    rfc: 'AAA010101AAA',
    email: `carga${__VU}_${__ITER}@example.com`,
    telefono: '5555555555',
    plan_id: 'INT100',
    domicilio: { calle:'a', numero:'1', colonia:'c', cp:'01000', ciudad:'CDMX', estado:'CDMX', zona:'NORTE' },
    contacto: { nombre:'Carga', email:`carga${__VU}_${__ITER}@example.com`, telefono:'5555555555' },
    consentimiento: { marketing:true, terminos:true },
    idem: `${__VU}-${__ITER}`
  });
  const headers = { 'Content-Type': 'application/json' };
  const res = http.post(`${BASE_URL}/clientes`, payload, { headers });
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(0.3);
}

