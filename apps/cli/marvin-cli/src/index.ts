#!/usr/bin/env node
import "dotenv/config";
import { Command } from "commander";
import {
  createMarvinClient,
  type MarvinAsset,
  type MarvinCollection,
  type MarvinEntry,
  type MarvinResource,
} from "./marvin-sdk.js";
import { renderData, renderList, type OutputMode } from "./output.js";

const program = new Command();

program
  .name("marvinctl")
  .description("CLI for testing Marvin publish API endpoints")
  .version("0.2.0")
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
  return createMarvinClient({
    apiUrl: opts.apiUrl,
    token: opts.token,
    workspaceSlug: opts.workspace,
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
  Title: (entry: MarvinEntry) => entry.title,
  Slug: (entry: MarvinEntry) => entry.slug,
  Type: (entry: MarvinEntry) =>
    typeof entry.entryType === "object" && entry.entryType && "slug" in entry.entryType
      ? String((entry.entryType as { slug?: string }).slug ?? "")
      : "",
  Status: (entry: MarvinEntry) => entry.status,
  Updated: (entry: MarvinEntry) => entry.updatedAt ?? entry.updateAt,
};

const collectionColumns = {
  Name: (collection: MarvinCollection) => collection.name,
  Slug: (collection: MarvinCollection) => collection.slug,
  Type: (collection: MarvinCollection) => collection.collectionType ?? collection.type,
  Visibility: (collection: MarvinCollection) => collection.visibility,
  Updated: (collection: MarvinCollection) => collection.updatedAt ?? collection.updateAt,
};

const resourceColumns = {
  Name: (resource: MarvinResource) => resource.name,
  Slug: (resource: MarvinResource) => resource.slug,
  Type: (resource: MarvinResource) => resource.resourceType,
  Description: (resource: MarvinResource) => resource.description,
  Updated: (resource: MarvinResource) => resource.updatedAt ?? resource.updateAt,
};

const assetColumns = {
  File: (asset: MarvinAsset) => asset.originalFilename ?? asset.filename ?? asset.slug,
  Type: (asset: MarvinAsset) => asset.contentType,
  URL: (asset: MarvinAsset) => asset.publicUrl,
  Alt: (asset: MarvinAsset) => asset.altText,
};

program.command("site").description("Fetch workspace site configuration").action(() => run(() => client().getSite()));

program
  .command("entries")
  .description("List published entries")
  .option("--entry-type <slug>", "Filter by entry type slug")
  .option("--collection <slug>", "Filter by collection slug")
  .option("--limit <number>", "Limit", (v) => Number(v))
  .action((opts) =>
    run(
      () => client().getEntries(opts),
      (data) => renderList(data as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program.command("entry <slug>").description("Fetch one entry by slug").action((slug) => run(() => client().getEntry(slug)));

program
  .command("collections")
  .description("List collections")
  .action(() =>
    run(
      () => client().getCollections(),
      (data) => renderList(data as MarvinCollection[], collectionColumns, outputMode()),
    ),
  );

program.command("collection <slug>").description("Fetch one collection by slug").action((slug) => run(() => client().getCollection(slug)));

program
  .command("collection-entries <slug>")
  .description("Fetch entries in a collection")
  .action((slug) =>
    run(
      () => client().getCollectionEntries(slug),
      (data) => renderList(data as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program
  .command("assets")
  .description("List assets")
  .option("--type <type>", "Filter by asset type")
  .option("--limit <number>", "Limit", (v) => Number(v))
  .action((opts) =>
    run(
      () => client().getAssets(opts),
      (data) => renderList(data as MarvinAsset[], assetColumns, outputMode()),
    ),
  );

program
  .command("resources")
  .description("List resources")
  .action(() =>
    run(
      () => client().getResources(),
      (data) => renderList(data as MarvinResource[], resourceColumns, outputMode()),
    ),
  );

program.command("resource <slug>").description("Fetch one resource by slug").action((slug) => run(() => client().getResource(slug)));

program
  .command("resource-entries <slug>")
  .description("Fetch entries that reference a resource")
  .action((slug) =>
    run(
      () => client().getResourceEntries(slug),
      (data) => renderList(data as MarvinEntry[], entryColumns, outputMode()),
    ),
  );

program.parseAsync();
