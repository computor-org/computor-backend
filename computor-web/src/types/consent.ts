// Shapes of the backend consent endpoints (ConsentStatusGet / PolicyTextGet
// in computor-types/src/computor_types/consent.py).

export interface ConsentStatus {
  required_version: string | null;
  has_consented: boolean;
  granted_at: string | null;
}

export interface PolicyText {
  version: string;
  lang: string;
  languages: string[];
  effective_from: string | null;
  content: string;
}
