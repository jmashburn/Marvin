#!/usr/bin/env node
import "dotenv/config";
import { Command } from "commander";
import { MarvinClient } from "@inneropen/marvin-sdk";
import type {
  MarvinAsset,
  MarvinCollection,
  MarvinEntry,
  MarvinResource,
} from "@inneropen/marvin-sdk/types";
import { renderData, renderList, type OutputMode } from "./output.js";

const program = new Command();

program
  .name("marvin")
  .description("Official CLI for Marvin CMS Publishing API")
  .version("1.0.0")
  .option("--api-url <url>", "Marvin API URL, overrides MARVIN_API_URL")
  .option("--token <token>", "Site client token, overrides MARVIN_SITE_CLIENT_TOKEN")
  .option("--workspace <slug>", "Workspace slug, overrides MARVIN_WORKSPACE_SLUG")
  .option("--output <format>", "Output format: table, json, yaml, csv", "table")
  .option("--json", "Shortcut for --output json", false)
  .option("--yaml", "Shortcut for --output yaml", false)
  .option("--csv", "Shortcut for --output csv", false);

function outputMode(): OutputMode {
  const opts = program.opts();
  if (opts.json) return "json";
  if (opts.yaml) return "yaml";
  if (opts.csv) return "csv";

  const value = String(opts.output ?? "table").toLowerCase();
  if (["table", "json", "yaml", "csv"].includes(value)) return value as OutputMode;

  console.error(`Unsupported output format: ${value}. Use table, json, yaml, or csv.`);
  process.exit(1);
}

function client() {
  const opts = program.opts();

  const apiUrl = opts.apiUrl || process.env.MARVIN_API_URL;
  const siteClientToken = opts.token || process.env.MARVIN_SITE_CLIENT_TOKEN;
  const workspaceSlug = opts.workspace || process.env.MARVIN_WORKSPACE_SLUG;

  if (!apiUrl) {
    throw new Error("MARVIN_API_URL is required (set via --api-url or MARVIN_API_URL env var)");
  }
  if (!siteClientToken) {
    throw new Error("Site client token is required (set via --token or MARVIN_SITE_CLIENT_TOKEN env var)");
  }
  if (!workspaceSlug) {
    throw new Error("Workspace slug is required (set via --workspace or MARVIN_WORKSPACE_SLUG env var)");
  }

  return new MarvinClient({
    apiUrl,
    siteClientToken,
    workspaceSlug,
  });
}

async function run(action: () => Promise<unknown>, render?: (data: unknown) => void) {
  try {
    const data = await action();
    if (render) {
      render(data);
      return;
    }
    renderData(data, outputMode());
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  }
}

const entryColumns = {
  Title: (entry: MarvinEntry) => entry.title || "",
  Slug: (entry: MarvinEntry) => entry.slug || "",
  Type: (entry: MarvinEntry) => {
    // entryType is a string (slug) from the publishing API
    if (typeof entry.entryType === "string") return entry.entryType;
    // Fallback for object format from admin API
    if (typeof entry.entryType === "object" && entry.entryType && "slug" in entry.entryType) {
      return String((entry.entryType as { slug?: string }).slug ?? "");
    }
    return "";
  },
  Status: (entry: MarvinEntry) => entry.status || "",
  Published: (entry: MarvinEntry) => entry.publishedAt ? new Date(entry.publishedAt).toISOString().split('T')[0] : "",
};

const collectionColumns = {
  Name: (collection: MarvinCollection) => collection.name || "",
  Slug: (collection: MarvinCollection) => collection.slug || "",
  Description: (collection: MarvinCollection) => (collection.description || "").substring(0, 50),
};

const resourceColumns = {
  Name: (resource: MarvinResource) => resource.name || "",
  Slug: (resource: MarvinResource) => resource.slug || "",
  Type: (resource: MarvinResource) => resource.resourceType || "",
  Description: (resource: MarvinResource) => (resource.description || "").substring(0, 50),
  URL: (resource: MarvinResource) => resource.url || "",
};

