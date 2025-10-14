import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '10s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{service:clientes}': ['p(95)<500'],
    'http_req_duration{service:catalogo}': ['p(95)<500'],
    'http_req_duration{service:facturacion}': ['p(95)<500'],
  },
  tags: { sprint: '0' },
};

export default function () {
  const s = [
    { name: 'clientes', url: 'http://app-clientes:8000/health' },
    { name: 'catalogo', url: 'http://app-catalogo:8001/health' },
    { name: 'facturacion', url: 'http://app-facturacion:8002/health' },
  ];
  for (const svc of s) {
    const res = http.get(svc.url, { tags: { service: svc.name } });
    check(res, { 'status 200': (r) => r.status === 200 });
    sleep(0.2);
  }
}
