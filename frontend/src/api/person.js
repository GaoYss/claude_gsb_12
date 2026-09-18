import { createResourceApi } from './client'
import http from './client'

const base = createResourceApi('persons')

export const personApi = {
  ...base,
  /** 在岗人员下拉选项 */
  options: (params) => http.get('/persons/options', { params }),
}
