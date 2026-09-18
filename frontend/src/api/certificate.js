import { createResourceApi } from './client'
import http from './client'

const base = createResourceApi('certificates')

export const certificateApi = {
  ...base,
  reminders: (params) => http.get('/certificates/reminders', { params }),
  validCheck: (params) => http.get('/certificates/valid-check', { params }),
}