const assetColumns = {
  Name: (asset: MarvinAsset) => asset.name || asset.slug || "",
  Slug: (asset: MarvinAsset) => asset.slug || "",
  Type: (asset: MarvinAsset) => asset.mimeType || "",
  Dimensions: (asset: MarvinAsset) =>
    asset.width && asset.height ? `${asset.width}x${asset.height}` : "",
  Alt: (asset: MarvinAsset) => (asset.altText || "").substring(0, 40),
};

program.command("site").description("Fetch workspace site configuration").action(() => run(async () => {
  const c = client();
  await c.initialize();
  return c.site;
}));

program
  .command("entries")
  .description("List published entries")
  .option("--entry-type <slug>", "Filter by entry type slug")
  .option("--collection <slug>", "Filter by collection slug")
  .option("--limit <number>", "Limit", (v) => Number(v))
  .option("--offset <number>", "Offset", (v) => Number(v))
  .action((opts) =>
    run(
      () => client().entries.list({
        entryType: opts.entryType,
        collection: opts.collection,
        limit: opts.limit,
        offset: opts.offset,
      }),
      (data) => renderList(data as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program
  .command("entry <slug>")
  .description("Fetch one entry by slug")
  .action((slug) =>
    run(
      () => client().entries.get(slug),
      (data) => renderList([data] as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program
  .command("collections")
  .description("List collections")
  .option("--limit <number>", "Limit", (v) => Number(v))
  .option("--offset <number>", "Offset", (v) => Number(v))
  .action((opts) =>
    run(
      () => client().collections.list(),
      (data) => renderList(data as MarvinCollection[], collectionColumns, outputMode()),
    ),
  );

program
  .command("collection <slug>")
  .description("Fetch one collection by slug")
  .action((slug) =>
    run(
      () => client().collections.get(slug),
      (data) => renderList([data] as MarvinCollection[], collectionColumns, outputMode()),
    ),
  );

program
  .command("collection-entries <slug>")
  .description("Fetch entries in a collection")
  .action((slug) =>
    run(
      async () => {
        const collection = await client().collections.get(slug);
        return collection.entries || [];
      },
      (data) => renderList(data as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program
  .command("assets")
  .description("List assets")
  .option("--type <type>", "Filter by asset type")
  .option("--limit <number>", "Limit", (v) => Number(v))
  .option("--offset <number>", "Offset", (v) => Number(v))
  .action((opts) =>
    run(
      () => client().assets.list({
        type: opts.type,
        limit: opts.limit,
        offset: opts.offset,
      }),
      (data) => renderList(data as MarvinAsset[], assetColumns, outputMode()),
    ),
  );

program
  .command("asset <slug>")
  .description("Fetch one asset by slug")
  .action((slug) =>
    run(
      async () => {
        const assets = await client().assets.list();
        const asset = assets.find(a => a.slug === slug);
        if (!asset) throw new Error(`Asset not found: ${slug}`);
        return asset;
      },
      (data) => renderList([data] as MarvinAsset[], assetColumns, outputMode()),
    ),
  );

program
  .command("resources")
  .description("List resources")
  .option("--resource-type <type>", "Filter by resource type")
  .option("--limit <number>", "Limit", (v) => Number(v))
  .option("--offset <number>", "Offset", (v) => Number(v))
  .action((opts) =>
    run(
      () => client().resources.list({
        resourceType: opts.resourceType,
        limit: opts.limit,
        offset: opts.offset,
      }),
      (data) => renderList(data as MarvinResource[], resourceColumns, outputMode()),
    ),
  );

program
  .command("resource <slug>")
  .description("Fetch one resource by slug")
  .action((slug) =>
    run(
      () => client().resources.get(slug),
      (data) => renderList([data] as MarvinResource[], resourceColumns, outputMode()),
    ),
  );

program
  .command("resource-entries <slug>")
  .description("Fetch entries that reference a resource")
  .action((slug) =>
    run(
      () => client().resources.entries(slug),
      (data) => renderList(data as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program.parseAsync();
