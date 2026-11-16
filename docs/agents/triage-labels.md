# Triage Labels

Labels used on this repo's issue tracker. Most are **triage roles** the skills speak in terms of; others (like `idea`) sit outside the triage flow.

## Triage roles

The skills speak in terms of five canonical triage roles. This section maps those roles to the actual label strings used in this repo's backlog.

| Canonical role    | Label in our backlog | Meaning                                  |
| ----------------- | -------------------- | ---------------------------------------- |
| `needs-triage`    | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`      | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human` | `ready-for-human`    | Requires human implementation            |
| `wontfix`         | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

## Other labels

These sit **outside** the triage state machine (`triage` ignores them); they mark stages of the idea → spec → tickets pipeline.

| Label  | Used by                          | Meaning                                                                                                   |
| ------ | -------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `idea` | `to-idea`                        | A discovery or idea captured to revisit later — a parking-lot stub, not a spec or a triaged item.          |
| `spec` | `grill-with-docs` (publish step) | A published spec (product requirements) issue — the source of truth for a feature, ready for `to-tickets`. |

An `idea` is a placeholder you revisit deliberately (`gh issue list --label idea`). A spec is published only at the end of grilling, so every `spec` issue is already grilled and ready for `to-tickets` to break into implementation tickets.
