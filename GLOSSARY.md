# workflows

Shared, reusable GitHub Actions workflows that other repositories call and pin by commit. Each workflow keeps its scripts and tests beside it in this repo.

## Language

**Consumer**:
A repository that calls one of this repo's workflows.
_Avoid_: client, downstream repo

**Caller workflow**:
The consumer's workflow file holding the `uses:` job that calls a workflow from this repo.
_Avoid_: wrapper, stub

**Tools checkout**:
This repo's files, checked out at the exact commit the consumer pinned, from which a shared workflow runs its scripts.
_Avoid_: workflow checkout (easily confused with the consumer's own checkout)
