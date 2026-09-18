import { createResourceApi } from './client'
import http from './client'

const base = createResourceApi('workers')

export const workerApi = {
  ...base,
  options: (params) => http.get('/workers/options', { params }),
  teams: () => http.get('/workers/teams'),
}
