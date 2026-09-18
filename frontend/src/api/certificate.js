import { createResourceApi } from './client'
import http from './client'

const base = createResourceApi('certificates')

export const certificateApi = {
  ...base,
  /** 证书到期提醒：即将到期 + 已过期 */
  reminders: (params) => http.get('/certificates/reminders', { params }),
  /** 安排持证任务前的逐人证书预校验 */
  check: (params) => http.get('/certificates/check', { params }),
  /** 注销 / 恢复在册 */
  changeStatus: (id, payload) => http.patch(`/certificates/${id}/status`, payload),
}
