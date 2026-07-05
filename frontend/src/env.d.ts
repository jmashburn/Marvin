/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly MARVIN_API_URL?: string;
  readonly MARVIN_GROUP_SLUG?: string;
  readonly MARVIN_SITE_CLIENT_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
