import { z } from "zod";

export * from "./database.types";

/**
 * User Roles within an organization
 */
export const UserRoleSchema = z.enum(["member", "tool-admin", "org-admin"]);
export type UserRole = z.infer<typeof UserRoleSchema>;

/**
 * Organization schema
 */
export const OrganizationSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  domains: z.array(z.string()),
  createdAt: z.string().datetime(),
});
export type Organization = z.infer<typeof OrganizationSchema>;

/**
 * User Profile schema
 */
export const ProfileSchema = z.object({
  id: z.string().uuid(),
  orgId: z.string().uuid(),
  email: z.string().email(),
  role: UserRoleSchema,
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  avatarUrl: z.string().url().optional(),
  createdAt: z.string().datetime(),
});
export type Profile = z.infer<typeof ProfileSchema>;

/**
 * DPDP Act 2023 Statutory Consent
 */
export const ConsentRecordSchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  orgId: z.string().uuid(),
  consentVersion: z.string().default("2026.1"),
  ipAddress: z.string().nullable().optional(),
  consentedAt: z.string().datetime(),
  status: z.enum(["active", "revoked"]).default("active"),
});
export type ConsentRecord = z.infer<typeof ConsentRecordSchema>;

export const DPDPConsentPayloadSchema = z.object({
  consentVersion: z.string().default("2026.1"),
  language: z.enum(["en", "hi"]).default("en"),
  acceptedDisclosures: z.array(z.string()).min(4),
});
export type DPDPConsentPayload = z.infer<typeof DPDPConsentPayloadSchema>;

/**
 * MCP Connector Providers
 */
export const ConnectorProviderSchema = z.enum([
  "google_workspace",
  "zoho_workplace",
  "microsoft_365",
  "notion",
  "slack",
  "atlassian",
  "canva",
  "figma",
  "hubspot",
  "custom_mcp",
]);
export type ConnectorProvider = z.infer<typeof ConnectorProviderSchema>;

export const McpConnectionStatusSchema = z.enum(["active", "expired", "revoked", "connecting"]);
export type McpConnectionStatus = z.infer<typeof McpConnectionStatusSchema>;

export const McpConnectionSchema = z.object({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  orgId: z.string().uuid(),
  provider: ConnectorProviderSchema,
  scopes: z.array(z.string()),
  vaultSecretId: z.string().uuid().nullable().optional(),
  status: McpConnectionStatusSchema,
  updatedAt: z.string().datetime(),
});
export type McpConnection = z.infer<typeof McpConnectionSchema>;

/**
 * Connector Metadata for UI Directory
 */
export interface ConnectorDefinition {
  id: ConnectorProvider;
  name: string;
  publisher: string;
  category: "productivity" | "sales_crm" | "accounting_finance" | "communication" | "developer";
  description: string;
  verified: boolean;
  iconName: string;
  defaultScopes: string[];
}

export const SEED_CONNECTORS: ConnectorDefinition[] = [
  {
    id: "google_workspace",
    name: "Google Workspace",
    publisher: "by Google",
    category: "productivity",
    description: "Search Drive files, compose Gmail drafts, check Calendar meetings, and read Docs & Sheets.",
    verified: true,
    iconName: "google",
    defaultScopes: [
      "https://www.googleapis.com/auth/drive.readonly",
      "https://www.googleapis.com/auth/gmail.send",
      "https://www.googleapis.com/auth/calendar.events.readonly",
    ],
  },
  {
    id: "zoho_workplace",
    name: "Zoho Workplace",
    publisher: "by Zoho",
    category: "accounting_finance",
    description: "Query GST invoices and bills via Zoho Books, manage leads in Zoho CRM, and check Zoho Mail.",
    verified: true,
    iconName: "zoho",
    defaultScopes: [
      "ZohoBooks.invoices.READ",
      "ZohoCRM.modules.leads.READ",
      "ZohoMail.messages.READ",
    ],
  },
  {
    id: "notion",
    name: "Notion",
    publisher: "by Notion",
    category: "productivity",
    description: "Search workspace pages, read task boards, and append notes to company wikis.",
    verified: true,
    iconName: "notion",
    defaultScopes: ["read_content", "update_content"],
  },
  {
    id: "slack",
    name: "Slack",
    publisher: "by Slack",
    category: "communication",
    description: "Send channel messages, summarize threads, and surface team announcements.",
    verified: true,
    iconName: "slack",
    defaultScopes: ["channels:read", "chat:write"],
  },
  {
    id: "atlassian",
    name: "Atlassian Jira & Confluence",
    publisher: "by Atlassian",
    category: "developer",
    description: "Read Jira sprint tickets, log issue comments, and search Confluence documentation.",
    verified: true,
    iconName: "atlassian",
    defaultScopes: ["read:jira-work", "read:confluence-content.all"],
  },
  {
    id: "canva",
    name: "Canva",
    publisher: "by Canva",
    category: "productivity",
    description: "Browse brand assets, design templates, and export marketing collateral.",
    verified: true,
    iconName: "canva",
    defaultScopes: ["asset:read", "design:read"],
  },
  {
    id: "figma",
    name: "Figma",
    publisher: "by Figma",
    category: "productivity",
    description: "Inspect component styles, extract design tokens, and review canvas frames.",
    verified: true,
    iconName: "figma",
    defaultScopes: ["file_read"],
  },
  {
    id: "hubspot",
    name: "HubSpot",
    publisher: "by HubSpot",
    category: "sales_crm",
    description: "Sync deals, contacts, pipeline stages, and marketing campaign metrics.",
    verified: true,
    iconName: "hubspot",
    defaultScopes: ["crm.objects.contacts.read", "crm.objects.deals.read"],
  },
];
