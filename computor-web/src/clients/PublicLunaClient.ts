import { APIClient, apiClient } from 'api/client';

export type LunaStatus =
  | { state: 'queued' | 'running' }
  | { state: 'done'; answer: string }
  | { state: 'failed'; answer: '' };

export class PublicLunaClient {
  constructor(private client: APIClient = apiClient) {}

  availability(): Promise<{ enabled: boolean }> {
    return this.client.get('/public-luna/availability');
  }

  ask(courseContentId: string, question: string, submittedText: string): Promise<{ id: string; state: 'queued' }> {
    return this.client.post('/public-luna/requests', {
      course_content_id: courseContentId,
      question,
      submitted_text: submittedText,
    });
  }

  status(id: string): Promise<LunaStatus> {
    return this.client.get(`/public-luna/requests/${encodeURIComponent(id)}`);
  }
}
