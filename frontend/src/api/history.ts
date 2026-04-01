import client from './client'
import type { PaginatedScans, ScanRecord } from '../types/api'

export async function getHistory(page = 1, pageSize = 20): Promise<PaginatedScans> {
  const { data } = await client.get<PaginatedScans>('/history', {
    params: { page, page_size: pageSize },
  })
  return data
}

export async function getScan(id: string): Promise<ScanRecord> {
  const { data } = await client.get<ScanRecord>(`/history/${id}`)
  return data
}
