import axios, { AxiosInstance } from 'axios';

export interface PaymenterClientConfig {
  baseUrl: string;
  apiKey: string;
}

export interface PaymenterSubscription {
  id: string;
  clientId: string;
  productId: string;
  status: 'active' | 'suspended' | 'unpaid' | 'cancelled';
  expiresAt: string | null;
}

export class PaymenterBillingClient {
  private client: AxiosInstance;

  constructor(config: PaymenterClientConfig) {
    this.client = axios.create({
      baseURL: config.baseUrl,
      headers: {
        'Authorization': `Bearer ${config.apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }

  // Retrieve tenant's active subscriptions
  async getTenantSubscriptions(clientId: string): Promise<PaymenterSubscription[]> {
    try {
      const response = await this.client.get(`/api/clients/${clientId}/subscriptions`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch subscriptions for Paymenter client: ${clientId}`, error);
      throw new Error('Billing systems communication error');
    }
  }

  // Create an usage metering invoice for resource-based consumption
  async createResourceInvoice(
    clientId: string,
    amount: number,
    description: string
  ): Promise<{ invoiceId: string; paymentUrl: string }> {
    try {
      const response = await this.client.post(`/api/clients/${clientId}/invoices`, {
        amount,
        description,
        status: 'unpaid',
      });
      return {
        invoiceId: response.data.id,
        paymentUrl: response.data.payment_url,
      };
    } catch (error) {
      console.error(`Failed to generate Paymenter resource invoice for client: ${clientId}`, error);
      throw new Error('Billing systems invoice creation failure');
    }
  }

  // Check quota validity before launching a workspace
  checkResourceLimits(
    requestedCpu: number,
    requestedRamMb: number,
    allocatedCpu: number,
    allocatedRamMb: number,
    maxCpuQuota: number,
    maxRamQuota: number
  ): boolean {
    if (allocatedCpu + requestedCpu > maxCpuQuota) return false;
    if (allocatedRamMb + requestedRamMb > maxRamQuota) return false;
    return true;
  }
}
