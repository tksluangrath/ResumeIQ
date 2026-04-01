import client from './client'
import type { TokenResponse, UserPublic } from '../types/api'

export async function register(email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/register', { email, password })
  return data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/login', { email, password })
  return data
}

export async function getMe(): Promise<UserPublic> {
  const { data } = await client.get<UserPublic>('/auth/me')
  return data
}
