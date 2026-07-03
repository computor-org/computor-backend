/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Sso

 */



export interface GitProviderCreate {
  organization_id: string;
  type: "gitlab" | "forgejo" | "github";
  url: string;
  token: string;
}

export interface GitProviderGet {
  id: string;
  organization_id: string;
  type: "gitlab" | "forgejo" | "github";
  url: string;
}

export interface OrgProviderResult {
  provider_entity_id: string;
  properties: any;
}

export interface FamilyProviderResult {
  provider_entity_id: string;
  properties: any;
}