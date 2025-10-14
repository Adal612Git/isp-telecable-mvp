import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 20 },
    { duration: '5s', target: 60 },
    { duration: '10s', target: 100 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // p95 < 3s
    http_req_failed: ['rate<0.01'],    // <1% de fallos
  },
};

export default function () {
  const url = 'http://app-clientes:8000/clientes';
  const res = http.get(url);
  check(res, {
    'status 200': (r) => r.status === 200,
  });
}

