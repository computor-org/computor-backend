/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Organizations

 */



import type { GitLabConfig, GitLabConfigGet, GitLabCredentials } from './common';

import type { UserList } from './users';



export interface OrganizationProperties {
  gitlab?: GitLabConfig | null;
}

export interface OrganizationPropertiesGet {
  gitlab?: GitLabConfigGet | null;
}

export interface OrganizationCreate {
  /** Organization title */
  title?: string | null;
  /** Organization description */
  description?: string | null;
  /** Hierarchical path (ltree format) */
  path: string;
  /** Type of organization */
  organization_type: OrganizationType;
  /** Associated user ID (for user type organizations) */
  user_id?: string | null;
  /** Additional properties */
  properties?: OrganizationProperties | null;
  /** Organization number/identifier */
  number?: string | null;
  /** Contact email address */
  email?: any | null;
  /** Phone number */
  telephone?: string | null;
  /** Fax number */
  fax_number?: string | null;
  /** Organization website URL */
  url?: string | null;
  /** Postal/ZIP code */
  postal_code?: string | null;
  /** Street address */
  street_address?: string | null;
  /** City/locality */
  locality?: string | null;
  /** State/region */
  region?: string | null;
  /** Country */
  country?: string | null;
}

export interface OrganizationGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  /** Organization unique identifier */
  id: string;
  /** Hierarchical path */
  path: string;
  /** Organization title */
  title?: string | null;
  /** Organization description */
  description?: string | null;
  /** Type of organization */
  organization_type: OrganizationType;
  /** Associated user ID */
  user_id?: string | null;
  /** Additional properties */
  properties?: OrganizationPropertiesGet | null;
  /** Organization number */
  number?: string | null;
  /** Contact email */
  email?: any | null;
  /** Phone number */
  telephone?: string | null;
  /** Fax number */
  fax_number?: string | null;
  /** Website URL */
  url?: string | null;
  /** Postal code */
  postal_code?: string | null;
  /** Street address */
  street_address?: string | null;
  /** City/locality */
  locality?: string | null;
  /** State/region */
  region?: string | null;
  /** Country */
  country?: string | null;
}

export interface OrganizationList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  /** Organization unique identifier */
  id: string;
  /** Hierarchical path */
  path: string;
  /** Organization title */
  title?: string | null;
  /** Type of organization */
  organization_type: OrganizationType;
  /** Associated user ID */
  user_id?: string | null;
  /** Contact email */
  email?: any | null;
}

export interface OrganizationUpdate {
  title?: string | null;
  description?: string | null;
  path?: string | null;
  organization_type?: OrganizationType | null;
  user_id?: string | null;
  properties?: OrganizationProperties | null;
  number?: string | null;
  email?: string | null;
  telephone?: string | null;
  fax_number?: string | null;
  url?: string | null;
  postal_code?: string | null;
  street_address?: string | null;
  locality?: string | null;
  region?: string | null;
  country?: string | null;
}

export interface OrganizationQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  path?: string | null;
  organization_type?: OrganizationType | null;
  user_id?: string | null;
  number?: string | null;
  email?: string | null;
  telephone?: string | null;
  fax_number?: string | null;
  url?: string | null;
  postal_code?: string | null;
  street_address?: string | null;
  locality?: string | null;
  region?: string | null;
  country?: string | null;
}

export interface OrganizationMemberCreate {
  id?: string | null;
  properties?: any | null;
  user_id: string;
  organization_id: string;
  organization_role_id: string;
}

export interface OrganizationMemberGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  properties?: any | null;
  user_id: string;
  organization_id: string;
  organization_role_id: string;
  user?: UserList | null;
}

export interface OrganizationMemberList {
  id: string;
  user_id: string;
  organization_id: string;
  organization_role_id: string;
  user?: UserList | null;
}

export interface OrganizationMemberUpdate {
  properties?: any | null;
  organization_role_id?: string | null;
}

export interface OrganizationMemberQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  user_id?: string | null;
  organization_id?: string | null;
  organization_role_id?: string | null;
}

/**
 * Request to create an organization via Temporal workflow.
 */
export interface OrganizationTaskRequest {
  organization: Record<string, any>;
  gitlab: GitLabCredentials;
  parent_group_id: number;
}

export interface OrganizationRoleGet {
  id: string;
  title?: string | null;
  description?: string | null;
  builtin?: boolean;
}

export interface OrganizationRoleList {
  id: string;
  title?: string | null;
  description?: string | null;
  builtin?: boolean;
}

export interface OrganizationRoleQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  builtin?: boolean | null;
}



export type OrganizationType = "user" | "community" | "organization";