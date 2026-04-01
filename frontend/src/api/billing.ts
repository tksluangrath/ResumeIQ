import client from './client'
import type { BillingStatusResponse, CheckoutResponse, PortalResponse } from '../types/api'

export async function getBillingStatus(): Promise<BillingStatusResponse> {
  const { data } = await client.get<BillingStatusResponse>('/billing/status')
  return data
}

export async function createCheckout(
  plan: 'starter' | 'pro',
  successUrl: string,
  cancelUrl: string,
): Promise<CheckoutResponse> {
  const { data } = await client.post<CheckoutResponse>('/billing/checkout', {
    plan,
    success_url: successUrl,
    cancel_url: cancelUrl,
  })
  return data
}

export async function getPortal(): Promise<PortalResponse> {
  const { data } = await client.get<PortalResponse>('/billing/portal')
  return data
}
