import client from './client'
import type { MatchResponse } from '../types/api'

export async function scanResume(file: File, jobDescription: string): Promise<MatchResponse> {
  const form = new FormData()
  form.append('resume', file)
  form.append('job_description', jobDescription)
  const { data } = await client.post<MatchResponse>('/match', form)
  return data
}
