import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    'http_req_duration{ep:agendar}': ['p(95)<800'],
    'http_req_duration{ep:cerrar}': ['p(95)<800'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const base = 'http://app-instalaciones:8004';
  const ag = http.post(`${base}/instalaciones/agendar`, JSON.stringify({ clienteId: 1, ventana: '9-12', zona: 'NORTE' }), { headers: { 'Content-Type': 'application/json' }, tags: { ep: 'agendar' } });
  check(ag, { 'agendar 200': (r) => r.status === 200 });
  const id = ag.json('id');
  http.put(`${base}/instalaciones/despachar/${id}`);
  const ce = http.put(`${base}/instalaciones/cerrar/${id}`, JSON.stringify({ evidencias: ['http://example/e1.png'], notas: 'ok' }), { headers: { 'Content-Type': 'application/json' }, tags: { ep: 'cerrar' } });
  check(ce, { 'cerrar 200': (r) => r.status === 200 });
  sleep(0.1);
}
