# Smart Collections

A **smart collection** fills itself from rules instead of being curated by hand. You describe
*which entries belong* (by type and status), and Marvin keeps the membership in sync
automatically as entries are created, published, edited, or archived.

Contrast with a **manual collection**, where you add and reorder entries yourself.

## How it works (materialized-via-reactions)

1. A collection has `isSmart: true` and a `smartRules` object.
2. Whenever an entry changes (created / updated / published / unpublished / archived / restored),
   a server-side reaction re-evaluates that entry against every smart collection's rules and
   adds or removes the membership row.
3. The **read path is unchanged** — the public site, renderers, and this admin UI all read the
   same membership rows as for a manually-curated collection. Smart collections are not a special
   case at render time.
4. A daily reconcile task re-materializes every smart collection as a safety net (covers missed
   events and bulk imports).

You do **not** add entries to a smart collection by hand — membership is derived. The entry
list on a smart collection reflects the rules.

## Rule format

`smartRules` is a JSON object. Every field is optional; combine them with `match`. An **empty
rule set matches nothing** (so a misconfigured smart collection can't sweep in the whole
workspace).

| Field | Meaning | Example |
| --- | --- | --- |
| `entry_types` | entry-type **slugs** to include | `["article", "bench-note"]` |
| `statuses` | entry statuses to include | `["published"]`, or `["inbox"]` for a Drafts collection |
| `tags` | tags to include — **reserved**, active once entries carry tags | `["leather"]` |
| `match` | how to combine the dimensions above | `"all"` (default) or `"any"` |

`match: "all"` (default) requires every provided dimension to hold; `"any"` requires at least one.

### Examples

```jsonc
// Published articles and bench notes
{ "entry_types": ["article", "bench-note"], "statuses": ["published"] }

// A "Drafts" collection: anything still in the inbox
{ "statuses": ["inbox"] }

// Anything published OR of type "release"
{ "entry_types": ["release"], "statuses": ["published"], "match": "any" }
```

### The Drafts → Published flow

Because membership follows `status`, an entry moves between smart collections as it progresses:
a draft matches a `{"statuses": ["inbox"]}` **Drafts** collection, and the moment it's published
it leaves Drafts and appears in a `{"statuses": ["published"]}` collection — no manual step.

## In the UI

The create (`/workspace/collections/new`) and edit (`/workspace/collections/{id}`) forms render
the shared **`SmartCollectionFields`** component:

- a **Smart Collection** toggle, and
- a **Rules (JSON)** editor (revealed when the toggle is on) with the inline reference above.

The component emits two form fields — `is_smart` and `smartRules` — which the forms forward to
the API. Manual entry management should be treated as read-only for a smart collection (its
membership is rule-managed); adding entries by hand isn't the model.

## In the SDK

```ts
import { createMarvinPlatformClient } from '@inneropen/marvin-sdk/platform';

const sdk = createMarvinPlatformClient({ /* … */ });

// Convenience: create a smart collection from rules
await sdk.collections.createSmart('Published Articles', {
  entry_types: ['article'],
  statuses: ['published'],
});

// Or via create() directly
await sdk.collections.create({
  name: 'Drafts',
  isSmart: true,
  smartRules: { statuses: ['inbox'] },
});
```

`SmartCollectionRules` is exported from `@inneropen/marvin-sdk/platform` for typing the rules.
Note the rule keys are **snake_case** (`entry_types`, `statuses`) — `smartRules` is stored as
opaque JSON and the server evaluates those exact keys.
