import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  thresholds: {
    http_req_duration: ['p(95)<800'],
  },
};

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
  const base = __ENV.K6_ORQ_URL
    || (__ENV.HOST_ORQ_PORT ? `http://localhost:${__ENV.HOST_ORQ_PORT}` : 'http://app-orquestador:8010');
  const res = http.post(`${base}/saga/alta-cliente`, payload, { headers });
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(0.5);
}
